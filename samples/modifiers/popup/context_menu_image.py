"""Right-click a tile to open a menu at the pointer.

Unlike ``popup``, no ``Observable`` is wired up here: the
``context_menu`` modifier owns both the open state and the click coordinate.
Right-click near the right or bottom edge to see the menu clamp back into view.
"""

import nuiitivet.material as nv


def _menu() -> nv.Widget:
    return nv.Menu(
        items=[
            nv.MenuItem("Open", leading_icon="open_in_new", on_click=lambda: print("Open")),
            nv.MenuItem("Rename", leading_icon="edit", on_click=lambda: print("Rename")),
            nv.MenuDivider(),
            nv.MenuItem("Delete", leading_icon="delete", on_click=lambda: print("Delete")),
        ],
    )


def _tile(label: str, color: str) -> nv.Widget:
    return nv.Container(
        width=160,
        height=110,
        child=nv.Text(label),
        alignment="center",
    ).modifier(nv.background(color) | nv.corner_radius(12) | nv.context_menu(_menu()))


def main(png: str = "") -> None:
    content = nv.Column(
        children=[
            nv.Text("Right-click a tile — the menu opens at the pointer"),
            nv.Row(
                children=[
                    _tile("Photo", "#90CAF9"),
                    _tile("Document", "#A5D6A7"),
                ],
                gap=16,
            ),
            nv.Text("Near an edge, the menu is clamped back into view"),
        ],
        gap=16,
        padding=24,
        cross_alignment="start",
    )

    app = nv.App(content=content, title="context_menu Modifier", width=440, height=320)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
