"""Selection controls demo for RadioGroup/RadioButton and Switch.

This sample demonstrates:
- RadioGroup controlling descendant RadioButton widgets in nested layouts.
- Switch with observable-backed checked states.
"""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material import RadioButton, RadioGroup, Switch, Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.observable import Observable


def _radio_row(value: str, label: str) -> Row:
    return Row(
        children=[
            RadioButton(value),
            Text(label),
        ],
        gap=12,
    )


def main() -> None:
    selected_plan = Observable("standard")
    wifi_enabled = Observable(True)
    notifications_enabled = Observable(False)

    radio_options = Container(
        child=Column(
            children=[
                _radio_row("standard", "Standard Plan"),
                _radio_row("pro", "Pro Plan"),
                _radio_row("enterprise", "Enterprise Plan"),
            ],
            gap=12,
            cross_alignment="start",
        ),
        padding=12,
    )

    radios = RadioGroup(
        radio_options,
        value=selected_plan,
    )

    switches = Column(
        children=[
            Row(children=[Switch(checked=wifi_enabled), Text("Enable Wi-Fi")], gap=12),
            Row(children=[Switch(checked=notifications_enabled), Text("Enable Notifications")], gap=12),
        ],
        gap=12,
        cross_alignment="start",
    )

    content = Column(
        children=[
            Text("Selection Controls Demo", padding=(0, 0, 0, 8)),
            Text("RadioGroup", padding=(0, 0, 0, 4)),
            radios,
            Text("Switch", padding=(0, 8, 0, 4)),
            switches,
        ],
        gap=8,
        cross_alignment="start",
    )

    root = Container(child=content, padding=20)

    app = MaterialApp(content=root)
    app.run()


if __name__ == "__main__":
    main()
