"""Step 4 expand sample."""

from __future__ import annotations
import nuiitivet as nv
import nuiitivet.material as md


def _card(label: str, expand: bool = True) -> md.FilledCard:
    # expand=True -> width/height="100%" (Fills grid cell)
    # expand=False -> width/height=default (Fits content)
    w = "100%" if expand else None
    h = "100%" if expand else None

    return md.FilledCard(
        md.Text(label),
        padding=12,
        alignment="center",
        width=w,
        height=h,
    )


def main(png: str = ""):
    widget = nv.Grid(
        rows=["50%", "50%"],
        columns=["50%", "50%"],
        row_gap=12,
        column_gap=12,
        padding=12,
        children=[
            # Top-Left: Expanded
            nv.GridItem(_card("Expanded", expand=True), row=0, column=0),
            # Top-Right: Not Expanded (Centered by default nv.GridItem alignment?)
            # nv.GridItem defaults to expansion? No, nv.GridItem just places it.
            # If the child is smaller than the cell, we need to know how it behaves.
            # By default, nv.Grid cells stretch?
            # In Nuiitivet, children layout is determined by their own constraints passed from parent.
            # If we don't pass flex, it should shrink to fit?
            # Let's explicitly set alignment on nv.GridItem if supported, or just let it float.
            nv.GridItem(_card("Shrink/Wrap\n(No Flex)", expand=False), row=0, column=1),
            # Bottom-Left: Expanded
            nv.GridItem(_card("Expanded", expand=True), row=1, column=0),
            # Bottom-Right: Not Expanded
            nv.GridItem(_card("Shrink/Wrap\n(No Flex)", expand=False), row=1, column=1),
        ],
    )

    app = md.MaterialApp(
        content=widget,
        title_bar=nv.DefaultTitleBar(title="Step 4: Expansion"),
        width=400,
        height=400,
    )
    if png:
        app.render_to_png(png)
        return
    app.run()


if __name__ == "__main__":
    main()
