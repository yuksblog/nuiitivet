from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.rendering.skia import rgba_to_skia_color, skcolor


def test_resolve_color_with_colorrole():
    # current theme should provide a hex for PRIMARY
    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    mat = light.extension(MaterialThemeData)
    assert mat is not None
    hexv = mat.roles.get(ColorRole.PRIMARY)
    assert hexv is not None
    assert rgba_to_skia_color(resolve_color_to_rgba(ColorRole.PRIMARY, theme=light)) == skcolor(hexv)


def test_resolve_color_with_colorrole_and_alpha():
    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    mat = light.extension(MaterialThemeData)
    assert mat is not None
    hexv = mat.roles.get(ColorRole.PRIMARY)
    assert hexv is not None
    assert rgba_to_skia_color(resolve_color_to_rgba((ColorRole.PRIMARY, 0.5), theme=light)) == skcolor(hexv, 0.5)


def test_resolve_default_colorrole_when_val_none():
    # default may be a ColorRole — resolve_color should handle that
    default_role = ColorRole.BACKGROUND
    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    mat = light.extension(MaterialThemeData)
    assert mat is not None
    hexv = mat.roles.get(default_role)
    assert hexv is not None
    assert rgba_to_skia_color(resolve_color_to_rgba(None, default=default_role, theme=light)) == skcolor(hexv)


def test_resolve_color_pair_alpha_multiplies_embedded_alpha():
    # When a (base, alpha) pair is used, alpha multiplies any alpha embedded in
    # the base literal.
    rgba = resolve_color_to_rgba(("#FF000080", 0.5))
    assert rgba == (255, 0, 0, 64)
