import nuiitivet.material as nv


def build_root() -> nv.Widget:
    # resize arrows over the divider
    divider = nv.Container(width=8, height=120).modifier(
        nv.background("#BDBDBD") | nv.cursor(nv.MouseCursor.RESIZE_LEFT_RIGHT)
    )

    # a clickable card without the hand
    card = nv.Container(
        width=220,
        height=120,
        padding=16,
        alignment="center",
        child=nv.Column(
            children=[nv.Text("Open on click"), nv.Button("Details", on_click=lambda: print("Details"))],
            gap=12,
        ),
    ).modifier(
        nv.background("#E3F2FD")
        | nv.corner_radius(12)
        | nv.clickable(on_click=lambda: print("Card clicked"))
        | nv.cursor(nv.MouseCursor.DEFAULT)
    )

    return nv.Row(children=[nv.Button("Save", on_click=lambda: print("Saved")), divider, card], gap=24, padding=16)


def main(png: str = ""):
    app = nv.App(nv.Window(content=build_root, title="Cursor Modifier", width=520, height=180))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
