import nuiitivet.theme as theme
from nuiitivet.material.theme.material_theme import MaterialTheme


def test_manager_set_theme_manual_toggle():
    """Test that theme can be manually toggled by setting new Theme instances."""
    old = theme.manager.current
    try:
        # Create explicit themes
        seed = "#6750A4"
        light_theme = MaterialTheme.light(seed)
        dark_theme = MaterialTheme.dark(seed)

        # Apply dark
        theme.manager.set_theme(dark_theme)
        assert theme.manager.current.mode == "dark"
        assert theme.manager.current == dark_theme

        # Apply light
        theme.manager.set_theme(light_theme)
        assert theme.manager.current.mode == "light"
        assert theme.manager.current == light_theme

    finally:
        # restore original theme
        try:
            theme.manager.set_theme(old)
        except Exception:
            pass


def test_manager_subscription():
    """Test that subscribers are notified when theme changes."""
    old = theme.manager.current
    notifications = []

    def on_theme_change(new_theme):
        notifications.append(new_theme)

    theme.manager.subscribe(on_theme_change)

    try:
        new_theme = MaterialTheme.light("#000000")
        theme.manager.set_theme(new_theme)

        assert len(notifications) == 1
        assert notifications[0] == new_theme

    finally:
        theme.manager.unsubscribe(on_theme_change)
        theme.manager.set_theme(old)
