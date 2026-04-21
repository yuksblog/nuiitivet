"""Visual demo for Material Design 3 toolbar widgets."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import DockedToolbar, FloatingToolbar, Text
from nuiitivet.material import App
from nuiitivet.material.buttons import IconButton
from nuiitivet.material.styles import IconButtonStyle, ToolbarStyle
from nuiitivet.widgets.box import Box


class ToolbarDemoWidget:
    """Widget builder for toolbar demo."""

    def _standard_actions(self) -> list[IconButton]:
        return [
            IconButton("menu", style=IconButtonStyle.standard()),
            IconButton("search", style=IconButtonStyle.standard()),
            IconButton("favorite", style=IconButtonStyle.filled()),
            IconButton("more_vert", style=IconButtonStyle.outlined()),
        ]

    def _vibrant_actions(self) -> list[IconButton]:
        return [
            IconButton("menu", style=IconButtonStyle.vibrant()),
            IconButton("search", style=IconButtonStyle.vibrant()),
            IconButton("favorite", style=IconButtonStyle.filled_vibrant()),
            IconButton("more_vert", style=IconButtonStyle.outlined_vibrant()),
        ]

    def build(self) -> Box:
        """Build demo widget tree."""
        demo_width = 560

        docked_standard = DockedToolbar(
            self._standard_actions(),
            style=ToolbarStyle.standard().copy_with(border_color="#D0D4DA", border_width=1.0),
        )
        docked_standard.width_sizing = demo_width

        docked_vibrant = DockedToolbar(
            self._vibrant_actions(),
            style=ToolbarStyle.vibrant().copy_with(border_color="#7A8AA0", border_width=1.0),
        )
        docked_vibrant.width_sizing = demo_width

        floating_standard = FloatingToolbar(
            self._standard_actions(),
            padding=(12, 8, 12, 8),
            style=ToolbarStyle.standard(),
        )
        floating_vibrant_vertical = FloatingToolbar(
            [
                IconButton("home", style=IconButtonStyle.vibrant()),
                IconButton("edit", style=IconButtonStyle.filled_vibrant()),
                IconButton("share", style=IconButtonStyle.tonal_vibrant()),
            ],
            orientation="vertical",
            padding=(12, 8, 12, 8),
            style=ToolbarStyle.vibrant().copy_with(corner_radius=16, elevation=1.0),
        )

        return Box(
            child=Column(
                [
                    Text("Material 3 Toolbar Demo"),
                    Text("DockedToolbar (space-between, edge-to-edge)"),
                    Text("First and last icons should align close to each side of the frame."),
                    docked_standard,
                    docked_vibrant,
                    Text("FloatingToolbar (supports outer padding)"),
                    Row(
                        [
                            floating_standard,
                            floating_vibrant_vertical,
                        ],
                        gap=16,
                        cross_alignment="start",
                    ),
                ],
                gap=10,
                cross_alignment="start",
            ),
            padding=20,
            background_color="#F2F2F7",
        )


def main() -> None:
    """Run toolbar demo."""
    demo = ToolbarDemoWidget()
    app = App(content=demo.build())
    app.run()


if __name__ == "__main__":
    main()
