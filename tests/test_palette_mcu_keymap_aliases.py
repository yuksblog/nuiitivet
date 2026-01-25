import sys
import types

from nuiitivet.material.theme import palette
from nuiitivet.material.theme.color_role import ColorRole


def test_theme_from_color_camelcase_aliases(monkeypatch):
    # Create a fake theme that returns camelCase keys (common alternative)
    camel_keys = {
        "primary": "#010101",
        "onPrimary": "#020202",
        "primaryContainer": "#030303",
        "onPrimaryContainer": "#040404",
        "inversePrimary": "#050505",
        "secondary": "#060606",
        "onSecondary": "#070707",
        "secondaryContainer": "#080808",
        "onSecondaryContainer": "#090909",
        "tertiary": "#0A0A0A",
        "onTertiary": "#0B0B0B",
        "tertiaryContainer": "#0C0C0C",
        "onTertiaryContainer": "#0D0D0D",
        "background": "#0E0E0E",
        "onBackground": "#0F0F0F",
        "surface": "#101010",
        "onSurface": "#111111",
        "surfaceVariant": "#121212",
        "onSurfaceVariant": "#131313",
        "outline": "#141414",
        "shadow": "#151515",
        "scrim": "#161616",
        "error": "#171717",
        "onError": "#181818",
        "errorContainer": "#191919",
        "onErrorContainer": "#1A1A1A",
    }

    fake_mod = types.SimpleNamespace()

    def theme_from_color(seed):
        class FakeTheme:
            def __init__(self, schemes):
                self._d = {"schemes": {"light": schemes, "dark": schemes}}

            def dict(self):
                return self._d

        return FakeTheme(camel_keys)

    fake_mod.theme_from_color = theme_from_color
    monkeypatch.setitem(sys.modules, "material_color_utilities", fake_mod)

    light, dark = palette.from_seed("#ABCDEF")

    # ensure every ColorRole has a mapping coming from our fake theme (alias supported)
    for role in ColorRole:
        assert role in light, f"{role} missing in light roles"
        assert role in dark, f"{role} missing in dark roles"

    # spot-check alias-resolved entries
    assert light[ColorRole.ON_PRIMARY] == camel_keys["onPrimary"]
    assert light[ColorRole.ON_ERROR] == camel_keys["onError"]
