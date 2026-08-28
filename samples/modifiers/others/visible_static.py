import nuiitivet.material as nv

_CAPTION = nv.TypeScaleToken.from_size(12)


def _panel(label: str) -> nv.Widget:
    return nv.Card(
        child=nv.Text(label, type_scale=nv.TypeScaleToken.from_size(14)),
        padding=16,
        width=180,
        style=nv.CardStyle.filled(),
    )


def main(png: str = "") -> None:
    content = nv.Column(
        children=[
            nv.Text("visible(True) — always shown", type_scale=_CAPTION),
            _panel("Always shown").modifier(nv.visible(True)),
            nv.Text("visible(False) — hidden, but layout space preserved", type_scale=_CAPTION),
            _panel("Never shown").modifier(nv.visible(False)),
            nv.Text("Sibling below: layout space of hidden widget is reserved", type_scale=_CAPTION),
        ],
        gap=12,
        cross_alignment="start",
        padding=24,
    )

    app = nv.App(nv.Window(content=content, title="visible() Static", width=480, height=280))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
