"""Tests for Shortcut.display — the accelerator label menus show."""

from __future__ import annotations

import sys

import pytest

from nuiitivet.input.codes import MOD_ACCEL, MOD_CTRL, MOD_META
from nuiitivet.input.shortcut import Shortcut


def test_display_macos_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    assert Shortcut.parse("Accel+S").display == "⌘S"
    assert Shortcut.parse("Accel+Shift+S").display == "⇧⌘S"
    assert Shortcut.parse("Ctrl+Alt+Delete").display == "⌃⌥Del"


def test_display_non_macos_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert Shortcut.parse("Accel+S").display == "Ctrl+S"
    assert Shortcut.parse("Accel+Shift+S").display == "Ctrl+Shift+S"
    assert Shortcut.parse("Meta+Enter").display == "Meta+Enter"


def test_display_key_forms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert Shortcut.parse("Ctrl+F5").display == "Ctrl+F5"
    assert Shortcut.parse("Ctrl+PgUp").display == "Ctrl+Page Up"
    assert Shortcut.parse("Ctrl+Escape").display == "Ctrl+Esc"


def test_display_resolves_accel_per_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    shortcut = Shortcut("s", MOD_ACCEL)
    monkeypatch.setattr(sys, "platform", "darwin")
    darwin_label = shortcut.display
    monkeypatch.setattr(sys, "platform", "linux")
    linux_label = shortcut.display
    assert darwin_label == "⌘S"
    assert linux_label == "Ctrl+S"
    # Sanity: the underlying masks differ per platform.
    assert MOD_CTRL != MOD_META
