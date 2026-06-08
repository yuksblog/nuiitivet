"""Material Widgets - SplitButton demo.

Demonstrates the M3 Expressive SplitButton with:
- Multiple size and variant presets displayed statically.
- An interactive split button where the trailing button opens a menu,
  and selecting a menu item changes the leading button label.
"""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Menu, MenuItem, Text
from nuiitivet.material.split_button import SplitButton
from nuiitivet.material.styles.split_button_style import SplitButtonStyle
from nuiitivet.modifiers import light_dismiss
from nuiitivet.observable import Observable

# ---------------------------------------------------------------------------
# Interactive demo state
# ---------------------------------------------------------------------------

_ACTIONS = ["Start driving", "Navigate home", "Navigate to work", "Explore nearby"]

_label: Observable[str] = Observable(_ACTIONS[0])
_menu_open: Observable[bool] = Observable(False)


def _close_menu() -> None:
    _menu_open.value = False


def _select_action(action: str) -> None:
    _label.value = action
    _close_menu()


def _make_interactive_split_button() -> SplitButton:
    """Build the interactive SplitButton bound to module-level observables."""
    return SplitButton(
        _label,
        icon="directions_car",
        on_click=lambda: print(f"Action: {_label.value}"),
        on_menu_toggle=lambda open: setattr(_menu_open, "value", open),
        menu_open=_menu_open,
        style=SplitButtonStyle.filled("s"),
    )


def _make_menu() -> Menu:
    """Build the dropdown menu for the interactive split button."""
    return Menu(
        items=[MenuItem(a, on_click=lambda a=a: _select_action(a)) for a in _ACTIONS],
        on_dismiss=_close_menu,
    )


# ---------------------------------------------------------------------------
# Interactive main content (uses overlay — for app.run())
# ---------------------------------------------------------------------------


def _build_interactive_content() -> Container:
    split_btn = _make_interactive_split_button()
    menu = _make_menu()

    # Attach the menu as a light-dismiss popup anchored to the split button's
    # trailing edge.  The menu aligns its top-left corner to the bottom-right
    # of the split button with a 4dp gap.
    anchored = split_btn.modifier(
        light_dismiss(
            menu,
            is_open=_menu_open,
            alignment="bottom-right",
            anchor="top-right",
            offset=(0.0, 4.0),
        )
    )

    return Container(
        padding=24,
        child=Column(
            gap=24,
            cross_alignment="start",
            children=[
                Text("Interactive — click the trailing button to open the menu"),
                anchored,
                Text("Style variants (Small)"),
                Row(
                    gap=8,
                    children=[
                        SplitButton("Filled", icon="star", style=SplitButtonStyle.filled("s")),
                        SplitButton("Tonal", icon="star", style=SplitButtonStyle.tonal("s")),
                        SplitButton("Elevated", icon="star", style=SplitButtonStyle.elevated("s")),
                        SplitButton("Outlined", icon="star", style=SplitButtonStyle.outlined("s")),
                    ],
                ),
                Text("Size variants (filled)"),
                Row(
                    gap=8,
                    cross_alignment="center",
                    children=[
                        SplitButton("XS", style=SplitButtonStyle.filled("xs")),
                        SplitButton("S", style=SplitButtonStyle.filled("s")),
                        SplitButton("M", style=SplitButtonStyle.filled("m")),
                    ],
                ),
            ],
        ),
    )


# ---------------------------------------------------------------------------
# PNG screenshot content (static — overlay not captured by render_to_png)
# ---------------------------------------------------------------------------


def _build_png_content() -> Container:
    """Build a static layout suitable for PNG rendering.

    Uses a Column showing the split button above a static menu to mimic the
    open-menu state since overlays are not captured by ``render_to_png``.
    """
    return Container(
        padding=24,
        child=Column(
            gap=20,
            cross_alignment="start",
            children=[
                Text("Style variants"),
                Row(
                    gap=8,
                    children=[
                        SplitButton("Filled", icon="star", style=SplitButtonStyle.filled("s")),
                        SplitButton("Tonal", icon="star", style=SplitButtonStyle.tonal("s")),
                        SplitButton("Elevated", icon="star", style=SplitButtonStyle.elevated("s")),
                        SplitButton("Outlined", icon="star", style=SplitButtonStyle.outlined("s")),
                    ],
                ),
                Text("Size variants (filled)"),
                Row(
                    gap=8,
                    cross_alignment="center",
                    children=[
                        SplitButton("XS", style=SplitButtonStyle.filled("xs")),
                        SplitButton("S", style=SplitButtonStyle.filled("s")),
                        SplitButton("M", style=SplitButtonStyle.filled("m")),
                        SplitButton("L", style=SplitButtonStyle.filled("l")),
                    ],
                ),
                Text("With menu open (static preview)"),
                Row(
                    gap=8,
                    cross_alignment="start",
                    children=[
                        Column(
                            gap=4,
                            cross_alignment="start",
                            children=[
                                SplitButton(
                                    "Start driving",
                                    icon="directions_car",
                                    menu_open=True,
                                    style=SplitButtonStyle.filled("s"),
                                ),
                                Menu(
                                    items=[
                                        MenuItem("Start driving"),
                                        MenuItem("Navigate home"),
                                        MenuItem("Navigate to work"),
                                        MenuItem("Explore nearby"),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(png_path: str = "") -> None:
    """Run the SplitButton demo.

    Args:
        png_path: If non-empty, render a static PNG to this path instead of
            opening the interactive window.
    """
    if png_path:
        app = App(
            content=_build_png_content(),
            title="SplitButton",
            width=760,
            height=600,
        )
        app.render_to_png(png_path)
    else:
        app = App(
            content=_build_interactive_content(),
            title="SplitButton",
            width=760,
            height=420,
        )
        app.run()


if __name__ == "__main__":
    main()
