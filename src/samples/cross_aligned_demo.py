from __future__ import annotations

from nuiitivet.layout.column import Column
from nuiitivet.layout.cross_aligned import CrossAligned
from nuiitivet.layout.row import Row
from nuiitivet.material import Text
from nuiitivet.material.app import MaterialApp
from nuiitivet.modifiers import background, border, corner_radius
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box


def _color_box(color: str) -> Box:
    return Box(width=Sizing.fixed(40), height=Sizing.fixed(40), background_color=color)


def main() -> None:
    # Column: cross-axis is horizontal.
    col = Column(
        children=[
            _color_box("#4CAF50"),
            CrossAligned(_color_box("#2196F3"), "center"),
            _color_box("#4CAF50"),
            CrossAligned(_color_box("#F44336"), "end"),
            _color_box("#4CAF50"),
        ],
        width=Sizing.fixed(220),
        gap=12,
        padding=12,
        cross_alignment="start",
    )

    col_frame = Box(
        child=col,
        background_color="#F5F5F5",
        border_color="#BDBDBD",
        border_width=1,
    )

    # Row: cross-axis is vertical.
    # Also demonstrates that CrossAligned metadata is preserved through modifiers.
    r2 = CrossAligned(_color_box("#9C27B0"), "end").modifier(
        corner_radius(10) | border("#9C27B0", width=2) | background("#EDE7F6")
    )

    row = Row(
        children=[
            _color_box("#FF9800"),
            r2,
            _color_box("#FF9800"),
            _color_box("#FF9800"),
        ],
        height=Sizing.fixed(140),
        gap=12,
        padding=12,
        cross_alignment="start",
    )

    row_frame = Box(
        child=row,
        background_color="#F5F5F5",
        border_color="#BDBDBD",
        border_width=1,
    )

    content = Column(
        children=[
            Text("CrossAligned Demo", padding=16),
            Text("Column cross_alignment='start' with per-child overrides", padding=(0, 8, 0, 0)),
            col_frame,
            Text("Row cross_alignment='start' with per-child override + modifiers", padding=(0, 16, 0, 0)),
            row_frame,
        ],
        padding=24,
        gap=16,
        cross_alignment="start",
    )

    app = MaterialApp(content=content)
    app.run()


if __name__ == "__main__":
    main()
