import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.material import Card, CardStyle
from nuiitivet.modifiers import visible
from nuiitivet.material.styles.text_style import TextStyle


def _panel(label: str) -> nv.Widget:
    return Card(
        child=md.Text(label, style=TextStyle(font_size=14)),
        padding=16,
        width=180,
        style=CardStyle.filled(),
    )


def main(png: str = "") -> None:
    content = nv.Column(
        children=[
            md.Text("visible(True) — always shown", style=TextStyle(font_size=12)),
            _panel("Always shown").modifier(visible(True)),
            md.Text("visible(False) — hidden, but layout space preserved", style=TextStyle(font_size=12)),
            _panel("Never shown").modifier(visible(False)),
            md.Text("Sibling below: layout space of hidden widget is reserved", style=TextStyle(font_size=12)),
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
