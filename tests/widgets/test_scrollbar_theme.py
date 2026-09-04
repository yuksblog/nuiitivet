"""Tests for generic scrollbar theming via the theme seam.

The scrollbar is a generic widget: it must not depend on ``material`` and must
resolve its colors from :class:`~nuiitivet.scrolling.ScrollbarThemeData` at paint
time so a single theme renders correctly across light and dark modes. Per the
framework-wide ``ThemeData`` / ``Style`` split, per-instance overrides live on
:class:`~nuiitivet.scrolling.ScrollbarStyle` and win over the theme default.
"""

from __future__ import annotations

import ast
from pathlib import Path

from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.scrolling import ScrollbarStyle, ScrollbarThemeData
from nuiitivet.theme.plain_theme import PlainTheme
from nuiitivet.theme.resolver import resolve_color_to_rgba


def test_scrollbar_widget_does_not_import_material_layer() -> None:
    """``widgets/scrollbar.py`` must not depend on ``nuiitivet.material``."""

    repo_root = Path(__file__).resolve().parents[2]
    scrollbar_file = repo_root / "src" / "nuiitivet" / "widgets" / "scrollbar.py"

    tree = ast.parse(scrollbar_file.read_text(encoding="utf-8"), filename=str(scrollbar_file))

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "nuiitivet.material" or alias.name.startswith("nuiitivet.material."):
                    violations.append(f"{node.lineno} imports {alias.name}")
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "nuiitivet.material" or module.startswith("nuiitivet.material."):
                violations.append(f"{node.lineno} imports from {module}")

    assert violations == []


def test_bare_theme_data_has_neutral_defaults() -> None:
    """A bare ``ScrollbarThemeData()`` resolves without any registered theme."""

    theme_data = ScrollbarThemeData()
    assert resolve_color_to_rgba(theme_data.track, theme=None) == (0, 0, 0, 30)
    assert resolve_color_to_rgba(theme_data.thumb, theme=None) == (0, 0, 0, 178)


def test_plain_theme_scrollbar_follows_light_dark_mode() -> None:
    """Plain themes carry a ScrollbarThemeData whose thumb flips with the mode."""

    light = PlainTheme.light()
    dark = PlainTheme.dark()

    st_light = light.extension(ScrollbarThemeData)
    st_dark = dark.extension(ScrollbarThemeData)
    assert st_light is not None and st_dark is not None

    light_thumb = resolve_color_to_rgba(st_light.thumb, theme=light)
    dark_thumb = resolve_color_to_rgba(st_dark.thumb, theme=dark)

    # on_surface is black in light, white in dark; alpha stays the same.
    assert light_thumb[:3] == (0, 0, 0)
    assert dark_thumb[:3] == (255, 255, 255)
    assert light_thumb[3] == dark_thumb[3]


def test_material_theme_scrollbar_follows_light_dark_mode() -> None:
    """Material themes register a token-based ScrollbarThemeData for both modes."""

    light = MaterialThemeFactory.light("#6750A4")
    dark = MaterialThemeFactory.dark("#6750A4")

    st_light = light.extension(ScrollbarThemeData)
    st_dark = dark.extension(ScrollbarThemeData)
    assert st_light is not None and st_dark is not None

    # The same token instance resolves to different RGB per mode.
    assert resolve_color_to_rgba(st_light.thumb, theme=light) != resolve_color_to_rgba(
        st_dark.thumb, theme=dark
    )
    # Active (pressed/drag) maps onto the PRIMARY accent — fully opaque.
    assert resolve_color_to_rgba(st_light.thumb_active, theme=light)[3] == 255
    assert resolve_color_to_rgba(st_dark.thumb_active, theme=dark)[3] == 255


def test_style_resolve_colors_falls_back_to_theme_data() -> None:
    """With no per-instance overrides, ScrollbarStyle uses the theme palette."""

    light = PlainTheme.light()
    theme_data = light.extension(ScrollbarThemeData)
    style = ScrollbarStyle()  # no color overrides

    resolved = style.resolve_colors(theme_data, theme=light)
    # Plain light on_surface is black; idle thumb alpha 0.70 -> 178.
    assert resolved["thumb"] == (0, 0, 0, 178)
    assert resolved["track"] == (0, 0, 0, 30)


def test_style_override_wins_over_theme_data() -> None:
    """A per-instance ColorSpec on ScrollbarStyle overrides the theme palette."""

    light = PlainTheme.light()
    theme_data = light.extension(ScrollbarThemeData)
    assert theme_data is not None
    style = ScrollbarStyle(thumb=(255, 0, 0, 255), track=("#00FF00", 0.5))

    resolved = style.resolve_colors(theme_data, theme=light)
    assert resolved["thumb"] == (255, 0, 0, 255)
    assert resolved["track"] == (0, 255, 0, 127)
    # Un-overridden slots still come from the theme.
    assert resolved["thumb_active"] == resolve_color_to_rgba(theme_data.thumb_active, theme=light)


def test_style_resolve_colors_without_theme_data_uses_neutral_defaults() -> None:
    """resolve_colors works even when no ScrollbarThemeData is registered."""

    resolved = ScrollbarStyle().resolve_colors(None, theme=None)
    assert resolved["track"] == (0, 0, 0, 30)
    assert resolved["thumb"] == (0, 0, 0, 178)
