"""Progress indicators demo for MD3 widgets."""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material import (
    CircularProgressIndicator,
    IndeterminateCircularProgressIndicator,
    IndeterminateLinearProgressIndicator,
    LinearProgressIndicator,
    App,
    Slider,
    Switch,
    Text,
)
from nuiitivet.material.styles import CircularProgressIndicatorStyle, LinearProgressIndicatorStyle
from nuiitivet.observable import Observable


def main() -> None:
    linear_value = Observable(0.35)
    circular_value = Observable(0.65)
    disabled = Observable(False)

    content = Column(
        children=[
            Text("Progress Indicators Demo"),
            Row(
                children=[
                    Switch(checked=disabled),
                    Text(disabled.map(lambda v: f"Disabled: {'ON' if v else 'OFF'}")),
                ],
                gap=12,
            ),
            Text(linear_value.map(lambda v: f"Linear value: {v:.2f}")),
            Slider(
                value=linear_value,
                length=320,
                on_change=lambda value: setattr(linear_value, "value", value),
            ),
            LinearProgressIndicator(
                value=linear_value,
                disabled=disabled,
                width=320,
                style=LinearProgressIndicatorStyle.flat(),
            ),
            IndeterminateLinearProgressIndicator(
                disabled=disabled,
                width=320,
                style=LinearProgressIndicatorStyle.flat(),
            ),
            Text(circular_value.map(lambda v: f"Circular value: {v:.2f}"), padding=(0, 8, 0, 0)),
            Slider(
                value=circular_value,
                length=320,
                on_change=lambda value: setattr(circular_value, "value", value),
            ),
            Row(
                children=[
                    CircularProgressIndicator(
                        value=circular_value,
                        disabled=disabled,
                        size=40,
                        style=CircularProgressIndicatorStyle.flat(),
                    ),
                    IndeterminateCircularProgressIndicator(
                        disabled=disabled,
                        size=40,
                        style=CircularProgressIndicatorStyle.flat(),
                    ),
                ],
                gap=24,
            ),
        ],
        gap=12,
        cross_alignment="start",
    )

    app = App(content=Container(child=content, padding=24))
    app.run()


if __name__ == "__main__":
    main()
