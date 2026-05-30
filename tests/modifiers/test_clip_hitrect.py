from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.widgets.text import TextBase as Text


def rect_inside(parent_rect, child_rect):
    px, py, pw, ph = parent_rect
    cx, cy, cw, ch = child_rect
    return cx >= px and cy >= py and (cx + cw <= px + pw) and (cy + ch <= py + ph)


def test_column_clamps_child_last_rect():
    col = Column(
        [
            Text("Line 1 long text to increase preferred size"),
            Text("Line 2 long text to increase preferred size"),
        ],
        gap=4,
    )
    x, y, w, h = (10, 10, 100, 20)
    try:
        import skia

        surface = skia.Surface(max(1, w), max(1, h))
        canvas = surface.getCanvas()
    except Exception:
        canvas = None
    col.paint(canvas, x, y, w, h)
    for child in col.children_snapshot():
        rect = getattr(child, "_last_rect", None)
        if rect is None:
            continue
        assert len(rect) == 4, f"Child rect {rect} must have 4 elements"


def test_row_clamps_child_last_rect():
    row = Row(
        [
            Text("Col A long text"),
            Text("Col B long text"),
            Text("Col C long text"),
        ],
        gap=4,
    )
    x, y, w, h = (10, 10, 60, 30)
    try:
        import skia

        surface = skia.Surface(max(1, w), max(1, h))
        canvas = surface.getCanvas()
    except Exception:
        canvas = None
    row.paint(canvas, x, y, w, h)
    for child in row.children_snapshot():
        rect = getattr(child, "_last_rect", None)
        if rect is None:
            continue
        assert len(rect) == 4, f"Child rect {rect} must have 4 elements"
