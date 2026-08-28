"""Material Widgets - HorizontalSlider, HorizontalCenteredSlider, HorizontalRangeSlider."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.Text("Slider"),
                nv.HorizontalSlider(value=0.4, width=360, min_value=0.0, max_value=1.0),
                nv.Text("Slider with stops & value indicator"),
                nv.HorizontalSlider(
                    value=60.0,
                    width=360,
                    min_value=0.0,
                    max_value=100.0,
                    stops=6,
                    show_value_indicator=True,
                ),
                nv.Text("CenteredSlider"),
                nv.HorizontalCenteredSlider(value=0.3, width=360, min_value=-1.0, max_value=1.0),
                nv.Text("RangeSlider"),
                nv.HorizontalRangeSlider(
                    value_start=0.25, value_end=0.75, width=360, min_value=0.0, max_value=1.0
                ),
            ],
        ),
    )
    app = nv.App(nv.Window(content=content, title="Slider", width=480, height=420))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
