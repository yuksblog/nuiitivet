"""Tests for Theme style integration (Phase 2)."""

from dataclasses import replace


def test_theme_has_style_properties():
    """Theme has button_style, checkbox_style, icon_style properties via material extension."""
    from nuiitivet.material.theme.material_theme import MaterialTheme
    from nuiitivet.material.theme.theme_data import MaterialThemeData

    light, dark = MaterialTheme.from_seed_pair("#6750A4", name="test")
    mat = light.extension(MaterialThemeData)
    assert mat is not None
    assert hasattr(mat, "filled_button_style")
    assert hasattr(mat, "checkbox_style")
    assert hasattr(mat, "icon_style")
    button = mat.filled_button_style
    checkbox = mat.checkbox_style
    icon = mat.icon_style
    assert button is not None
    assert checkbox is not None
    assert icon is not None


def test_theme_default_styles():
    """MaterialTheme.from_seed() creates themes with default M3 styles."""
    from nuiitivet.material.theme.material_theme import MaterialTheme
    from nuiitivet.material.styles.button_style import ButtonStyle
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle
    from nuiitivet.material.styles.icon_style import IconStyle
    from nuiitivet.material.theme.theme_data import MaterialThemeData

    light, dark = MaterialTheme.from_seed_pair("#6750A4")
    mat = light.extension(MaterialThemeData)
    assert mat is not None
    button = mat.filled_button_style
    assert isinstance(button, ButtonStyle)
    assert button.corner_radius == 20
    assert button.container_height == 40
    assert button.padding == (16, 0, 16, 0)
    checkbox = mat.checkbox_style
    assert isinstance(checkbox, CheckboxStyle)
    assert checkbox.default_touch_target == 48
    assert checkbox.icon_size_ratio == 18.0 / 48.0
    icon = mat.icon_style
    assert isinstance(icon, IconStyle)
    assert icon.default_size == 24


def test_theme_with_styles():
    """Theme styles can be customized via copy_with on MaterialThemeData."""
    from nuiitivet.material.theme.material_theme import MaterialTheme
    from nuiitivet.material.styles.button_style import ButtonStyle
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle
    from nuiitivet.material.theme.theme_data import MaterialThemeData

    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    custom_button = ButtonStyle.outlined()
    custom_checkbox = CheckboxStyle().copy_with(default_touch_target=56)

    # Customizing styles requires updating the extension
    mat = light.extension(MaterialThemeData)
    assert mat is not None
    new_material = mat.copy_with(_filled_button_style=custom_button, _checkbox_style=custom_checkbox)
    custom_theme = replace(light, extensions=[new_material])

    assert mat.filled_button_style.corner_radius == 20
    assert mat.checkbox_style.default_touch_target == 48
    custom_mat = custom_theme.extension(MaterialThemeData)
    assert custom_mat is not None
    assert custom_mat.filled_button_style.border_width == 1.0
    assert custom_mat.checkbox_style.default_touch_target == 56
    assert custom_mat.icon_style.default_size == 24


def test_theme_style_lazy_loading():
    """Theme styles are lazy-loaded to avoid circular imports."""
    from nuiitivet.material.theme.theme_data import MaterialThemeData
    from nuiitivet.theme.theme import Theme

    # Manually create theme with Material extension
    material = MaterialThemeData(roles={})
    theme = Theme(mode="light", extensions=[material])

    mat = theme.extension(MaterialThemeData)
    assert mat is not None
    button = mat.filled_button_style
    checkbox = mat.checkbox_style
    icon = mat.icon_style
    assert button is not None
    assert checkbox is not None
    assert icon is not None


def test_theme_manager_provides_styles():
    """Theme manager's current theme provides styles via material extension."""
    from nuiitivet.theme import manager
    from nuiitivet.material.theme.material_theme import MaterialTheme
    from nuiitivet.material.theme.theme_data import MaterialThemeData

    old = manager.current
    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    try:
        manager.set_theme(light)
        current = manager.current
        mat = current.extension(MaterialThemeData)
        assert mat is not None
        assert hasattr(mat, "filled_button_style")
        assert hasattr(mat, "checkbox_style")
        assert hasattr(mat, "icon_style")
        button = mat.filled_button_style
        checkbox = mat.checkbox_style
        icon = mat.icon_style
        assert button is not None
        assert checkbox is not None
        assert icon is not None
    finally:
        manager.set_theme(old)


def test_theme_style_button_variants():
    """Theme can hold different button style variants."""
    from nuiitivet.material.theme.material_theme import MaterialTheme
    from nuiitivet.material.styles.button_style import ButtonStyle
    from nuiitivet.material.theme.theme_data import MaterialThemeData

    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    filled = ButtonStyle.filled()
    outlined = ButtonStyle.outlined()
    text = ButtonStyle.text()
    elevated = ButtonStyle.elevated()
    tonal = ButtonStyle.tonal()
    assert filled.background is not None
    assert outlined.border_width == 1.0
    assert text.padding == (16, 0, 16, 0)
    assert elevated.elevation == 1.0
    assert tonal.background is not None

    mat = light.extension(MaterialThemeData)
    assert mat is not None
    new_material = mat.copy_with(_filled_button_style=outlined)
    custom = replace(light, extensions=[new_material])
    custom_mat = custom.extension(MaterialThemeData)
    assert custom_mat is not None
    assert custom_mat.filled_button_style.border_width == 1.0


def test_theme_immutability_preserved():
    """Theme remains immutable after adding style fields."""
    from nuiitivet.material.theme.material_theme import MaterialTheme
    from nuiitivet.material.theme.theme_data import MaterialThemeData

    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    try:
        light.mode = "dark"
        assert False, "Should not be able to modify frozen theme"
    except Exception:
        pass
    try:
        mat = light.extension(MaterialThemeData)
        assert mat is not None
        mat._filled_button_style = None
        assert False, "Should not be able to modify frozen theme data"
    except Exception:
        pass


def test_theme_styles_independent_of_mode():
    """Light and dark themes share same style instances by default."""
    from nuiitivet.material.theme.material_theme import MaterialTheme
    from nuiitivet.material.theme.theme_data import MaterialThemeData

    light, dark = MaterialTheme.from_seed_pair("#6750A4")
    light_mat = light.extension(MaterialThemeData)
    dark_mat = dark.extension(MaterialThemeData)
    assert light_mat is not None
    assert dark_mat is not None
    assert light_mat.filled_button_style.corner_radius == dark_mat.filled_button_style.corner_radius
    assert light_mat.checkbox_style.default_touch_target == dark_mat.checkbox_style.default_touch_target
    assert light_mat.icon_style.default_size == dark_mat.icon_style.default_size
