"""Comprehensive Style and Theme customization demo.

Demonstrates:
- Theme customization via MaterialThemeData for global style customization
- Individual widget style parameters
- Style.copy_with() for fine-grained customization
- Visual comparison of default vs custom styles
"""

from dataclasses import replace
from nuiitivet.material.app import MaterialApp
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Text
from nuiitivet.material import Checkbox
from nuiitivet.material.icon import Icon
from nuiitivet.material.buttons import FilledButton
from nuiitivet.material.styles import ButtonStyle, CheckboxStyle, IconStyle, TextStyle
from nuiitivet.theme import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.material.theme.theme_data import MaterialThemeData


def main():
    light, _ = MaterialTheme.from_seed_pair("#6750A4", name="Base Theme")
    custom_checkbox = CheckboxStyle(
        default_touch_target=56,
        icon_size_ratio=0.5,
        hover_alpha=0.15,
        pressed_alpha=0.25,
    )
    custom_icon = IconStyle(
        default_size=32,
        color=ColorRole.SECONDARY,
        font_family_priority=(
            "Material Symbols Rounded",
            "Material Symbols Outlined",
        ),
    )
    custom_button = ButtonStyle.tonal()

    mat = light.extension(MaterialThemeData)
    if mat is None:
        raise ValueError("MaterialThemeData not found in theme extensions")

    new_material = mat.copy_with(_checkbox_style=custom_checkbox, _icon_style=custom_icon, _button_style=custom_button)
    custom_theme = replace(light, extensions=[new_material])

    manager.set_theme(custom_theme)
    children = [
        Text("Style & Theme Customization Demo", style=TextStyle(color=ColorRole.PRIMARY), padding=(0, 0, 0, 16)),
        Text("1. Theme-level Styles (via MaterialThemeData)", style=TextStyle(color=ColorRole.ON_SURFACE)),
        Row(gap=16, children=[Checkbox(checked=True), Text("Larger checkbox (56px touch target, 0.5 icon ratio)")]),
        Row(gap=16, children=[Icon("favorite"), Text("Larger icon (32px, rounded, secondary color)")]),
        Row(gap=16, children=[FilledButton(label="Theme Button"), Text("Tonal button (from theme default)")]),
        Text("", height=Sizing.fixed(20)),
        Text("2. Per-Widget Style Override", style=TextStyle(color=ColorRole.ON_SURFACE)),
        Row(
            gap=16,
            children=[
                Checkbox(
                    checked=True,
                    style=CheckboxStyle(default_touch_target=40, icon_size_ratio=0.3, hover_alpha=0.05),
                ),
                Text("Smaller checkbox (40px, 0.3 ratio, subtle hover)"),
            ],
        ),
        Row(
            gap=16,
            children=[
                Icon("star", style=IconStyle(default_size=48, color=ColorRole.TERTIARY)),
                Text("Large star icon (48px, tertiary color)"),
            ],
        ),
        Row(
            gap=16,
            children=[
                FilledButton(label="Outlined", button_style=ButtonStyle.outlined()),
                Text("Outlined button (overrides theme tonal)"),
            ],
        ),
        Text("", height=Sizing.fixed(20)),
        Text("3. Style.copy_with() Customization", style=TextStyle(color=ColorRole.ON_SURFACE)),
        Row(
            gap=16,
            children=[
                Checkbox(checked=True, style=CheckboxStyle().copy_with(hover_alpha=0.2, pressed_alpha=0.3)),
                Text("Default size, custom hover/press alpha"),
            ],
        ),
        Row(
            gap=16,
            children=[
                FilledButton(
                    label="Custom",
                    button_style=ButtonStyle.filled().copy_with(
                        background=ColorRole.ERROR, foreground=ColorRole.ON_ERROR
                    ),
                ),
                Text("Filled button with error colors"),
            ],
        ),
        Text(
            "\nℹ️ All widgets support optional style parameters",
            style=TextStyle(color=ColorRole.ON_SURFACE_VARIANT),
            padding=(0, 20, 0, 0),
        ),
        Text("• No style param → uses Theme default", style=TextStyle(color=ColorRole.ON_SURFACE_VARIANT)),
        Text("• With style param → uses provided style", style=TextStyle(color=ColorRole.ON_SURFACE_VARIANT)),
        Text("• copy_with() → customizes existing style", style=TextStyle(color=ColorRole.ON_SURFACE_VARIANT)),
    ]
    root = Column(gap=16, padding=20, children=children)
    app = MaterialApp(content=root)
    app.run()


if __name__ == "__main__":
    main()
