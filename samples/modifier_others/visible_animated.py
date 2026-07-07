import nuiitivet.material as nv

_FADE_SCALE = nv.TransitionDefinition(
    motion=nv.LinearMotion(0.25),
    pattern=nv.FadePattern(start_alpha=0.0, end_alpha=1.0)
    | nv.ScalePattern(start_scale_x=0.9, start_scale_y=0.9, end_scale_x=1.0, end_scale_y=1.0),
)


def _panel(label: str) -> nv.Widget:
    return nv.Card(
        child=nv.Text(label, type_scale=nv.TypeScaleToken.from_size(14)),
        padding=16,
        width=220,
        style=nv.CardStyle.filled(),
    )


class _VisibleToggleDemo(nv.ComposableWidget):
    is_visible: nv.Observable[bool] = nv.Observable(True)

    def build(self) -> nv.Widget:
        def toggle() -> None:
            self.is_visible.value = not self.is_visible.value

        return nv.Column(
            children=[
                nv.Text(
                    "Toggle with TransitionDefinition (fade + scale)",
                    type_scale=nv.TypeScaleToken.from_size(12),
                ),
                nv.Button("Toggle visibility", on_click=toggle, style=nv.ButtonStyle.filled()),
                _panel("Animated widget").modifier(nv.visible(self.is_visible, transition=_FADE_SCALE)),
                nv.Text(
                    "↑ Layout space is always reserved",
                    type_scale=nv.TypeScaleToken.from_size(12),
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

    app = nv.App(content=content, title="visible() Animated", width=480, height=280)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
