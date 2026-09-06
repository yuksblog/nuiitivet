"""``resolve_color_to_rgba`` accepts literals, tokens, ``(base, alpha)`` pairs
and a caller-supplied role hook, in that order of preference."""

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.theme import Theme


class _Alias:
    """A token that resolves to another token."""

    def resolve(self, theme=None):  # type: ignore[no-untyped-def]
        return ColorRole.PRIMARY


class _Broken:
    def resolve(self, theme=None):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")


def _theme() -> Theme:
    return MaterialThemeFactory.light("#6750A4")


def _primary(theme: Theme) -> tuple[int, int, int, int]:
    mat = theme.extension(MaterialThemeData)
    assert mat is not None
    return resolve_color_to_rgba(mat.roles[ColorRole.PRIMARY])


def test_literals_resolve_without_a_theme() -> None:
    assert resolve_color_to_rgba("#102030") == (16, 32, 48, 255)
    assert resolve_color_to_rgba("#10203080") == (16, 32, 48, 128)
    assert resolve_color_to_rgba((1, 2, 3)) == (1, 2, 3, 255)
    assert resolve_color_to_rgba((1, 2, 3, 4)) == (1, 2, 3, 4)
    assert resolve_color_to_rgba(0x102030) == (16, 32, 48, 255)
    assert resolve_color_to_rgba("red") == (255, 0, 0, 255)


def test_a_token_resolves_through_the_theme() -> None:
    theme = _theme()
    assert resolve_color_to_rgba(ColorRole.PRIMARY, theme=theme) == _primary(theme)


def test_a_token_resolving_to_a_token_is_followed() -> None:
    theme = _theme()
    assert resolve_color_to_rgba(_Alias(), theme=theme) == _primary(theme)


def test_a_pair_multiplies_the_resolved_alpha() -> None:
    theme = _theme()
    r, g, b, _ = _primary(theme)
    assert resolve_color_to_rgba((ColorRole.PRIMARY, 0.5), theme=theme) == (r, g, b, 127)
    assert resolve_color_to_rgba(("#10203080", 0.5)) == (16, 32, 48, 64)
    assert resolve_color_to_rgba(((1, 2, 3, 200), 0.5)) == (1, 2, 3, 100)


def test_an_unresolvable_value_falls_back_to_default_then_transparent() -> None:
    assert resolve_color_to_rgba(None, default="#ffffff") == (255, 255, 255, 255)
    assert resolve_color_to_rgba(ColorRole.PRIMARY, default="#ffffff") == (255, 255, 255, 255)
    assert resolve_color_to_rgba(_Broken(), default="#ffffff") == (255, 255, 255, 255)
    assert resolve_color_to_rgba(None) == (0, 0, 0, 0)
    assert resolve_color_to_rgba(object()) == (0, 0, 0, 0)


def test_the_role_hook_is_the_last_resort() -> None:
    seen = []

    def hook(value):  # type: ignore[no-untyped-def]
        seen.append(value)
        return "#010203"

    assert resolve_color_to_rgba("#ffffff", role_resolver=hook) == (255, 255, 255, 255)
    assert seen == []
    assert resolve_color_to_rgba(ColorRole.PRIMARY, role_resolver=hook) == (1, 2, 3, 255)
    assert resolve_color_to_rgba((ColorRole.PRIMARY, 0.5), role_resolver=hook) == (1, 2, 3, 127)
    assert seen == [ColorRole.PRIMARY, ColorRole.PRIMARY]
