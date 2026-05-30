"""Material Widgets - ToggleButton variants."""

from __future__ import annotations

from nuiitivet.material import App, ToggleButton, ToggleButtonStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=12,
            cross_alignment="start",
            children=[
                Row(
                    gap=12,
                    children=[
                        ToggleButton("Filled", icon="check", selected=True, style=ToggleButtonStyle.filled()),
                        ToggleButton("Filled", icon="check", selected=False, style=ToggleButtonStyle.filled()),
                    ],
                ),
                Row(
                    gap=12,
                    children=[
                        ToggleButton("Outlined", icon="check", selected=True, style=ToggleButtonStyle.outlined()),
                        ToggleButton("Outlined", icon="check", selected=False, style=ToggleButtonStyle.outlined()),
                    ],
                ),
                Row(
                    gap=12,
                    children=[
                        ToggleButton(
                            "Disabled", icon="check", selected=True, disabled=True, style=ToggleButtonStyle.filled()
                        ),
                        ToggleButton(
                            "Disabled", icon="check", selected=False, disabled=True, style=ToggleButtonStyle.outlined()
                        ),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title="ToggleButton",
        width=560,
        height=260,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
