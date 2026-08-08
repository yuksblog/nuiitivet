import nuiitivet.material as nv

is_open: nv.Observable[bool] = nv.Observable(False)


def toggle() -> None:
    is_open.value = not is_open.value


def close() -> None:
    is_open.value = False


menu = nv.Menu(
    items=[
        nv.MenuItem("New", on_click=lambda: print("New")),
        nv.MenuItem("Open...", on_click=lambda: print("Open")),
        nv.MenuDivider(),
        nv.MenuItem("Save", leading_icon="save", on_click=lambda: print("Save")),
        nv.MenuItem("Close", on_click=close),
    ],
    on_dismiss=close,
)

anchor = (
    nv.Container(
        width=160,
        height=40,
        child=nv.Text("Open (light-dismiss)"),
        alignment="center",
    )
    .modifier(nv.background("#4CAF50") | nv.corner_radius(8) | nv.clickable(on_click=toggle))
    .modifier(
        nv.light_dismiss(
            menu,
            is_open=is_open,
            target_anchor="bottom-left",
            content_anchor="top-left",
            offset=(0.0, 4.0),
        )
    )
)


def main(png: str = "") -> None:
    if png:
        # For screenshot: place menu directly in layout (overlay not captured by render_to_png)
        _anchor = nv.Container(
            width=160, height=40, child=nv.Text("Open (light-dismiss)"), alignment="center"
        ).modifier(nv.background("#4CAF50") | nv.corner_radius(8))
        _menu = nv.Menu(
            items=[
                nv.MenuItem("New", on_click=lambda: print("New")),
                nv.MenuItem("Open...", on_click=lambda: print("Open")),
                nv.MenuDivider(),
                nv.MenuItem("Save", leading_icon="save", on_click=lambda: print("Save")),
                nv.MenuItem("Close", on_click=lambda: None),
            ],
        )
        app = nv.App(
            content=nv.Column(children=[_anchor, _menu], gap=4, padding=16),
            title="light_dismiss Modifier",
            width=400,
            height=400,
        )
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app = nv.App(
        content=nv.Column(children=[anchor], gap=8, padding=16),
        title="light_dismiss Modifier",
        width=400,
        height=400,
    )
    app.run()


if __name__ == "__main__":
    main()
