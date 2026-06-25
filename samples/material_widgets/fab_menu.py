"""Material Widgets - FabMenu (MD3 Expressive FAB Menu).

A single ``FabMenu`` drives everything through one ``is_open`` observable: the
FAB morphs its icon between ``add`` and ``close``, the labelled actions reveal
with a staggered animation, and tapping outside (or selecting an action)
dismisses the menu via the shared light-dismiss overlay.
"""

from __future__ import annotations

from nuiitivet.material import App, ExtendedFab, Fab, FabMenu, FabMenuItem, FabStyle
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable

_ACTIONS = [
    ("edit", "Compose"),
    ("image", "Add photo"),
    ("link", "Add link"),
    ("videocam", "Add video"),
]


def _items() -> list[FabMenuItem]:
    return [
        FabMenuItem(icon=icon, label=label, on_click=lambda label=label: print(label))
        for icon, label in _ACTIONS
    ]


def _build_interactive_content() -> Container:
    """The real, interactive FabMenu anchored at the bottom-trailing corner."""
    fab_menu = FabMenu("add", items=_items(), style=FabStyle.primary("m"))
    return Container(padding=16, alignment="bottom-right", child=fab_menu)


def _build_png_content() -> Container:
    """Static open-state preview for the screenshot.

    The real menu list is a light-dismiss overlay with a staggered reveal
    animation, so it is not captured by ``render_to_png``.  This mirrors the
    open state with static tonal pills above the solid close button.
    """
    pills = [
        ExtendedFab(label, icon=icon, style=FabStyle.primary(), expanded=Observable(True))
        for icon, label in _ACTIONS
    ]
    return Container(
        padding=16,
        alignment="bottom-right",
        child=Column(
            gap=8,
            cross_alignment="end",
            children=[*pills, Fab("close", style=FabStyle.primary_solid("m"))],
        ),
    )


def main(png_path: str = "") -> None:
    if png_path:
        app = App(content=_build_png_content(), title="FabMenu", width=420, height=520)
        app.render_to_png(png_path)
    else:
        app = App(content=_build_interactive_content(), title="FabMenu", width=420, height=520)
        app.run()


if __name__ == "__main__":
    main()
