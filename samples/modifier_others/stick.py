import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.material import Icon
from nuiitivet.material.styles.icon_style import IconStyle
from nuiitivet.modifiers import stick
from nuiitivet.widgeting.widget import Widget


def _base_icon(name: str) -> Widget:
    # A large base icon onto which a decoration is composed.
    return Icon(name, size=64, style=IconStyle(color="#5F6368"))


def _overlay_icon(name: str, color: str) -> Widget:
    # A smaller icon layered on top to form a new, composite symbol.
    return Icon(name, size=30, style=IconStyle(color=color))


def main(png: str = "") -> None:
    content = nv.Row(
        children=[
            # cloud + upward arrow = "upload to cloud"
            _base_icon("cloud").modifier(
                stick(
                    _overlay_icon("arrow_upward", "#1A73E8"),
                    alignment="center",
                    anchor="center",
                    offset=(0, 6),
                )
            ),
            # folder + star = "favorite folder"
            _base_icon("folder").modifier(
                stick(
                    _overlay_icon("star", "#F9AB00"),
                    alignment="center",
                    anchor="center",
                    offset=(0, 8),
                )
            ),
            # photo + pencil = "edit photo"
            _base_icon("photo").modifier(
                stick(
                    _overlay_icon("edit", "#188038"),
                    alignment="center",
                    anchor="center",
                    offset=(0, 6),
                )
            ),
        ],
        gap=32,
        padding=24,
    )

    app = md.App(content=content, title="stick Modifier", width=400)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
