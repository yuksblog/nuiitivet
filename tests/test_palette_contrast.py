from nuiitivet.theme import Theme
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.colors.utils import passes_wcag


def _check_theme_contrast(theme: Theme) -> None:
    mat = theme.extension(MaterialThemeData)
    assert mat is not None
    # primary / onPrimary should meet AA normal text (4.5)
    p = mat.roles.get(ColorRole.PRIMARY)
    onp = mat.roles.get(ColorRole.ON_PRIMARY)
    assert p is not None and onp is not None, "missing primary/onPrimary"
    assert passes_wcag(onp, p, level="AA", large=False), f"primary/onPrimary fail: {onp}/{p}"

    # surface / onSurface should meet AA normal text
    s = mat.roles.get(ColorRole.SURFACE)
    ons = mat.roles.get(ColorRole.ON_SURFACE)
    assert s is not None and ons is not None, "missing surface/onSurface"
    assert passes_wcag(ons, s, level="AA", large=False), f"surface/onSurface fail: {ons}/{s}"


def test_several_seeds_meet_contrast():
    seeds = ["#6750A4", "#FF0000", "#00FF00", "#0000FF", "#808080"]
    for seed in seeds:
        light, dark = MaterialTheme.from_seed_pair(seed)
        _check_theme_contrast(light)
        _check_theme_contrast(dark)
