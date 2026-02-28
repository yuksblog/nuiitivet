"""Slider demo showing horizontal and vertical orientations."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material import CenteredSlider, Orientation, RangeSlider, Slider, Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.observable import Observable


def main() -> None:
    horizontal_value = Observable(0.3)
    vertical_value = Observable(0.7)
    indicator_value = Observable(0.5)
    stops_value = Observable(0.0)
    centered_value = Observable(0.0)
    range_start = Observable(0.2)
    range_end = Observable(0.8)

    horizontal_slider = Slider(
        value=horizontal_value,
        orientation=Orientation.HORIZONTAL,
        length=320,
        min_value=0.0,
        max_value=1.0,
        on_change=lambda value: setattr(horizontal_value, "value", value),
    )

    vertical_slider = Slider(
        value=vertical_value,
        orientation=Orientation.VERTICAL,
        length=220,
        min_value=0.0,
        max_value=1.0,
        on_change=lambda value: setattr(vertical_value, "value", value),
    )

    indicator_slider = Slider(
        value=indicator_value,
        orientation=Orientation.HORIZONTAL,
        length=320,
        min_value=0.0,
        max_value=1.0,
        show_value_indicator=True,
        on_change=lambda value: setattr(indicator_value, "value", value),
    )

    stops_slider = Slider(
        value=stops_value,
        orientation=Orientation.HORIZONTAL,
        length=320,
        min_value=0.0,
        max_value=100.0,
        stops=6,
        on_change=lambda value: setattr(stops_value, "value", value),
    )

    centered_slider = CenteredSlider(
        value=centered_value,
        orientation=Orientation.HORIZONTAL,
        length=320,
        min_value=-1.0,
        max_value=1.0,
        on_change=lambda value: setattr(centered_value, "value", value),
    )

    range_slider = RangeSlider(
        value_start=range_start,
        value_end=range_end,
        orientation=Orientation.HORIZONTAL,
        length=320,
        min_value=0.0,
        max_value=1.0,
        on_change=lambda values: (
            setattr(range_start, "value", values[0]),
            setattr(range_end, "value", values[1]),
        ),
    )

    range_label = range_start.combine(range_end).compute(lambda start, end: f"Range: {start:.2f} - {end:.2f}")

    content = Column(
        children=[
            Text("Slider Demo"),
            Text(horizontal_value.map(lambda value: f"Horizontal: {value:.2f}")),
            horizontal_slider,
            Text("Drag the slider below to show value indicator"),
            Text(indicator_value.map(lambda value: f"With indicator: {value:.2f}")),
            indicator_slider,
            Text(stops_value.map(lambda value: f"Stops (6): {value:.0f}")),
            stops_slider,
            Text(centered_value.map(lambda value: f"Centered: {value:.2f}")),
            centered_slider,
            Text(range_label),
            range_slider,
            Row(
                children=[
                    vertical_slider,
                    Text(vertical_value.map(lambda value: f"Vertical: {value:.2f}")),
                ],
                gap=16,
                cross_alignment="center",
            ),
        ],
        gap=12,
        cross_alignment="start",
        padding=24,
    )

    app = MaterialApp(content=Container(child=content, padding=8))
    app.run()


if __name__ == "__main__":
    main()
