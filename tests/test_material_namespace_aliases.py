"""Tests for theme-namespaced aliases in ``nuiitivet.material``.

See issue #85.
"""

from __future__ import annotations

import nuiitivet
from nuiitivet import material
from nuiitivet.material import App, MaterialApp, MaterialOverlay, Overlay, ThemeFactory
from nuiitivet.material.theme.material_theme import MaterialThemeFactory


def test_app_alias_is_material_app() -> None:
    assert App is MaterialApp


def test_overlay_alias_is_material_overlay() -> None:
    assert Overlay is MaterialOverlay


def test_theme_factory_alias_is_material_theme_factory() -> None:
    assert ThemeFactory is MaterialThemeFactory


def test_aliases_in_all() -> None:
    assert "App" in material.__all__
    assert "Overlay" in material.__all__
    assert "ThemeFactory" in material.__all__


def test_original_names_still_exported() -> None:
    assert "MaterialApp" in material.__all__
    assert "MaterialOverlay" in material.__all__


def test_top_level_does_not_expose_app() -> None:
    assert "App" not in nuiitivet.__all__
    assert not hasattr(nuiitivet, "App")
