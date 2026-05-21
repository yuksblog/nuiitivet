"""Material Widgets - Menu (rendered inline)."""

from __future__ import annotations

import nuiitivet as nv
from nuiitivet.material import App, Menu, MenuDivider, MenuItem, SubMenuItem
from nuiitivet.layout.container import Container


def main(png_path: str = "") -> None:
    menu = Menu(
        items=[
            MenuItem("New", leading_icon="add"),
            MenuItem("Open...", leading_icon="folder_open"),
            MenuDivider(),
            MenuItem("Save", leading_icon="save", trailing="Ctrl+S"),
            MenuItem("Save As...", trailing="Shift+Ctrl+S", disabled=True),
            SubMenuItem(
                "Export",
                items=[MenuItem("PNG"), MenuItem("SVG")],
            ),
            MenuDivider(),
            MenuItem("Exit"),
        ],
    )

    app = App(
        content=Container(padding=24, child=menu),
        title_bar=nv.DefaultTitleBar(title="Menu"),
        width=360,
        height=380,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
