"""Material Widgets - Card filled/outlined/elevated."""

from __future__ import annotations

import nuiitivet.material as nv


def _card(label: str, style: nv.CardStyle) -> nv.Card:
    return nv.Card(
        nv.Column(gap=4, children=[nv.Text(label), nv.Text("Card body content")]),
        width=160,
        height=110,
        padding=16,
        style=style,
    )


def build_root() -> nv.Widget:
    content = nv.Container(
        padding=24,
        child=nv.Row(
            gap=16,
            children=[
                _card("Filled", nv.CardStyle.filled()),
                _card("Outlined", nv.CardStyle.outlined()),
                _card("Elevated", nv.CardStyle.elevated()),
            ],
        ),
    )
    return content


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, title="Card", width=600, height=220))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
