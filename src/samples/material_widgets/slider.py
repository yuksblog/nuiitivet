"""Material Widgets - Slider, CenteredSlider, RangeSlider."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, CenteredSlider, RangeSlider, Slider, Text
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=16,
            cross_alignment="start",
            children=[
                Text("Slider"),
                Slider(value=0.4, length=360, min_value=0.0, max_value=1.0),
                Text("Slider with stops & value indicator"),
                Slider(
                    value=60.0,
                    length=360,
                    min_value=0.0,
                    max_value=100.0,
                    stops=6,
                    show_value_indicator=True,
                ),
                Text("CenteredSlider"),
                CenteredSlider(value=0.3, length=360, min_value=-1.0, max_value=1.0),
                Text("RangeSlider"),
                RangeSlider(value_start=0.25, value_end=0.75, length=360, min_value=0.0, max_value=1.0),
            ],
        ),
    )
    app = App(
        content=content,
        title_bar=nv.DefaultTitleBar(title="Slider"),
        width=480,
        height=420,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
