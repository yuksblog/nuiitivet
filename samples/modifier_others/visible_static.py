import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.material import Card, CardStyle
from nuiitivet.modifiers import visible
from nuiitivet.theme.type_scale import TypeScaleToken

_CAPTION = TypeScaleToken.from_size(12)


def _panel(label: str) -> nv.Widget:
    return Card(
        child=md.Text(label, type_scale=TypeScaleToken.from_size(14)),
        padding=16,
        width=180,
        style=CardStyle.filled(),
    )


def main(png: str = "") -> None:
    content = nv.Column(
        children=[
            md.Text("visible(True) — always shown", type_scale=_CAPTION),
            _panel("Always shown").modifier(visible(True)),
            md.Text("visible(False) — hidden, but layout space preserved", type_scale=_CAPTION),
            _panel("Never shown").modifier(visible(False)),
            md.Text("Sibling below: layout space of hidden widget is reserved", type_scale=_CAPTION),
        ],
        gap=12,
        cross_alignment="start",
        padding=24,
    )

    app = md.App(content=content, title="visible() Static", width=480, height=280)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
