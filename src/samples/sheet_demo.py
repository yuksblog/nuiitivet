"""Modal SideSheet and BottomSheet demo.

Covers:
- Right-side sheet (default style)
- Left-side sheet (custom width)
- Bottom sheet with fixed height
- Bottom sheet with content-driven height (default)
- Non-dismissible side sheet with on_close callback
- Side sheet with dynamic Back button driven by MutableObservable
"""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material import (
    Divider,
    FilledButton,
    App,
    Overlay,
    OutlinedButton,
    Text,
)
from nuiitivet.material.sheet import BottomSheet, SideSheet
from nuiitivet.material.styles.sheet_style import BottomSheetStyle, SideSheetStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.observable import Observable
from nuiitivet.widgets.box import Box


# ---------------------------------------------------------------------------
# Sheet content builders
# ---------------------------------------------------------------------------


def _sheet_content(label: str) -> Box:
    return Box(
        Column(
            children=[
                Text(label, style=TextStyle(font_size=16)),
                Divider(),
                Text("Item 1"),
                Text("Item 2"),
                Text("Item 3"),
                Text("Tap outside (scrim) to dismiss."),
            ],
            gap=12,
            cross_alignment="start",
        ),
        padding=24,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    def open_right_sheet() -> None:
        """Right-side sheet — default SideSheetStyle (width=400)."""
        Overlay.root().side_sheet(
            SideSheet(_sheet_content("Right Side Sheet"), headline="Settings"),
        )

    def open_left_sheet() -> None:
        """Left-side sheet — custom width."""
        Overlay.root().side_sheet(
            SideSheet(
                _sheet_content("Left Side Sheet"),
                headline="Navigation",
                side="left",
                style=SideSheetStyle(width=320),
            ),
        )

    def open_bottom_sheet_fixed() -> None:
        """Bottom sheet — fixed height."""
        Overlay.root().bottom_sheet(
            BottomSheet(
                _sheet_content("Bottom Sheet (height=280)"),
                headline="Filter",
                style=BottomSheetStyle(height=280),
            ),
        )

    def open_bottom_sheet_auto() -> None:
        """Bottom sheet — content-driven height (default)."""
        Overlay.root().bottom_sheet(
            BottomSheet(
                _sheet_content("Bottom Sheet (content-driven)"),
                headline="Filter",
            ),
        )

    def open_non_dismissible_sheet() -> None:
        """Right-side sheet — dismiss_on_outside_tap=False, close via on_close callback."""
        handle = Overlay.root().side_sheet(
            SideSheet(
                _sheet_content("Non-Dismissible Sheet"),
                headline="Edit",
                on_close=lambda: handle.close(None),
            ),
            dismiss_on_outside_tap=False,
        )

    def open_dynamic_back_sheet() -> None:
        """Side sheet with dynamic Back button driven by MutableObservable."""
        _show_back: Observable[bool] = Observable(False)

        def go_back() -> None:
            _show_back.value = False

        def navigate_detail() -> None:
            _show_back.value = True

        content = Box(
            Column(
                children=[
                    Divider(),
                    Text("Press the button below to simulate navigation."),
                    OutlinedButton("Go to detail →", on_click=navigate_detail),
                ],
                gap=12,
                cross_alignment="start",
            ),
            padding=24,
        )

        Overlay.root().side_sheet(
            SideSheet(
                content,
                headline="Settings",
                on_back=go_back,
                show_back_button=_show_back,
            ),
        )

    content = Container(
        child=Column(
            children=[
                Text("Sheet Demo", style=TextStyle(font_size=22)),
                Divider(),
                Row(
                    children=[
                        FilledButton("Right Sheet (default)", on_click=open_right_sheet),
                        FilledButton("Left Sheet (w=320)", on_click=open_left_sheet),
                    ],
                    gap=12,
                ),
                Row(
                    children=[
                        FilledButton("Bottom Sheet (h=280)", on_click=open_bottom_sheet_fixed),
                        FilledButton("Bottom Sheet (auto)", on_click=open_bottom_sheet_auto),
                    ],
                    gap=12,
                ),
                FilledButton("Non-dismissible Sheet", on_click=open_non_dismissible_sheet),
                FilledButton("Dynamic Back Button", on_click=open_dynamic_back_sheet),
            ],
            gap=20,
            cross_alignment="start",
        ),
        padding=32,
    )

    app = App(content=content, width=600, height=420)
    app.run()


if __name__ == "__main__":
    main()
