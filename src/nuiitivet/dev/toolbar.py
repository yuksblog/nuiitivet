"""The bar over a selected widget: its name, then its presets in a select box each.

The bar hangs just above the selection, left-aligned with it, and drops
below it when the window's top leaves no room. It carries the caption's
job for the selection: the name leads, and a box per preset follows. A box
names what it writes and shows the value in the source: the preset's name,
``custom`` for a value that is not a preset, or the default when the
keyword is absent. A click on a box opens its list under it; a click on a
row writes. The geometry lives here so that the mode's hit-testing and the
overlay's painting read the same rects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .hud import fit_inside

Rect = tuple[float, float, float, float]
Size = tuple[float, float]

#: The bar's height, and the room between it and the selection.
BAR_H = 32.0
STANDOFF = 4.0
#: A select box's height and the room between its edge and its text.
BOX_H = 24.0
BOX_PAD = 8.0
#: Between the name and the first box, and between boxes.
GAP = 8.0
#: A row of an open list.
ROW_H = 24.0
#: The glyph that marks a box as one that opens.
ARROW = "▾"


@dataclass(frozen=True)
class Box:
    """One select box.

    Attributes:
        label: What the box writes, as shown: ``style``, ``size``, ``type scale``.
        value: The value shown in the box.
        options: The rows the box opens, in order.
        current: The row the source holds, or ``None`` when it holds none of them.
    """

    label: str
    value: str
    options: tuple[str, ...]
    current: Optional[int]

    @property
    def text(self) -> str:
        """The box's text: its label, its value and the arrow."""
        return f"{self.label}  {self.value}  {ARROW}"


@dataclass(frozen=True)
class Toolbar:
    """The bar's name and boxes, where it hangs, and the list open under one box.

    Attributes:
        name: The selection's name, leading the bar.
        boxes: Left to right after the name.
        anchor: The selection's rect, which the bar hangs over.
        open: The box whose list is open, or ``None``.
        highlighted: The row ``Enter`` would write, in the open list.
    """

    name: str
    boxes: tuple[Box, ...]
    anchor: Rect
    open: Optional[int] = None
    highlighted: int = 0


def backdrop(bar: Toolbar, measure: Callable[[str], float], window: Size) -> Rect:
    """The bar's panel: over the anchor, under it when the top leaves no room, pushed inside the window.

    An unknown ``window`` (``(0, 0)``) pushes nothing.
    """
    width = BOX_PAD * 2 + measure(bar.name) + sum(measure(box.text) + BOX_PAD * 2 + GAP for box in bar.boxes)
    ax, ay, _aw, ah = bar.anchor
    y = ay - STANDOFF - BAR_H
    if y < 0.0:
        y = ay + ah + STANDOFF
    x = ax
    if window[0] > 0 and window[1] > 0:
        x, y = fit_inside((x, y), (width, BAR_H), window)
    return (x, y, width, BAR_H)


def name_rect(bar: Toolbar, measure: Callable[[str], float], window: Size) -> Rect:
    """Where the name sits: at the bar's left, the bar's height."""
    x, y, _w, h = backdrop(bar, measure, window)
    return (x + BOX_PAD, y, measure(bar.name), h)


def box_rects(bar: Toolbar, measure: Callable[[str], float], window: Size) -> list[Rect]:
    """Each box's rect, left to right after the name, centred in the bar's height."""
    nx, ny, nw, _nh = name_rect(bar, measure, window)
    x = nx + nw + GAP
    rects: list[Rect] = []
    for box in bar.boxes:
        width = measure(box.text) + BOX_PAD * 2
        rects.append((x, ny + (BAR_H - BOX_H) / 2.0, width, BOX_H))
        x += width + GAP
    return rects


def row_rects(bar: Toolbar, measure: Callable[[str], float], window: Size) -> list[Rect]:
    """Each row of the open list, under its box and inside the window; empty when no list is open."""
    if bar.open is None:
        return []
    box = bar.boxes[bar.open]
    bx, _by, bw, _bh = box_rects(bar, measure, window)[bar.open]
    _px, py, _pw, ph = backdrop(bar, measure, window)
    row_width = max(bw, max((measure(option) for option in box.options), default=0.0) + BOX_PAD * 2)
    top = py + ph
    if window[0] > 0 and window[1] > 0:
        bx, top = fit_inside((bx, top), (row_width, ROW_H * len(box.options)), window)
    return [(bx, top + index * ROW_H, row_width, ROW_H) for index in range(len(box.options))]


def hit(bar: Toolbar, measure: Callable[[str], float], window: Size, x: float, y: float) -> Optional[tuple[str, int]]:
    """What the point is on: ``("row", i)`` of the open list, ``("box", i)``, or ``("bar", 0)`` on the panel.

    ``None`` off the bar.
    """
    for index, rect in enumerate(row_rects(bar, measure, window)):
        if _inside(rect, x, y):
            return ("row", index)
    for index, rect in enumerate(box_rects(bar, measure, window)):
        if _inside(rect, x, y):
            return ("box", index)
    return ("bar", 0) if _inside(backdrop(bar, measure, window), x, y) else None


def _inside(rect: Rect, x: float, y: float) -> bool:
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


__all__ = [
    "ARROW",
    "BAR_H",
    "BOX_H",
    "BOX_PAD",
    "Box",
    "ROW_H",
    "STANDOFF",
    "Toolbar",
    "backdrop",
    "box_rects",
    "hit",
    "name_rect",
    "row_rects",
]
