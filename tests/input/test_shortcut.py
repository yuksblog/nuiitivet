"""Tests for the ``Shortcut`` value type and ``MOD_ACCEL`` (issue #327).

Covers spec parsing, key-name normalization, exact modifier matching, and the
platform resolution of ``MOD_ACCEL`` — which must happen at match time, never at
construction, so one ``Shortcut`` value is portable across platforms.
"""

from __future__ import annotations

import pytest

import nuiitivet as nv
from nuiitivet.input.codes import (
    MOD_ACCEL,
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    accel_mask,
    resolve_modifiers,
)
from nuiitivet.input.shortcut import (
    Shortcut,
    ShortcutBinding,
    ShortcutScope,
    normalize_key_name,
    to_shortcut,
)


def test_exported_from_root() -> None:
    assert nv.Shortcut is Shortcut
    assert nv.ShortcutBinding is ShortcutBinding
    assert nv.MOD_ACCEL == MOD_ACCEL


def test_parse_single_key() -> None:
    assert Shortcut.parse("S") == Shortcut("s", 0)


def test_parse_modifiers_are_case_insensitive_with_aliases() -> None:
    assert Shortcut.parse("Accel+S") == Shortcut("s", MOD_ACCEL)
    assert Shortcut.parse("primary+s") == Shortcut("s", MOD_ACCEL)
    assert Shortcut.parse("CTRL+SHIFT+Z") == Shortcut("z", MOD_CTRL | MOD_SHIFT)
    assert Shortcut.parse("Command+Option+F1") == Shortcut("f1", MOD_META | MOD_ALT)


def test_parse_plus_as_key() -> None:
    assert Shortcut.parse("Accel++") == Shortcut("+", MOD_ACCEL)


def test_parse_rejects_bad_specs() -> None:
    with pytest.raises(ValueError):
        Shortcut.parse("")
    with pytest.raises(ValueError):
        Shortcut.parse("Hyper+S")


def test_normalize_key_name_strips_backend_digit_prefix() -> None:
    # pyglet reports the "1" key as "_1"; a shortcut written as "Accel+1" must
    # still match it.
    assert normalize_key_name("_1") == "1"
    assert normalize_key_name("ESC") == "escape"
    assert Shortcut.parse("Accel+1").matches("_1", accel_mask())


def test_accel_resolves_at_match_time_not_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    save = Shortcut.parse("Accel+S")
    # The declaration keeps the logical bit — nothing platform-specific baked in.
    assert save.modifiers == MOD_ACCEL

    monkeypatch.setattr("sys.platform", "darwin")
    assert resolve_modifiers(MOD_ACCEL) == MOD_META
    assert save.matches("s", MOD_META)
    assert not save.matches("s", MOD_CTRL)

    monkeypatch.setattr("sys.platform", "win32")
    assert resolve_modifiers(MOD_ACCEL) == MOD_CTRL
    assert save.matches("s", MOD_CTRL)
    assert not save.matches("s", MOD_META)


def test_resolve_modifiers_preserves_other_bits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    assert resolve_modifiers(MOD_ACCEL | MOD_SHIFT) == MOD_META | MOD_SHIFT
    assert resolve_modifiers(MOD_CTRL | MOD_ALT) == MOD_CTRL | MOD_ALT


def test_matches_requires_exact_modifier_mask() -> None:
    save = Shortcut("s", MOD_ACCEL)
    assert not save.matches("s", accel_mask() | MOD_SHIFT)
    assert not save.matches("s", 0)
    assert not save.matches("d", accel_mask())


def test_to_shortcut_accepts_str_and_shortcut() -> None:
    typed = Shortcut("d", MOD_ACCEL)
    assert to_shortcut("Accel+D") == typed
    assert to_shortcut(typed) is typed


def test_binding_defaults_to_foreground_scope() -> None:
    # The default must not require focus: that is the whole point of the layer.
    binding = ShortcutBinding(Shortcut.parse("Accel+S"), lambda: None)
    assert binding.scope is ShortcutScope.FOREGROUND


def test_binding_identity_is_the_gesture() -> None:
    # ShortcutNode keys bindings by gesture, so two bindings for the same gesture
    # must compare (and hash) equal regardless of the callback.
    a = ShortcutBinding(Shortcut.parse("Accel+S"), lambda: None)
    b = ShortcutBinding(Shortcut.parse("Accel+S"), lambda: None)
    assert a == b
    assert hash(a) == hash(b)
