"""Material Widgets - FabMenu (MD3 Expressive FAB Menu).

A single ``FabMenu`` drives everything through one ``is_open`` observable: the
FAB morphs its icon between ``add`` and ``close``, the labelled actions reveal
with a staggered animation, and tapping outside (or selecting an action)
dismisses the menu via the shared light-dismiss overlay.
"""

from __future__ import annotations

from nuiitivet.material import App, FabMenu, FabMenuItem, FabStyle
from nuiitivet.layout.container import Container


def _items() -> list[FabMenuItem]:
    return [
        FabMenuItem(icon="edit", label="Compose", on_click=lambda: print("Compose")),
        FabMenuItem(icon="image", label="Add photo", on_click=lambda: print("Add photo")),
        FabMenuItem(icon="link", label="Add link", on_click=lambda: print("Add link")),
        FabMenuItem(icon="videocam", label="Add video", on_click=lambda: print("Add video")),
    ]


def main(png_path: str = "") -> None:
    # Anchor the FAB at the bottom-trailing corner; the menu expands upward.
    fab_menu = FabMenu("add", items=_items(), style=FabStyle.primary("m"))
    content = Container(
        padding=16,
        alignment="bottom-right",
        child=fab_menu,
    )
    app = App(
        content=content,
        title="FabMenu",
        width=420,
        height=520,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
