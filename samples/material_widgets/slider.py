"""Material Widgets - HorizontalSlider, HorizontalCenteredSlider, HorizontalRangeSlider."""

from __future__ import annotations

from nuiitivet.material import (
    App,
    HorizontalCenteredSlider,
    HorizontalRangeSlider,
    HorizontalSlider,
    Text,
)
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
                HorizontalSlider(value=0.4, width=360, min_value=0.0, max_value=1.0),
                Text("Slider with stops & value indicator"),
                HorizontalSlider(
                    value=60.0,
                    width=360,
                    min_value=0.0,
                    max_value=100.0,
                    stops=6,
                    show_value_indicator=True,
                ),
                Text("CenteredSlider"),
                HorizontalCenteredSlider(value=0.3, width=360, min_value=-1.0, max_value=1.0),
                Text("RangeSlider"),
                HorizontalRangeSlider(
                    value_start=0.25, value_end=0.75, width=360, min_value=0.0, max_value=1.0
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title="Slider",
        width=480,
        height=420,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
