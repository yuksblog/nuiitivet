from nuiitivet.theme.manager import ThemeManager
from nuiitivet.material.theme.material_theme import MaterialTheme


def test_manager_set_theme_manual_toggle():
    """Test that theme can be manually toggled by setting new Theme instances."""
    mgr = ThemeManager()
    seed = "#6750A4"
    light_theme = MaterialTheme.light(seed)
    dark_theme = MaterialTheme.dark(seed)

    mgr.set_theme(dark_theme)
    assert mgr.current.mode == "dark"
    assert mgr.current == dark_theme

    mgr.set_theme(light_theme)
    assert mgr.current.mode == "light"
    assert mgr.current == light_theme


def test_manager_subscription():
    """Test that subscribers are notified when theme changes."""
    mgr = ThemeManager()
    notifications = []

    def on_theme_change(new_theme):
        notifications.append(new_theme)

    mgr.subscribe(on_theme_change)

    new_theme = MaterialTheme.light("#000000")
    mgr.set_theme(new_theme)

    assert len(notifications) == 1
    assert notifications[0] == new_theme

    mgr.unsubscribe(on_theme_change)
