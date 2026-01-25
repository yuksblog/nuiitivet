from nuiitivet.material.icon import Icon
from nuiitivet.rendering.skia import skcolor
from nuiitivet.theme import manager
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.material.theme.material_theme import MaterialTheme


def test_icon_resolve_color_uses_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))
    icon = Icon("home")
    # _resolve_color is removed, use resolve_color_to_rgba directly
    rgba = resolve_color_to_rgba(icon.style.color)
    mat = manager.current.extension(MaterialThemeData)
    assert mat is not None
    expected_hex = mat.roles.get(ColorRole.ON_SURFACE)
    assert expected_hex is not None
    expected_rgba = resolve_color_to_rgba(expected_hex)
    assert rgba == expected_rgba


def test_button_overlay_alpha_values():
    black_ov = skcolor("#000000", 0.12)
    if isinstance(black_ov, tuple):
        alpha = black_ov[3]
    else:
        alpha = int(black_ov) >> 24 & 255
    assert alpha == int(0.12 * 255)
    white_ov = skcolor("#FFFFFF", 0.06)
    if isinstance(white_ov, tuple):
        alpha = white_ov[3]
    else:
        alpha = int(white_ov) >> 24 & 255
    assert alpha == int(0.06 * 255)
