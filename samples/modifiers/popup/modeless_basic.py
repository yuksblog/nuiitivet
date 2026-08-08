import nuiitivet.material as nv

is_open: nv.Observable[bool] = nv.Observable(False)


def toggle() -> None:
    is_open.value = not is_open.value


info_panel = nv.Card(
    child=nv.Column(
        children=[
            nv.Text("Keyboard Shortcuts"),
            nv.HorizontalDivider(padding=(4, 0)),
            nv.Text("Ctrl+N  New file"),
            nv.Text("Ctrl+O  Open file"),
            nv.Text("Ctrl+S  Save"),
            nv.Text("Ctrl+Z  Undo"),
        ],
        gap=6,
        cross_alignment="start",
    ),
    padding=16,
    width=200,
    style=nv.CardStyle.elevated(),
)

anchor = (
    nv.Container(
        width=160,
        height=40,
        child=nv.Text("Show shortcuts"),
        alignment="center",
    )
    .modifier(nv.background("#2196F3") | nv.corner_radius(8) | nv.clickable(on_click=toggle))
    .modifier(
        nv.modeless(
            info_panel,
            is_open=is_open,
            target_anchor="bottom-left",
            content_anchor="top-left",
            offset=(0.0, 4.0),
        )
    )
)


def main(png: str = "") -> None:
    if png:
        # For screenshot: place popup content directly in layout (overlay not captured by render_to_png)
        _anchor = nv.Container(width=160, height=40, child=nv.Text("Show shortcuts"), alignment="center").modifier(
            nv.background("#2196F3") | nv.corner_radius(8)
        )
        _panel = nv.Card(
            child=nv.Column(
                children=[
                    nv.Text("Keyboard Shortcuts"),
                    nv.HorizontalDivider(padding=(4, 0)),
                    nv.Text("Ctrl+N  New file"),
                    nv.Text("Ctrl+O  Open file"),
                    nv.Text("Ctrl+S  Save"),
                    nv.Text("Ctrl+Z  Undo"),
                ],
                gap=6,
                cross_alignment="start",
            ),
            padding=16,
            width=200,
            style=nv.CardStyle.elevated(),
        )
        app = nv.App(
            content=nv.Column(children=[_anchor, _panel], gap=4, padding=16),
            title="modeless Modifier",
            width=300,
            height=350,
        )
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app = nv.App(
        content=nv.Column(children=[anchor], gap=8, padding=16),
        title="modeless Modifier",
        width=300,
        height=250,
    )
    app.run()


if __name__ == "__main__":
    main()
