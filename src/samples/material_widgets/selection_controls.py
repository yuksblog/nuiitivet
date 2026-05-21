"""Material Widgets - Checkbox, RadioButton, Switch."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Checkbox, RadioButton, RadioGroup, Switch, Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=16,
            cross_alignment="start",
            children=[
                Text("Checkbox"),
                Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        Checkbox(checked=True),
                        Checkbox(checked=False),
                        Checkbox(checked=True, disabled=True),
                        Checkbox(checked=False, disabled=True),
                    ],
                ),
                Text("RadioButton"),
                RadioGroup(
                    Row(
                        gap=16,
                        cross_alignment="center",
                        children=[
                            Row(gap=6, cross_alignment="center", children=[RadioButton("a"), Text("Option A")]),
                            Row(gap=6, cross_alignment="center", children=[RadioButton("b"), Text("Option B")]),
                            Row(gap=6, cross_alignment="center", children=[RadioButton("c"), Text("Option C")]),
                        ],
                    ),
                    value="a",
                ),
                Text("Switch"),
                Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        Switch(checked=True),
                        Switch(checked=False),
                        Switch(checked=True, disabled=True),
                        Switch(checked=False, disabled=True),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="Selection Controls"),
        width=520,
        height=360,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
