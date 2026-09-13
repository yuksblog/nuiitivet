"""Layout mode playground: Rows and Columns to drag cards between.

Run with hot reload::

    python -m nuiitivet.dev run scripts/debug/layout_mode_move.py

Enter layout mode with Cmd+Shift+E (Ctrl+Shift+E), then drag a card by its
body. Each container below exercises one reading:

- ``top`` / ``left``: drag along the main axis to reorder in place; drag over
  the other one to move across (the destination is washed and shows the slot)
- ``empty``: an empty destination; the line sits at its start
- ``stacked``: a ``Stack`` child can leave but not reorder; a badge says so
  while it is dragged inside the ``Stack``
- ``from_data`` / ``comprehension``: children not written as a list literal
  (``Column.builder``, a comprehension); a badge appears while a card hovers
  over them and no line is drawn, and their own cards cannot leave

The panels themselves are children of the outer Rows: press one's padding,
between the cards, to reorder it there or move it into ``top``.

Every landed move rewrites this file and hot reload applies it; Cmd+Z undoes.
"""

from __future__ import annotations

import nuiitivet.material as nv


def card(label: str) -> nv.Widget:
    return nv.Card(child=nv.Text(label, padding=12), style=nv.CardStyle.outlined(), key=label)


def panel(child: nv.Widget) -> nv.Widget:
    return child.modifier(nv.border("#9a9a9a", width=1))


def build_root() -> nv.Widget:
    top = nv.Row(
        children=[
            card("A"),
            card("B"),
            card("C"),
        ],
        gap=8,
        padding=8,
    )
    left = nv.Column(
        children=[
            card("one"),
            card("two"),
            card("three"),
        ],
        gap=8,
        padding=8,
    )
    empty = nv.Column(
        children=[],
        gap=8,
        padding=8,
        width=140,
        height=200,
    )
    stacked = nv.Stack(
        children=[
            nv.Container(width=140, height=200).modifier(nv.background("#e3e6f0")),
            card("floating"),
        ],
        alignment="center",
    )
    from_data = nv.Column.builder(
        ["x", "y"],
        lambda item, index: card(item),
        gap=8,
        padding=8,
    )
    comprehension = nv.Row(
        children=[card(tag) for tag in ("p", "q")],
        gap=8,
        padding=8,
    )
    return nv.Column(
        children=[
            nv.Text("top: Row", padding=(8, 0)),
            panel(top),
            nv.Text("left: Column / empty: Column / stacked: Stack", padding=(8, 0)),
            nv.Row(children=[panel(left), panel(empty), panel(stacked)], gap=16),
            nv.Text("from_data: Column.builder / comprehension: Row", padding=(8, 0)),
            nv.Row(children=[panel(from_data), panel(comprehension)], gap=16),
        ],
        padding=16,
        gap=8,
    )


def main(png: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, title="Layout mode: move across", width=720, height=720))
    if png:
        app.render_to_png(png)
        print(f"Rendered {png}")
        return
    app.run()


if __name__ == "__main__":
    main()
