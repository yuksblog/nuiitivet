"""Material Widgets - Button style variants."""

from __future__ import annotations

from nuiitivet.material import App, Button
from nuiitivet.material.styles.button_style import ButtonStyle
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
                        Button("Filled", style=ButtonStyle.filled()),
                        Button("Tonal", style=ButtonStyle.tonal()),
                        Button("Elevated", style=ButtonStyle.elevated()),
                    ],
                ),
                Row(
                    gap=12,
                    children=[
                        Button("Outlined", style=ButtonStyle.outlined()),
                        Button("Text", style=ButtonStyle.text()),
                    ],
                ),
                Row(
                    gap=12,
                    children=[
                        Button("With icon", icon="add", style=ButtonStyle.filled()),
                        Button("Disabled", style=ButtonStyle.filled(), disabled=True),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title="Button",
        width=560,
        height=260,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
