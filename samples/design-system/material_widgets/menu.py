"""Material Widgets - Menu (rendered inline)."""

from __future__ import annotations

import nuiitivet.material as nv


def main(png_path: str = "") -> None:
    menu = nv.Menu(
        items=[
            nv.MenuItem("New", leading_icon="add"),
            nv.MenuItem("Open...", leading_icon="folder_open"),
            nv.MenuDivider(),
            nv.MenuItem("Save", leading_icon="save", trailing="Ctrl+S"),
            nv.MenuItem("Save As...", trailing="Shift+Ctrl+S", disabled=True),
            nv.SubMenuItem(
                "Export",
                items=[nv.MenuItem("PNG"), nv.MenuItem("SVG")],
            ),
            nv.MenuDivider(),
            nv.MenuItem("Exit"),
        ],
    )

    app = nv.App(nv.Window(content=nv.Container(padding=24, child=menu), title="Menu", width=460, height=380))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
