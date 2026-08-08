"""Material Widgets - SplitButton demo.

Demonstrates the M3 Expressive SplitButton with:
- Multiple size and variant presets displayed statically.
- An interactive split button where the trailing button opens a menu,
  and selecting a menu item changes the leading button label.
"""

from __future__ import annotations

from typing import Callable

import nuiitivet.material as nv

# ---------------------------------------------------------------------------
# Interactive demo state
# ---------------------------------------------------------------------------

_ACTIONS = ["Start driving", "Navigate home", "Navigate to work", "Explore nearby"]

_label: nv.Observable[str] = nv.Observable(_ACTIONS[0])
_menu_open: nv.Observable[bool] = nv.Observable(False)


def _close_menu() -> None:
    _menu_open.value = False


def _select_action(action: str) -> None:
    _label.value = action
    _close_menu()


def _make_interactive_split_button() -> nv.SplitButton:
    """Build the interactive SplitButton bound to module-level observables."""
    return nv.SplitButton(
        _label,
        icon="directions_car",
        on_click=lambda: print(f"Action: {_label.value}"),
        on_menu_toggle=lambda open: _menu_open.set(open),
        menu_open=_menu_open,
        style=nv.SplitButtonStyle.filled("s"),
    )


def _make_action_callback(action: str) -> Callable[[], None]:
    return lambda: _select_action(action)


def _make_menu() -> nv.Menu:
    """Build the dropdown menu for the interactive split button."""
    return nv.Menu(
        items=[nv.MenuItem(a, on_click=_make_action_callback(a)) for a in _ACTIONS],
        on_dismiss=_close_menu,
    )


# ---------------------------------------------------------------------------
# Interactive main content (uses overlay — for app.run())
# ---------------------------------------------------------------------------


def _build_interactive_content() -> nv.Container:
    split_btn = _make_interactive_split_button()
    menu = _make_menu()

    # Attach the menu as a light-dismiss popup anchored to the split button's
    # trailing edge.  The menu aligns its top-left corner to the bottom-right
    # of the split button with a 4dp gap.
    anchored = split_btn.modifier(
        nv.light_dismiss(
            menu,
            is_open=_menu_open,
            target_anchor="bottom-right",
            content_anchor="top-right",
            offset=(0.0, 4.0),
        )
    )

    return nv.Container(
        padding=24,
        child=nv.Column(
            gap=24,
            cross_alignment="start",
            children=[
                nv.Text("Interactive — click the trailing button to open the menu"),
                anchored,
                nv.Text("Style variants (Small)"),
                nv.Row(
                    gap=8,
                    children=[
                        nv.SplitButton("Filled", icon="star", style=nv.SplitButtonStyle.filled("s")),
                        nv.SplitButton("Tonal", icon="star", style=nv.SplitButtonStyle.tonal("s")),
                        nv.SplitButton("Elevated", icon="star", style=nv.SplitButtonStyle.elevated("s")),
                        nv.SplitButton("Outlined", icon="star", style=nv.SplitButtonStyle.outlined("s")),
                    ],
                ),
                nv.Text("Size variants (filled)"),
                nv.Row(
                    gap=8,
                    cross_alignment="center",
                    children=[
                        nv.SplitButton("XS", style=nv.SplitButtonStyle.filled("xs")),
                        nv.SplitButton("S", style=nv.SplitButtonStyle.filled("s")),
                        nv.SplitButton("M", style=nv.SplitButtonStyle.filled("m")),
                    ],
                ),
            ],
        ),
    )


# ---------------------------------------------------------------------------
# PNG screenshot content (static — overlay not captured by render_to_png)
# ---------------------------------------------------------------------------


def _build_png_content() -> nv.Container:
    """Build a static layout suitable for PNG rendering.

    Uses a Column showing the split button above a static menu to mimic the
    open-menu state since overlays are not captured by ``render_to_png``.
    """
    return nv.Container(
        padding=24,
        child=nv.Column(
            gap=20,
            cross_alignment="start",
            children=[
                nv.Text("Style variants"),
                nv.Row(
                    gap=8,
                    children=[
                        nv.SplitButton("Filled", icon="star", style=nv.SplitButtonStyle.filled("s")),
                        nv.SplitButton("Tonal", icon="star", style=nv.SplitButtonStyle.tonal("s")),
                        nv.SplitButton("Elevated", icon="star", style=nv.SplitButtonStyle.elevated("s")),
                        nv.SplitButton("Outlined", icon="star", style=nv.SplitButtonStyle.outlined("s")),
                    ],
                ),
                nv.Text("Size variants (filled)"),
                nv.Row(
                    gap=8,
                    cross_alignment="center",
                    children=[
                        nv.SplitButton("XS", style=nv.SplitButtonStyle.filled("xs")),
                        nv.SplitButton("S", style=nv.SplitButtonStyle.filled("s")),
                        nv.SplitButton("M", style=nv.SplitButtonStyle.filled("m")),
                        nv.SplitButton("L", style=nv.SplitButtonStyle.filled("l")),
                    ],
                ),
                nv.Text("With menu open (static preview)"),
                nv.Row(
                    gap=8,
                    cross_alignment="start",
                    children=[
                        nv.Column(
                            gap=4,
                            cross_alignment="start",
                            children=[
                                nv.SplitButton(
                                    "Start driving",
                                    icon="directions_car",
                                    menu_open=True,
                                    style=nv.SplitButtonStyle.filled("s"),
                                ),
                                nv.Menu(
                                    items=[
                                        nv.MenuItem("Start driving"),
                                        nv.MenuItem("Navigate home"),
                                        nv.MenuItem("Navigate to work"),
                                        nv.MenuItem("Explore nearby"),
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
        app = nv.App(
            content=_build_png_content(),
            title="SplitButton",
            width=760,
            height=600,
        )
        app.render_to_png(png_path)
    else:
        app = nv.App(
            content=_build_interactive_content(),
            title="SplitButton",
            width=760,
            height=420,
        )
        app.run()


if __name__ == "__main__":
    main()
