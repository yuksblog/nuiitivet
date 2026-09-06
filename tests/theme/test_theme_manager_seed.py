from nuiitivet.theme.manager import ThemeManager
from nuiitivet.material.theme.material_theme import MaterialThemeFactory


def test_manager_set_theme_manual_toggle():
    """Test that theme can be manually toggled by setting new Theme instances."""
    mgr = ThemeManager()
    seed = "#6750A4"
    light_theme = MaterialThemeFactory.light(seed)
    dark_theme = MaterialThemeFactory.dark(seed)

    mgr.set_theme(dark_theme)
    assert mgr.current.mode == "dark"
    assert mgr.current == dark_theme

    mgr.set_theme(light_theme)
    assert mgr.current.mode == "light"
    assert mgr.current == light_theme


def test_manager_notifies_its_owner():
    """The owning provider -- not the widgets -- is told about a theme change."""
    mgr = ThemeManager()
    notifications = []
    mgr.on_change = notifications.append

    new_theme = MaterialThemeFactory.light("#000000")
    mgr.set_theme(new_theme)

    assert len(notifications) == 1
    assert notifications[0] == new_theme


def test_manager_bumps_its_generation_on_every_change():
    """The counter lets anything derived from the theme tell it has moved."""
    mgr = ThemeManager()
    start = mgr.generation

    mgr.set_theme(MaterialThemeFactory.light("#000000"))
    mgr.set_theme(MaterialThemeFactory.light("#111111"))

    assert mgr.generation == start + 2


def test_manager_without_an_initial_theme_starts_light():
    manager = ThemeManager()

    assert manager.current.mode == "light"
    assert manager.current is manager.current
