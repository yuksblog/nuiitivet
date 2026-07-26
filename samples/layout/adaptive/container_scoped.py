"""Container-scoped adaptive layout: adaptive toolbar placement.

A content pane holds an explanatory ``Card`` plus a toolbar. The toolbar's
placement follows the pane's **shape**, read from its own ``Geometry``:

- landscape (wider than tall) -> a ``VerticalFloatingToolbar`` on the *right*
- portrait  (taller than wide) -> a ``HorizontalFloatingToolbar`` on the *bottom*

The pane fills the window here, so resizing the window past square flips the
placement. Because it reads its own ``Geometry``, the same panel dropped into any
container reflows on *that* container's shape.
"""

import nuiitivet.material as nv


def _actions() -> list[nv.IconButton]:
    return [
        nv.IconButton("format_bold", style=nv.IconButtonStyle.standard()),
        nv.IconButton("format_italic", style=nv.IconButtonStyle.standard()),
        nv.IconButton("link", style=nv.IconButtonStyle.standard()),
        nv.IconButton("image", style=nv.IconButtonStyle.filled()),
    ]


class AdaptiveToolbarPanel(nv.ComposableWidget):
    """Card + toolbar; toolbar sits on the right when wide, below when tall."""

    def on_mount(self) -> None:
        # ``Geometry.of`` needs a mounted context (an ancestor chain), so the
        # bound values are derived here — not in ``__init__``, where this widget
        # has no ancestors yet. ``build()`` then just references them.
        size = nv.Geometry.of(self).size
        self._index = size.map(lambda s: 1 if s.width >= s.height else 0)
        self._caption = size.map(
            lambda s: f"pane {s.width}×{s.height} — "
            + ("landscape: toolbar on the right" if s.width >= s.height else "portrait: toolbar on the bottom")
        )
        super().on_mount()

    def _card(self) -> nv.Widget:
        return nv.Card(
            nv.Column(
                [
                    nv.Text("Adaptive toolbar placement"),
                    nv.Text(self._caption),
                ],
                gap=12,
                padding=24,
                cross_alignment="start",
            ),
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )

    def build(self) -> nv.Widget:
        portrait = nv.Column(
            [self._card(), nv.HorizontalFloatingToolbar(_actions(), style=nv.ToolbarStyle.standard())],
            gap=16,
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )
        landscape = nv.Row(
            [self._card(), nv.VerticalFloatingToolbar(_actions(), style=nv.ToolbarStyle.standard())],
            gap=16,
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )
        # Deck mounts both arrangements and shows one by the shape-derived index.
        return nv.Deck(
            children=[portrait, landscape],
            index=self._index,
            width=nv.Sizing.flex(1),
            height=nv.Sizing.flex(1),
        )


def build_root() -> nv.Widget:
    """Factory root (uncalled), so `python -m nuiitivet.dev` can hot-reload it."""
    # A filling Geometry: the panel reflows on its own box (here, the window).
    return nv.Container(
        nv.Geometry(AdaptiveToolbarPanel(), width="100%", height="100%"),
        padding=24,
        width=nv.Sizing.flex(1),
        height=nv.Sizing.flex(1),
    )


def main(png: str = ""):
    app = nv.App(content=build_root, width=760, height=460, title="Container-scoped Adaptive Layout")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
