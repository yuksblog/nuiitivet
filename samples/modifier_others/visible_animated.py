import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.animation import LinearMotion
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern, ScalePattern
from nuiitivet.material import Card, CardStyle
from nuiitivet.modifiers import visible
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.observable import Observable
from nuiitivet.widgeting.widget import ComposableWidget

_FADE_SCALE = TransitionDefinition(
    motion=LinearMotion(0.25),
    pattern=FadePattern(start_alpha=0.0, end_alpha=1.0)
    | ScalePattern(start_scale_x=0.9, start_scale_y=0.9, end_scale_x=1.0, end_scale_y=1.0),
)


def _panel(label: str) -> nv.Widget:
    return Card(
        child=md.Text(label, style=TextStyle(font_size=14)),
        padding=16,
        width=220,
        style=CardStyle.filled(),
    )


class _VisibleToggleDemo(ComposableWidget):
    is_visible: Observable[bool] = Observable(True)

    def build(self) -> nv.Widget:
        from nuiitivet.material.buttons import Button
        from nuiitivet.material import ButtonStyle

        def toggle() -> None:
            self.is_visible.value = not self.is_visible.value

        return nv.Column(
            children=[
                md.Text(
                    "Toggle with TransitionDefinition (fade + scale)",
                    style=TextStyle(font_size=12),
                ),
                Button("Toggle visibility", on_click=toggle, style=ButtonStyle.filled()),
                _panel("Animated widget").modifier(visible(self.is_visible, transition=_FADE_SCALE)),
                md.Text(
                    "↑ Layout space is always reserved",
                    style=TextStyle(font_size=12),
                ),
            ],
            gap=12,
            cross_alignment="start",
        )


def main(png: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=_VisibleToggleDemo(),
    )

    app = md.App(content=content, title="visible() Animated", width=480, height=280)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
