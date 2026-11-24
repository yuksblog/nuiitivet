"""A page beside a heavy panel: what the page shows while the layout runs past its deadline.

The panel holds ``ROWS`` rows of cells. Its layout alone takes longer than the
layout's share of a frame, so the page beside it is left pending on every
frame that changes the panel's width.

Change the width by dragging the window's edge, or by pressing the menu button
of the rail. The switch on the page chooses what a pending page shows: its
last layout, or nothing, as before that was painted.

Run::

    uv run python -m nuiitivet.dev run scripts/debug/pending_page_demo.py
"""

from __future__ import annotations

from typing import Any

import nuiitivet.material as nv
from nuiitivet.layout import layout_utils

ROWS = 300

show_last_layout = nv.State(True)

# A hot reload runs this module again: wrap the framework's function, not the last wrapper.
_paint_pending = getattr(layout_utils.paint_pending_child, "wrapped", layout_utils.paint_pending_child)


def _paint_pending_child(child: Any, canvas: Any, x: int, y: int, width: int, height: int) -> None:
    if show_last_layout.value:
        _paint_pending(child, canvas, x, y, width, height)
    else:
        child.set_last_rect(x, y, width, height)


_paint_pending_child.wrapped = _paint_pending  # type: ignore[attr-defined]
layout_utils.paint_pending_child = _paint_pending_child


def build_root() -> nv.Widget:
    rail = nv.NavigationRail(
        children=[
            nv.RailItem(icon="home", label="Home"),
            nv.RailItem(icon="search", label="Search"),
            nv.RailItem(icon="settings", label="Settings"),
        ],
        index=nv.State(0),
        expanded=nv.State(False),
        show_menu_button=True,
    )
    panel = nv.Column(
        [
            nv.Row([nv.Text(f"cell {row}-{column}", width="wt") for column in range(4)], width="wt")
            for row in range(ROWS)
        ],
        width="wt",
        height="wt",
    )
    page = nv.Card(
        nv.Column(
            gap=12,
            padding=24,
            cross_alignment="start",
            children=[
                nv.Text("The page", type_scale=nv.TypeScale.HEADLINE_SMALL),
                nv.Text("Drag the window's edge, or press the menu button of the rail."),
                nv.Row(
                    [nv.Switch(show_last_layout), nv.Text("A pending page shows its last layout")],
                    gap=12,
                    cross_alignment="center",
                ),
                nv.Text(
                    show_last_layout.map(
                        lambda on: (
                            "On: the page keeps its picture while the width changes."
                            if on
                            else "Off: the page is painted as nothing while the width changes."
                        )
                    )
                ),
                *[nv.Button(f"Action {index + 1}") for index in range(4)],
            ],
        ),
        style=nv.CardStyle.filled().copy_with(border_radius=0),
        width="wt",
        height="wt",
    )
    return nv.Row([rail, panel, page], width="wt", height="wt")


def main() -> None:
    nv.App(nv.Window(content=build_root, title="A pending page", width=1100, height=720)).run()


if __name__ == "__main__":
    main()
