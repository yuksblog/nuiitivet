from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.theme_data import MaterialThemeData


def test_theme_from_seed_generates_both_modes():
    light, dark = MaterialTheme.from_seed_pair("#6750A4")
    # basic checks
    assert light.mode == "light"
    assert dark.mode == "dark"
    # must have primary color keys and they should differ between modes
    from nuiitivet.material.theme.color_role import ColorRole

    light_mat = light.extension(MaterialThemeData)
    dark_mat = dark.extension(MaterialThemeData)
    assert light_mat is not None
    assert dark_mat is not None
    lp = light_mat.roles.get(ColorRole.PRIMARY)
    dp = dark_mat.roles.get(ColorRole.PRIMARY)
    assert isinstance(lp, str) and isinstance(dp, str)
    assert lp != dp
