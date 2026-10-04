from typing import Any

import skia

from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.observable import Observable
from nuiitivet.layout.row import Row


def _make_obs(initial):

    class _Tmp:
        x = Observable(initial)

    return _Tmp().x


def test_text_auto_bind_and_unbind(nuiitivet_mount):
    s = _make_obs("hello")
    t = Text(s)
    host = nuiitivet_mount(t)
    assert t._label_unsub is not None
    s.value = "world"
    # `> 0`, not `== 1`: coalescing two invalidations into one would break an
    # exact count with no change in behaviour. What matters is that the binding
    # requested a repaint at all, and that unbinding stopped it.
    assert host.invalidate_count > 0
    after_bind = host.invalidate_count

    t.unmount()
    assert t._label_unsub is None
    s.value = "again"
    assert host.invalidate_count == after_bind


def test_text_observable_change_marks_layout_needs_on_parent(nuiitivet_mount) -> None:
    s = _make_obs("hi")
    bound = Text(s)
    root = Row([Text("Last click:"), bound], gap=8)
    nuiitivet_mount(root)

    root.layout(400, 40)
    assert root.needs_layout is False
    assert bound.needs_layout is False

    s.value = "Clicked: " + ("X" * 80)
    assert root.needs_layout is True


def _paint_clipped_text(label: str, y: int, width: int) -> list[bytes]:
    """Paint a text clipped to a ``width`` x 20 box at ``(4, y)`` and return the rows of a 60 x 40 surface."""
    surface_type: Any = skia.Surface  # the local stub declares no constructor
    surface = surface_type(60, 40)
    canvas = surface.getCanvas()
    canvas.clear(0xFFFFFFFF)
    text = Text(label, max_lines=1, overflow="clip", soft_wrap=False)
    text.layout(width, 20)
    text.paint(canvas, 4, y, width, 20)
    pixels = bytes(surface.makeImageSnapshot().tobytes())
    return [pixels[row * 240 : (row + 1) * 240] for row in range(40)]


def test_text_clipped_to_its_box_draws_nothing_outside_it() -> None:
    rows = _paint_clipped_text("a text far wider than its box", 10, 20)

    white = b"\xff" * 4
    assert any(row[4 * 4 : 24 * 4] != white * 20 for row in rows)
    assert all(row[24 * 4 :] == white * 36 for row in rows)


def test_text_clipped_to_its_box_paints_the_same_rows_when_the_canvas_cuts_it() -> None:
    full = _paint_clipped_text("gjpq3", 10, 50)
    cut = _paint_clipped_text("gjpq3", -5, 50)

    assert cut[:25] == full[15:]
