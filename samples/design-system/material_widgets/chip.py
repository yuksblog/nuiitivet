"""Material Widgets - Chip variants."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=12,
            cross_alignment="start",
            children=[
                nv.Text("Assist / Filter"),
                nv.Row(
                    gap=12,
                    children=[
                        nv.AssistChip("Assist", leading_icon="add"),
                        nv.FilterChip("Filter", selected=True, leading_icon="tune"),
                        nv.FilterChip("Filter", selected=False, leading_icon="tune"),
                    ],
                ),
                nv.Text("Input / Suggestion"),
                nv.Row(
                    gap=12,
                    children=[
                        nv.InputChip("Input", leading_icon="person", trailing_icon="close"),
                        nv.SuggestionChip("Suggestion", leading_icon="lightbulb"),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(nv.Window(content=content, title="Chip", width=560, height=240))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
