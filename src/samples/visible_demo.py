"""visible() Modifier Demo

Demonstrates the three core usages of the visible() modifier:

1. Static visibility   - constant True/False at construction time
2. Observable toggle   - reactive show/hide driven by Observable[bool]
3. Animated visibility - enter/exit animation via TransitionDefinition

When hidden, the widget is rendered fully transparent and ignores input, but
it continues to occupy its normal layout space (visible() is a thin
composition of opacity() + ignore_pointer()). For layout-size animations,
use a dedicated layout-aware Widget instead.
"""

from __future__ import annotations

from nuiitivet.animation import LinearMotion
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern, ScalePattern
from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material import App, Text
from nuiitivet.material.buttons import Button
from nuiitivet.material import ButtonStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.modifiers import background, corner_radius, visible
from nuiitivet.observable import Observable
from nuiitivet.widgets.box import Box
from nuiitivet.widgeting.widget import ComposableWidget, Widget

_FADE_SCALE = TransitionDefinition(
    motion=LinearMotion(0.25),
    pattern=FadePattern(start_alpha=0.0, end_alpha=1.0)
    | ScalePattern(start_scale_x=0.9, start_scale_y=0.9, end_scale_x=1.0, end_scale_y=1.0),
)


def _panel(label: str, color: str) -> Widget:
    return Box(
        child=Text(label, style=TextStyle(font_size=14, color=(255, 255, 255, 255))),
        padding=16,
        width=200,
    ).modifier(background(color) | corner_radius(8))


def _section_label(text: str) -> Widget:
    return Text(text, style=TextStyle(font_size=11, color=(100, 100, 100, 255)))


class _ObservableToggleDemo(ComposableWidget):
    is_visible: Observable[bool] = Observable(True)

    def build(self) -> Widget:
        def toggle() -> None:
            self.is_visible.value = not self.is_visible.value

        return Column(
            children=[
                _section_label("Observable toggle (no animation, layout space preserved)"),
                Button("Toggle", on_click=toggle, style=ButtonStyle.filled()),
                _panel("Hello", "#2196F3").modifier(visible(self.is_visible)),
                Text("Below sibling", style=TextStyle(font_size=12)),
            ],
            gap=12,
            cross_alignment="start",
        )


class _AnimatedToggleDemo(ComposableWidget):
    is_visible: Observable[bool] = Observable(True)

    def build(self) -> Widget:
        def toggle() -> None:
            self.is_visible.value = not self.is_visible.value

        return Column(
            children=[
                _section_label("Animated toggle (fade + scale, layout space preserved)"),
                Button("Toggle", on_click=toggle, style=ButtonStyle.filled()),
                _panel("Animated", "#4CAF50").modifier(visible(self.is_visible, transition=_FADE_SCALE)),
                Text("Below sibling", style=TextStyle(font_size=12)),
            ],
            gap=12,
            cross_alignment="start",
        )


def _static_demo() -> Widget:
    return Column(
        children=[
            _section_label("Static visibility"),
            Row(
                children=[
                    _panel("Always shown", "#FF5722").modifier(visible(True)),
                    _panel("Never shown", "#9C27B0").modifier(visible(False)),
                    _panel("Trailing sibling", "#607D8B"),
                ],
                gap=12,
            ),
        ],
        gap=12,
        cross_alignment="start",
    )


def main(png: str = "") -> None:
    content = Column(
        children=[
            _static_demo(),
            _ObservableToggleDemo(),
            _AnimatedToggleDemo(),
        ],
        gap=24,
        padding=24,
        cross_alignment="start",
    )

    app = App(content=content, width=680, height=520)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
