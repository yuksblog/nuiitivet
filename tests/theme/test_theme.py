from nuiitivet.theme import Theme, ThemeManager
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData


def test_theme_get_and_notify_owner():
    # create a small theme and manager to avoid mutating module-level state
    roles = {ColorRole.PRIMARY: "#111111"}
    t = Theme(mode="light", extensions=[MaterialThemeData(roles=roles)])
    m = ThemeManager(t)

    mat = m.current.extension(MaterialThemeData)
    assert mat is not None
    assert mat.roles.get(ColorRole.PRIMARY) == "#111111"

    called = []

    # One owner hook, not a subscriber list: widgets never register here.
    m.on_change = lambda theme: called.append(theme.mode)

    t2 = Theme(mode="dark", extensions=[MaterialThemeData(roles={ColorRole.PRIMARY: "#222222"})])
    m.set_theme(t2)
    assert called == ["dark"]
    mat2 = m.current.extension(MaterialThemeData)
    assert mat2 is not None
    assert mat2.roles.get(ColorRole.PRIMARY) == "#222222"


def test_theme_manager_offers_no_subscriber_registry():
    """A provider that held consumer references is what this design removes."""
    m = ThemeManager(Theme(mode="light", extensions=[]))

    assert not hasattr(m, "subscribe")
    assert not hasattr(m, "unsubscribe")
    assert not hasattr(m, "_subscribers")
