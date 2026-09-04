"""Tests for the dev action primitives (click / type / key + settle)."""

from __future__ import annotations

from typing import Any, Optional

import pytest

from nuiitivet.dev.action import (
    TargetNotFoundError,
    check_condition,
    click,
    press_key,
    resolve_modifiers,
    settle,
    type_text,
)
from nuiitivet.input.codes import (
    MOD_SHIFT,
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_DELETE,
    TEXT_MOTION_LEFT,
    accel_mask,
)


class _Node:
    def __init__(self, *, rect: Optional[tuple] = (0, 0, 100, 40), **identity: Any) -> None:
        self.children: list[_Node] = []
        self.built_child: Optional[_Node] = None
        self.global_layout_rect = rect
        self.laid_out = False
        for name, value in identity.items():
            setattr(self, name, value)

    def layout(self, width: int, height: int) -> None:
        self.laid_out = True

    def clear_needs_layout(self) -> None:
        pass


class _App:
    """Fake app recording the synthetic input it received."""

    def __init__(self, root: _Node) -> None:
        self.root = root
        self.width = 360
        self.height = 240
        self.presses: list[tuple] = []
        self.releases: list[tuple] = []
        self.texts: list[str] = []
        self.key_presses: list[tuple] = []
        self.key_releases: list[tuple] = []
        self.text_motions: list[tuple] = []
        self.invalidated = 0
        self._text_handled = True
        self._key_handled = True
        self._motion_handled = False

    def _dispatch_mouse_press(self, x: int, y: int, *, button: Any = None) -> None:
        self.presses.append((x, y, button))

    def _dispatch_mouse_release(self, x: int, y: int, *, button: Any = None) -> None:
        self.releases.append((x, y, button))

    def _dispatch_text(self, text: str) -> bool:
        self.texts.append(text)
        return self._text_handled

    def _dispatch_key_press(self, key: str, modifiers: int) -> bool:
        self.key_presses.append((key, modifiers))
        return self._key_handled

    def _dispatch_key_release(self, key: str, modifiers: int) -> bool:
        self.key_releases.append((key, modifiers))
        return False

    def _dispatch_text_motion(self, motion: int, select: bool = False) -> bool:
        self.text_motions.append((motion, select))
        return self._motion_handled

    def invalidate(self) -> None:
        self.invalidated += 1


def test_resolve_modifiers_int_and_names() -> None:
    assert resolve_modifiers(0) == 0
    assert resolve_modifiers(5) == 5
    # Names stand in for backend input, and backends emit physical masks:
    # "accel" resolves to the platform's Ctrl/Cmd, never the logical bit.
    assert resolve_modifiers(["accel", "shift"]) == accel_mask() | MOD_SHIFT
    assert resolve_modifiers(None) == 0


def test_resolve_modifiers_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown modifier"):
        resolve_modifiers(["hyper"])


def test_click_by_key_targets_rect_center() -> None:
    target = _Node(key="submit", rect=(10, 20, 100, 40))
    app = _App(_Node())
    app.root.children = [target]

    result = click(app, key="submit")

    # Center of (10, 20, 100, 40) is (60, 40).
    assert app.presses == [(60, 40, None)]
    assert app.releases == [(60, 40, None)]
    assert result["clicked"] == {"type": "_Node", "key": "submit"}
    assert result["x"] == 60 and result["y"] == 40


def test_click_by_label() -> None:
    target = _Node(label="increment", rect=(0, 0, 20, 20))
    app = _App(_Node())
    app.root.children = [target]

    click(app, label="increment")
    assert app.presses == [(10, 10, None)]


def test_click_by_raw_coordinates() -> None:
    app = _App(_Node())
    click(app, x=5, y=7)
    assert app.presses == [(5, 7, None)]


def test_click_missing_target_raises() -> None:
    app = _App(_Node())
    with pytest.raises(TargetNotFoundError, match="no widget matched"):
        click(app, key="nope")


def test_click_requires_target_or_coords() -> None:
    app = _App(_Node())
    with pytest.raises(ValueError, match="requires a 'key'"):
        click(app)


def test_click_target_without_rect_raises() -> None:
    target = _Node(key="ghost", rect=None)
    app = _App(_Node())
    app.root.children = [target]
    with pytest.raises(TargetNotFoundError, match="no layout rect"):
        click(app, key="ghost")


def test_type_text_routes_to_focused() -> None:
    app = _App(_Node())
    result = type_text(app, "hello")
    assert app.texts == ["hello"]
    assert result == {"typed": "hello", "handled": True}


def test_press_key_with_modifiers() -> None:
    app = _App(_Node())
    result = press_key(app, "s", ["accel"])
    assert app.key_presses == [("s", accel_mask())]
    assert app.key_releases == [("s", accel_mask())]
    assert result["handled"] is True
    assert result["modifiers"] == accel_mask()


def test_press_key_editing_key_also_dispatches_its_text_motion() -> None:
    app = _App(_Node())

    press_key(app, "backspace")

    # Both routes, as a backend delivers them -- only the motion edits text.
    assert app.key_presses == [("backspace", 0)]
    assert app.text_motions == [(TEXT_MOTION_BACKSPACE, False)]


def test_press_key_shift_makes_the_motion_extend_the_selection() -> None:
    app = _App(_Node())

    press_key(app, "left", ["shift"])

    assert app.text_motions == [(TEXT_MOTION_LEFT, True)]


def test_press_key_aliased_editing_key_maps_to_its_motion() -> None:
    app = _App(_Node())

    press_key(app, "Del")

    assert app.text_motions == [(TEXT_MOTION_DELETE, False)]


def test_press_key_non_editing_key_dispatches_no_motion() -> None:
    app = _App(_Node())

    press_key(app, "enter")

    assert app.text_motions == []


def test_press_key_reports_handled_when_only_the_motion_consumed_it() -> None:
    app = _App(_Node())
    app._key_handled = False
    app._motion_handled = True

    result = press_key(app, "home")

    assert result["handled"] is True


def test_settle_lays_out_and_invalidates() -> None:
    root = _Node()
    app = _App(root)
    settle(app)
    assert root.laid_out is True
    assert app.invalidated == 1


def test_actions_settle_after_dispatch() -> None:
    app = _App(_Node())
    app.root.children = [_Node(key="x", rect=(0, 0, 10, 10))]
    click(app, key="x")
    # settle() ran: a layout pass + a repaint request followed the click.
    assert app.root.laid_out is True
    assert app.invalidated == 1


def test_check_condition_settles_then_evaluates() -> None:
    root = _Node()
    root.children = [_Node(label="Done")]
    app = _App(root)

    assert check_condition(app, label="Done") is True
    # A settle ran as part of the poll (layout pass + repaint request).
    assert root.laid_out is True
    assert app.invalidated == 1


def test_check_condition_absent() -> None:
    app = _App(_Node())
    app.root.children = [_Node(key="spinner", rect=(0, 0, 10, 10))]
    assert check_condition(app, key="spinner", present=False) is False
    assert check_condition(app, key="spinner", present=True) is True
