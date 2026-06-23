"""Material Widgets - ExtendedFab with collapse/expand.

Every ExtendedFab below toggles its own collapse/expand state when clicked,
so the morph between the extended pill and the circular FAB can be observed
directly for each colour mapping and size.
"""

from __future__ import annotations

from nuiitivet.material import App, ExtendedFab, FabStyle, Text
from nuiitivet.observable import Observable
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row


def _toggling_fab(label: str, icon: str, style: FabStyle) -> ExtendedFab:
    """Return an ExtendedFab that toggles its own expanded state on click."""
    expanded = Observable(True)
    return ExtendedFab(
        label,
        icon=icon,
        style=style,
        expanded=expanded,
        on_click=lambda: setattr(expanded, "value", not expanded.value),
    )


def main(png_path: str = "") -> None:
    content = Container(
        padding=24,
        child=Column(
            gap=16,
            cross_alignment="start",
            children=[
                Text("Tonal color variants (size s) — click to collapse/expand"),
                Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        _toggling_fab("Compose", "edit", FabStyle.primary()),
                        _toggling_fab("Share", "share", FabStyle.secondary()),
                        _toggling_fab("Save", "save", FabStyle.tertiary()),
                    ],
                ),
                Text("Solid color variants (size s) — click to collapse/expand"),
                Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        _toggling_fab("Compose", "edit", FabStyle.primary_solid()),
                        _toggling_fab("Share", "share", FabStyle.secondary_solid()),
                        _toggling_fab("Save", "save", FabStyle.tertiary_solid()),
                    ],
                ),
                Text("Sizes (s / m / l) — click to collapse/expand"),
                Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        _toggling_fab("Compose", "edit", FabStyle.primary("s")),
                        _toggling_fab("Compose", "edit", FabStyle.primary("m")),
                        _toggling_fab("Compose", "edit", FabStyle.primary("l")),
                    ],
                ),
            ],
        ),
    )
    app = App(
        content=content,
        title="ExtendedFab",
        width=660,
        height=420,
    )
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
