"""Tests for MenuBarStyle / MenuBarThemeData merging."""

from __future__ import annotations

from nuiitivet.menubar.style import MenuBarStyle
from nuiitivet.menubar.theme_data import MenuBarThemeData


def test_merged_palette_defaults_when_no_theme_data() -> None:
    style = MenuBarStyle()
    palette = style.merged_palette(None)
    assert palette == MenuBarThemeData()


def test_merged_palette_applies_overrides() -> None:
    theme_data = MenuBarThemeData(bar_background="#111111", popup_background="#222222")
    style = MenuBarStyle(bar_background="#ABCDEF")
    palette = style.merged_palette(theme_data)
    assert palette.bar_background == "#ABCDEF"
    assert palette.popup_background == "#222222"


def test_merged_palette_without_overrides_is_theme_data() -> None:
    theme_data = MenuBarThemeData(bar_background="#111111")
    assert MenuBarStyle().merged_palette(theme_data) is theme_data


def test_copy_with() -> None:
    style = MenuBarStyle().copy_with(bar_height=48)
    assert style.bar_height == 48
    assert style.item_gap == MenuBarStyle().item_gap
