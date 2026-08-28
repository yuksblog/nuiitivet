"""Material Widgets - ExtendedFab with collapse/expand.

Every ExtendedFab below toggles its own collapse/expand state when clicked,
so the morph between the extended pill and the circular FAB can be observed
directly for each colour mapping and size.
"""

from __future__ import annotations

import nuiitivet.material as nv


def _toggling_fab(label: str, icon: str, style: nv.FabStyle) -> nv.ExtendedFab:
    """Return an ExtendedFab that toggles its own expanded state on click."""
    expanded = nv.Observable(True)
    return nv.ExtendedFab(
        label,
        icon=icon,
        style=style,
        expanded=expanded,
        on_click=lambda: expanded.set(not expanded.value),
    )


def main(png_path: str = "") -> None:
    content = nv.Container(
        padding=24,
        child=nv.Column(
            gap=16,
            cross_alignment="start",
            children=[
                nv.Text("Tonal color variants (size s) — click to collapse/expand"),
                nv.Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        _toggling_fab("Compose", "edit", nv.FabStyle.primary()),
                        _toggling_fab("Share", "share", nv.FabStyle.secondary()),
                        _toggling_fab("Save", "save", nv.FabStyle.tertiary()),
                    ],
                ),
                nv.Text("Solid color variants (size s) — click to collapse/expand"),
                nv.Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        _toggling_fab("Compose", "edit", nv.FabStyle.primary_solid()),
                        _toggling_fab("Share", "share", nv.FabStyle.secondary_solid()),
                        _toggling_fab("Save", "save", nv.FabStyle.tertiary_solid()),
                    ],
                ),
                nv.Text("Sizes (s / m / l) — click to collapse/expand"),
                nv.Row(
                    gap=16,
                    cross_alignment="center",
                    children=[
                        _toggling_fab("Compose", "edit", nv.FabStyle.primary("s")),
                        _toggling_fab("Compose", "edit", nv.FabStyle.primary("m")),
                        _toggling_fab("Compose", "edit", nv.FabStyle.primary("l")),
                    ],
                ),
            ],
        ),
    )
    app = nv.App(nv.Window(content=content, title="ExtendedFab", width=660, height=420))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run()


if __name__ == "__main__":
    main()
