"""OS file drops with ``drop_target()``: two independent drop zones.

Dragging files in from Finder / Explorer delivers them to the innermost widget
under the drop point that opted in via ``drop_target`` — not globally. This
sample places two zones side by side so the routing is visible: each zone lists
only the files dropped onto it, and a drop outside both zones is discarded.

Interactions:
    - Drag one or more files from your file manager onto either zone.
    - Drop onto the window background: nothing accepts it, nothing happens.
"""

from __future__ import annotations

import nuiitivet.material as nv

_ZONE_W = 240
_ZONE_H = 200

_MUTED = nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT)


class DropZone(nv.ComposableWidget):
    def __init__(self, title: str, tint: nv.ColorRole) -> None:
        super().__init__()
        self._title = title
        self._tint = tint
        self.listing = nv.Observable("Drop files here")

    def _on_drop(self, e: nv.FileDropEvent) -> None:
        names = "\n".join(p.name for p in e.paths)
        self.listing.value = f"{len(e.paths)} file(s) at {e.local_x:.0f}, {e.local_y:.0f}:\n{names}"

    def build(self):
        return nv.Container(
            width=_ZONE_W,
            height=_ZONE_H,
            alignment="center",
            child=nv.Column(
                children=[
                    nv.Text(self._title, type_scale=nv.TypeScale.TITLE_MEDIUM),
                    nv.Text(self.listing, style=_MUTED, type_scale=nv.TypeScale.BODY_SMALL),
                ],
                gap=12,
                cross_alignment="center",
            ),
        ).modifier(
            nv.background(self._tint)
            | nv.corner_radius(12)
            | nv.drop_target(on_drop=self._on_drop)
        )


def main(png: str = ""):
    content = nv.Row(
        children=[
            DropZone("Zone A", nv.ColorRole.SURFACE_CONTAINER_HIGH),
            DropZone("Zone B", nv.ColorRole.SECONDARY_CONTAINER),
        ],
        gap=24,
        padding=24,
    )
    app = nv.App(content=content, title="drop_target — file drop zones", width=560)
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
