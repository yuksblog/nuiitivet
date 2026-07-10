"""Tests for the pyglet backend's key/modifier normalization.

These exercise the backend-to-widget boundary: widgets receive whatever
``_normalize_key`` returns, so a dropped modifier mask here silently disables
every modifier-gated branch downstream (Ctrl+A in EditableText, Shift+Arrow in
Slider, and so on).
"""

import pytest
from pyglet.window import key as pyglet_key

from nuiitivet.backends.pyglet.runner import _normalize_key, _normalize_modifiers
from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT


@pytest.mark.parametrize(
    "symbol, expected_name",
    [
        (pyglet_key.A, "a"),
        (pyglet_key.RIGHT, "right"),
        (pyglet_key.LEFT, "left"),
        (pyglet_key.UP, "up"),
        (pyglet_key.DOWN, "down"),
        (pyglet_key.ESCAPE, "escape"),
        (pyglet_key.TAB, "tab"),
        (pyglet_key.SPACE, "space"),
        (pyglet_key.ENTER, "enter"),
        (pyglet_key.RETURN, "enter"),
    ],
)
def test_normalize_key_without_modifiers(symbol: int, expected_name: str) -> None:
    assert _normalize_key(symbol, 0) == (expected_name, 0)


@pytest.mark.parametrize(
    "symbol, expected_name",
    [
        (pyglet_key.A, "a"),
        (pyglet_key.RIGHT, "right"),
        (pyglet_key.LEFT, "left"),
        (pyglet_key.UP, "up"),
        (pyglet_key.DOWN, "down"),
        (pyglet_key.ESCAPE, "escape"),
        (pyglet_key.TAB, "tab"),
        (pyglet_key.SPACE, "space"),
        (pyglet_key.ENTER, "enter"),
        (pyglet_key.RETURN, "enter"),
    ],
)
@pytest.mark.parametrize(
    "pyglet_modifiers, expected_modifier_keys",
    [
        (pyglet_key.MOD_SHIFT, MOD_SHIFT),
        (pyglet_key.MOD_CTRL, MOD_CTRL),
        (pyglet_key.MOD_ALT, MOD_ALT),
        (pyglet_key.MOD_COMMAND, MOD_META),
        (pyglet_key.MOD_CTRL | pyglet_key.MOD_SHIFT, MOD_CTRL | MOD_SHIFT),
    ],
)
def test_normalize_key_preserves_modifiers(
    symbol: int,
    expected_name: str,
    pyglet_modifiers: int,
    expected_modifier_keys: int,
) -> None:
    """Every named key must carry its modifier mask, not only tab/space/enter."""
    assert _normalize_key(symbol, pyglet_modifiers) == (expected_name, expected_modifier_keys)


def test_normalize_key_ctrl_a_reaches_editable_text_shortcut() -> None:
    """Ctrl+A must arrive as the ("a", MOD_CTRL) pair EditableText gates its shortcuts on."""
    name, modifier_keys = _normalize_key(pyglet_key.A, pyglet_key.MOD_CTRL)
    assert name == "a"
    assert bool(modifier_keys & (MOD_CTRL | MOD_META))


def test_normalize_key_cmd_a_reaches_editable_text_shortcut() -> None:
    """Cmd+A (macOS) maps to META and must satisfy the same gate."""
    name, modifier_keys = _normalize_key(pyglet_key.A, pyglet_key.MOD_COMMAND)
    assert name == "a"
    assert bool(modifier_keys & (MOD_CTRL | MOD_META))


def test_normalize_key_shift_arrow_reaches_slider_coarse_step() -> None:
    """Shift+Arrow must arrive with MOD_SHIFT so Slider takes its 10x step."""
    name, modifier_keys = _normalize_key(pyglet_key.RIGHT, pyglet_key.MOD_SHIFT)
    assert name == "right"
    assert bool(modifier_keys & MOD_SHIFT)


def test_normalize_key_ignores_unknown_modifier_bits() -> None:
    """Modifier bits nuiitivet does not model must not leak into the mask."""
    assert _normalize_key(pyglet_key.A, pyglet_key.MOD_CAPSLOCK) == ("a", 0)


def test_normalize_key_names_unknown_symbol_but_keeps_modifiers() -> None:
    """An unmapped symbol still yields a name from pyglet and keeps its modifiers."""
    name, modifier_keys = _normalize_key(999999, pyglet_key.MOD_CTRL)
    assert name == "999999"
    assert modifier_keys == MOD_CTRL


def test_normalize_key_keeps_modifiers_when_name_lookup_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure naming the key must not zero out an already-resolved modifier mask."""

    def boom(_symbol: int) -> str:
        raise RuntimeError("symbol_string failed")

    monkeypatch.setattr(pyglet_key, "symbol_string", boom)

    assert _normalize_key(pyglet_key.A, pyglet_key.MOD_CTRL) == ("", MOD_CTRL)


@pytest.mark.parametrize(
    "pyglet_modifiers, expected_modifier_keys",
    [
        (0, 0),
        (pyglet_key.MOD_SHIFT, MOD_SHIFT),
        (pyglet_key.MOD_CTRL, MOD_CTRL),
        (pyglet_key.MOD_ALT, MOD_ALT),
        (pyglet_key.MOD_COMMAND, MOD_META),
        (
            pyglet_key.MOD_SHIFT | pyglet_key.MOD_CTRL | pyglet_key.MOD_ALT | pyglet_key.MOD_COMMAND,
            MOD_SHIFT | MOD_CTRL | MOD_ALT | MOD_META,
        ),
    ],
)
def test_normalize_modifiers(pyglet_modifiers: int, expected_modifier_keys: int) -> None:
    assert _normalize_modifiers(pyglet_modifiers) == expected_modifier_keys
