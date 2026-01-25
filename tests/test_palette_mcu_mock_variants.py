import sys
import types

from nuiitivet.material.theme import palette
from nuiitivet.material.theme.color_role import ColorRole


def _make_fake_theme(light: dict, dark: dict):
    class FakeTheme:
        def __init__(self, light, dark):
            self._d = {"schemes": {"light": light, "dark": dark}}

        def dict(self):
            return self._d

    return FakeTheme(light, dark)


def test_theme_from_color_hex(monkeypatch):
    fake_mod = types.SimpleNamespace()

    def theme_from_color(seed):
        return _make_fake_theme({"primary": "#112233"}, {"primary": "#332211"})

    fake_mod.theme_from_color = theme_from_color
    monkeypatch.setitem(sys.modules, "material_color_utilities", fake_mod)

    light, dark = palette.from_seed("#ABCDEF")
    assert light[ColorRole.PRIMARY].lower() == "#112233"
    assert dark[ColorRole.PRIMARY].lower() == "#332211"


def test_theme_from_color_argb_int(monkeypatch):
    fake_mod = types.SimpleNamespace()

    def theme_from_color(seed):
        return _make_fake_theme({"primary": 0xFF112233}, {"primary": 0xFF332211})

    fake_mod.theme_from_color = theme_from_color
    monkeypatch.setitem(sys.modules, "material_color_utilities", fake_mod)

    light, dark = palette.from_seed("#000000")
    assert light[ColorRole.PRIMARY].lower() == "#112233"
    assert dark[ColorRole.PRIMARY].lower() == "#332211"


def test_theme_from_color_tuple(monkeypatch):
    fake_mod = types.SimpleNamespace()

    # 3-tuple -> (r,g,b); 4-tuple -> (a,r,g,b) handled by code
    def theme_from_color(seed):
        return _make_fake_theme({"primary": (17, 34, 51)}, {"primary": (255, 51, 34, 17)})

    fake_mod.theme_from_color = theme_from_color
    monkeypatch.setitem(sys.modules, "material_color_utilities", fake_mod)

    light, dark = palette.from_seed("#010203")
    assert light[ColorRole.PRIMARY].lower() == "#112233"
    # 4-tuple uses indices 1..3 -> (51,34,17) -> #332211
    assert dark[ColorRole.PRIMARY].lower() == "#332211"


def test_corepalette_legacy(monkeypatch):
    # Fake tonal member exposing .tone(tone)
    class FakePalMember:
        def __init__(self, hexint):
            self._hex = int(hexint)

        def tone(self, t):
            return self._hex

    class FakeCorePalette:
        @staticmethod
        def of(argb):
            class CP:
                primary = FakePalMember(0xFF112233)
                secondary = FakePalMember(0xFF445566)
                neutral = FakePalMember(0xFFEEEEEE)
                neutral_variant = FakePalMember(0xFFDDDDDD)
                error = FakePalMember(0xFFAA0000)

            return CP()

    fake_core = types.SimpleNamespace(CorePalette=FakeCorePalette)
    fake_mod = types.SimpleNamespace(core=fake_core)
    monkeypatch.setitem(sys.modules, "material_color_utilities", fake_mod)

    light, dark = palette.from_seed("#010203")
    # compute expected from the fake CorePalette we provided
    # Ensure the CorePalette path returns hex strings for primary roles
    assert isinstance(light[ColorRole.PRIMARY], str) and light[ColorRole.PRIMARY].startswith("#")
    assert isinstance(dark[ColorRole.PRIMARY], str) and dark[ColorRole.PRIMARY].startswith("#")
