"""Material Widgets - Text typography sizes."""

from __future__ import annotations

from nuiitivet.material import App, Text
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container


def _line(label: str, size: int) -> Text:
    return Text(f"{label} ({size}sp)", style=TextStyle(font_size=size))


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=8,
            cross_alignment="start",
            children=[
                _line("Display", 36),
                _line("Headline", 28),
                _line("Title", 22),
                _line("Body", 16),
                _line("Label", 14),
                _line("Caption", 12),
            ],
        ),
    )
    app = App(
        content=content,
        title="Text",
        width=420,
        height=300,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
