"""Buttons Demo - MD3 sizing and padding visual checks.

This demo is meant to visually validate MD3-ish metrics:
- touch target min height: 48dp
- container height: 40dp
- icon size: 20dp
- leading/trailing insets: 16dp
- gap between icon and text: 8dp
- font size: 14
"""

from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.material.buttons import FilledButton, FilledTonalButton, OutlinedButton, ElevatedButton, TextButton
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box


def _section(title: str):
    return Text(title, padding=(0, 12, 0, 4))


def main() -> None:
    samples = [
        "OK",
        "Cancel",
        "Confirm",
        "iiii",
        "WWWW",
        "gyp",
        "Hello",
        "(test)",
    ]

    metrics_note = Column(
        children=[
            Text("MD3 Button Samples"),
        ],
        gap=6,
        cross_alignment="start",
    )

    fixed_width_buttons = Column(
        children=[
            _section("Fixed width=240 (detect centering)"),
            *[FilledButton(label, icon="search", width=Sizing.fixed(240)) for label in samples],
        ],
        gap=10,
        cross_alignment="center",
    )

    variants_auto_width = Column(
        children=[
            _section("Variants (auto width)"),
            FilledButton("Filled", icon="search"),
            OutlinedButton("Outlined", icon="search"),
            ElevatedButton("Elevated", icon="search"),
            FilledTonalButton("Tonal", icon="search"),
            TextButton("Text", icon="search"),
        ],
        gap=10,
        cross_alignment="center",
    )

    text_buttons = Column(
        children=[
            _section("TextButton samples (auto width)"),
            *[TextButton(label, icon="search") for label in samples],
        ],
        gap=10,
        cross_alignment="center",
    )

    outlined_buttons = Column(
        children=[
            _section("OutlinedButton samples (auto width)"),
            *[OutlinedButton(label, icon="search") for label in samples],
        ],
        gap=10,
        cross_alignment="center",
    )

    content = Column(
        children=[
            metrics_note,
            Row(
                children=[
                    fixed_width_buttons,
                    variants_auto_width,
                    text_buttons,
                    outlined_buttons,
                ],
                gap=24,
                cross_alignment="start",
            ),
        ],
        gap=16,
        cross_alignment="start",
    )

    root = Box(child=content, padding=24, background_color="#F2F2F7")

    app = MaterialApp(content=root)
    app.run()


if __name__ == "__main__":
    main()
