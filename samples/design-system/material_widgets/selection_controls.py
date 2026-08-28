"""Material Widgets - Checkbox, RadioButton, Switch."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.Text("Checkbox"),
                nv.Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        nv.Checkbox(checked=True),
                        nv.Checkbox(checked=False),
                        nv.Checkbox(checked=True, disabled=True),
                        nv.Checkbox(checked=False, disabled=True),
                    ],
                ),
                nv.Text("RadioButton"),
                nv.RadioGroup(
                    nv.Row(
                        gap=16,
                        cross_alignment="center",
                        children=[
                            nv.Row(
                                gap=6,
                                cross_alignment="center",
                                children=[nv.RadioButton("a"), nv.Text("Option A")],
                            ),
                            nv.Row(
                                gap=6,
                                cross_alignment="center",
                                children=[nv.RadioButton("b"), nv.Text("Option B")],
                            ),
                            nv.Row(
                                gap=6,
                                cross_alignment="center",
                                children=[nv.RadioButton("c"), nv.Text("Option C")],
                            ),
                        ],
                    ),
                    value="a",
                ),
                nv.Text("Switch"),
                nv.Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        nv.Switch(checked=True),
                        nv.Switch(checked=False),
                        nv.Switch(checked=True, disabled=True),
                        nv.Switch(checked=False, disabled=True),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(nv.Window(content=content, title="Selection Controls", width=520, height=360))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
