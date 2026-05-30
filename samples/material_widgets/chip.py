"""Material Widgets - Chip variants."""

from __future__ import annotations

from nuiitivet.material import App, AssistChip, FilterChip, InputChip, SuggestionChip, Text
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
                Text("Assist / Filter"),
                Row(
                    gap=12,
                    children=[
                        AssistChip("Assist", leading_icon="add"),
                        FilterChip("Filter", selected=True, leading_icon="tune"),
                        FilterChip("Filter", selected=False, leading_icon="tune"),
                    ],
                ),
                Text("Input / Suggestion"),
                Row(
                    gap=12,
                    children=[
                        InputChip("Input", leading_icon="person", trailing_icon="close"),
                        SuggestionChip("Suggestion", leading_icon="lightbulb"),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title="Chip",
        width=560,
        height=240,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
