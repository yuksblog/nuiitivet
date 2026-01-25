from nuiitivet.theme import Theme, ThemeManager
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData


def test_theme_get_and_subscribe():
    # create a small theme and manager to avoid mutating module-level state
    roles = {ColorRole.PRIMARY: "#111111"}
    t = Theme(mode="light", extensions=[MaterialThemeData(roles=roles)])
    m = ThemeManager(t)

    mat = m.current.extension(MaterialThemeData)
    assert mat is not None
    assert mat.roles.get(ColorRole.PRIMARY) == "#111111"

    called = []

    def on_change(theme):
        called.append(theme.mode)

    m.subscribe(on_change)
    t2 = Theme(mode="dark", extensions=[MaterialThemeData(roles={ColorRole.PRIMARY: "#222222"})])
    m.set_theme(t2)
    assert called == ["dark"]
    mat2 = m.current.extension(MaterialThemeData)
    assert mat2 is not None
    assert mat2.roles.get(ColorRole.PRIMARY) == "#222222"
