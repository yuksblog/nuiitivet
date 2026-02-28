import sys
import types

from nuiitivet.material.theme import palette
from nuiitivet.material.theme.color_role import ColorRole


def test_theme_from_color_full_keymap(monkeypatch):
    # build fake schemes with keys matching expected snake_case keys
    keys = {
        "primary": "#010101",
        "on_primary": "#020202",
        "primary_container": "#030303",
        "on_primary_container": "#040404",
        "inverse_primary": "#050505",
        "secondary": "#060606",
        "on_secondary": "#070707",
        "secondary_container": "#080808",
        "on_secondary_container": "#090909",
        "tertiary": "#0A0A0A",
        "on_tertiary": "#0B0B0B",
        "tertiary_container": "#0C0C0C",
        "on_tertiary_container": "#0D0D0D",
        "background": "#0E0E0E",
        "on_background": "#0F0F0F",
        "surface": "#101010",
        "on_surface": "#111111",
        "inverse_surface": "#1B1B1F",
        "inverse_on_surface": "#F2F0F4",
        "surface_variant": "#121212",
        "on_surface_variant": "#131313",
        "outline": "#141414",
        "shadow": "#151515",
        "scrim": "#161616",
        "error": "#171717",
        "on_error": "#181818",
        "error_container": "#191919",
        "on_error_container": "#1A1A1A",
    }

    fake_mod = types.SimpleNamespace()

    def theme_from_color(seed):
        class FakeTheme:
            def __init__(self, schemes):
                self._d = {"schemes": {"light": schemes, "dark": schemes}}

            def dict(self):
                return self._d

        return FakeTheme(keys)

    fake_mod.theme_from_color = theme_from_color
    monkeypatch.setitem(sys.modules, "material_color_utilities", fake_mod)

    light, dark = palette.from_seed("#ABCDEF")

    # ensure every ColorRole has a mapping coming from our fake theme
    for role in ColorRole:
        assert role in light, f"{role} missing in light roles"
        assert role in dark, f"{role} missing in dark roles"

    # spot-check a few values to ensure mapping preserves values
    assert light[ColorRole.PRIMARY] == keys["primary"]
    assert light[ColorRole.ON_PRIMARY] == keys["on_primary"]
    assert light[ColorRole.SURFACE_VARIANT] == keys["surface_variant"]
