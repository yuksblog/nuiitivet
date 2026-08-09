"""Adaptive toolbar placement: a pane that reacts to its own size.

A content pane holds an explanatory ``Card`` plus a toolbar. The toolbar's
placement follows the pane's **shape**, reported by ``on_size_changed`` on the
pane itself:

- landscape (wider than tall) -> a ``VerticalFloatingToolbar`` on the *right*
- portrait  (taller than wide) -> a ``HorizontalFloatingToolbar`` on the *bottom*

A ``Grid`` holds all three widgets at once — card, right toolbar, bottom toolbar —
and each toolbar is wrapped in a ``Collapsible`` that folds it away along its own
axis. The toolbar tracks are ``"auto"``, so a collapsed toolbar takes the track
with it and the card — on the filling ``"wt"`` track — reclaims the space.

Building it this way keeps **one** card instance: reflowing reshapes the card
rather than replacing it, so anything the user has going on inside (scroll
position, a half-typed field, a selection) survives. Swapping between two
prebuilt arrangements would discard it.

The pane fills the window here, so resizing the window past square flips the
placement. Nothing in the panel refers to the window, so the same panel dropped
into any container reflows on *that* container's shape instead.
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

    def __init__(self) -> None:
        # Filling sizing is what makes the reported size the *available* space
        # rather than the content's intrinsic size.
        super().__init__(width="wt", height="wt")
        # True matches this app's initial 760x460 window, so the first report
        # writes the same value and nothing animates on the first frame.
        self._landscape = nv.Observable(True)
        self._portrait = self._landscape.map(lambda landscape: not landscape)
        self._caption = nv.Observable("")

    def _on_size(self, size: nv.Size) -> None:
        """Receive this widget's own size whenever it changes."""
        landscape = size.width >= size.height
        self._landscape.value = landscape
        self._caption.value = f"pane {size.width}×{size.height} — " + (
            "landscape: toolbar on the right" if landscape else "portrait: toolbar on the bottom"
        )

    def build(self) -> nv.Widget:
        card = nv.Card(
            nv.Column(
                [
                    nv.Text("Adaptive toolbar placement"),
                    nv.Text(self._caption),
                ],
                gap=12,
                padding=24,
                cross_alignment="start",
            ),
            width="wt",
            height="wt",
        )
        # Each toolbar folds along the axis it occupies, so the "auto" track it
        # sits in collapses with it.
        right_toolbar = nv.Collapsible(
            nv.VerticalFloatingToolbar(_actions(), style=nv.ToolbarStyle.standard()),
            opened=self._landscape,
            axis="horizontal",
        )
        bottom_toolbar = nv.Collapsible(
            nv.HorizontalFloatingToolbar(_actions(), style=nv.ToolbarStyle.standard()),
            opened=self._portrait,
            axis="vertical",
        )
        return nv.Grid(
            children=[
                nv.GridItem(card, row=0, column=0),
                nv.GridItem(right_toolbar, row=0, column=1, alignment="center"),
                nv.GridItem(bottom_toolbar, row=1, column=0, alignment="center"),
            ],
            rows=["wt", "auto"],
            columns=["wt", "auto"],
            row_gap=16,
            column_gap=16,
            width="wt",
            height="wt",
        ).modifier(nv.on_size_changed(self._on_size))


def build_root() -> nv.Widget:
    """Factory root (uncalled), so `python -m nuiitivet.dev` can hot-reload it."""
    return nv.Container(
        AdaptiveToolbarPanel(),
        padding=24,
        width="wt",
        height="wt",
    )


def main(png: str = ""):
    app = nv.App(content=build_root, width=760, height=460, title="Adaptive Toolbar Placement")
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
