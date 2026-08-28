import nuiitivet.material as nv


def _base_icon(name: str) -> nv.Widget:
    # A large base icon onto which a decoration is composed.
    return nv.Icon(name, size=64, style=nv.IconStyle(color="#5F6368"))


def _overlay_icon(name: str, color: str) -> nv.Widget:
    # A smaller icon layered on top to form a new, composite symbol.
    return nv.Icon(name, size=30, style=nv.IconStyle(color=color))


def main(png: str = "") -> None:
    content = nv.Row(
        children=[
            # cloud + upward arrow = "upload to cloud"
            _base_icon("cloud").modifier(
                nv.stick(
                    _overlay_icon("arrow_upward", "#1A73E8"),
                    target_anchor="center",
                    content_anchor="center",
                )
            ),
            # folder + star = "favorite folder"
            _base_icon("folder").modifier(
                nv.stick(
                    _overlay_icon("star", "#F9AB00"),
                    target_anchor="center",
                    content_anchor="center",
                )
            ),
            # photo + pencil = "edit photo"
            _base_icon("photo").modifier(
                nv.stick(
                    _overlay_icon("edit", "#188038"),
                    target_anchor="center",
                    content_anchor="center",
                )
            ),
        ],
        gap=32,
        padding=24,
    )

    app = nv.App(nv.Window(content=content, title="stick Modifier", width=400))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
