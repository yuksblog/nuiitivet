"""Inside a frame the layout stops at its limit, at a child whose rect its parent decided.

The limit is a share of a frame, counted from the start of the layout. A child
past it is left pending: it keeps its rect, nothing below it runs, paint draws
its last layout, and the layout of the next frame lays it out. A child sized by
its content is measured and laid out whatever the time. Outside a frame, where
no loop runs, the layout runs to its end.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Callable, List, Optional, Tuple

import pytest
import skia

from nuiitivet.layout import layout_utils
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.deck import Deck
from nuiitivet.layout.grid import Grid, GridItem
from nuiitivet.layout.layout_utils import has_pending_layout, layout_frame
from nuiitivet.layout.row import Row
from nuiitivet.layout.scrollable import VerticalScrollable
from nuiitivet.layout.stack import Stack
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.overlay.overlay import Overlay
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.rendering.skia import make_raster_surface
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgeting import frame_clock, idle_work
from nuiitivet.widgeting.frame_clock import begin_frame, end_frame
from nuiitivet.widgeting.idle_work import has_idle_work
from nuiitivet.widgeting.paint_replay import replay_safe
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box


class _App:
    def __init__(self) -> None:
        self.invalidations = 0
        self._pointer_capture_manager = PointerCaptureManager()

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.invalidations += 1


class _Probe(Box):
    """A box that records its measurements, its layouts and its paints."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.measured: List[Tuple[Optional[int], Optional[int]]] = []
        self.laid_out: List[Tuple[int, int]] = []
        self.painted = 0
        self.painted_at: List[Tuple[int, int, int, int]] = []

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        self.measured.append((max_width, max_height))
        return super().preferred_size(max_width=max_width, max_height=max_height)

    def layout(self, width: int, height: int) -> None:
        self.laid_out.append((width, height))
        super().layout(width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1
        self.painted_at.append((x, y, width, height))
        super().paint(canvas, x, y, width, height)


@pytest.fixture(autouse=True)
def no_leftover_state():
    idle_work._tasks.clear()
    layout_utils._pending.clear()
    frame_clock._started_at = None
    yield
    idle_work._tasks.clear()
    layout_utils._pending.clear()
    frame_clock._started_at = None


@pytest.fixture
def no_time_left(monkeypatch):
    """The limit is spent as the layout begins: inside a frame it descends into no parent-sized child."""
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.0)


def _give_time(monkeypatch) -> None:
    """The frames from here on have more time than any layout in this file takes."""
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 1000.0)


def _frame(root, width: int, height: int, *, root_pass: bool = True) -> None:
    """One frame's layout. No idle time runs before or after it."""
    begin_frame(perf_counter())
    try:
        layout_frame(root, width, height, root_pass=root_pass)
    finally:
        end_frame()


def _fixed(width: int = 50, height: int = 20) -> _Probe:
    return _Probe(width=Sizing.fixed(width), height=Sizing.fixed(height))


# ---- The measurement ----------------------------------------------------------
def test_a_column_does_not_measure_a_child_sized_by_the_parent() -> None:
    fixed = _fixed()
    weighted = _Probe(width=Sizing.weight(), height=Sizing.weight())
    auto = _Probe(width=Sizing.auto(), height=Sizing.fixed(20))
    column = Column([fixed, weighted, auto])
    column.layout(200, 100)

    assert fixed.measured == [] and weighted.measured == [], "each axis comes from the parent"
    assert auto.measured, "an auto axis asks the child"
    assert fixed.layout_rect == (0, 0, 50, 20)
    assert weighted.layout_rect == (0, 20, 200, 60)


def test_a_row_does_not_measure_a_child_sized_by_the_parent() -> None:
    fixed = _fixed()
    row = Row([fixed, _Probe(width=Sizing.weight(), height=Sizing.auto())])
    row.layout(200, 100)

    assert fixed.measured == []
    assert fixed.layout_rect == (0, 0, 50, 20)


def test_a_container_does_not_measure_a_child_sized_by_the_parent() -> None:
    fixed = _fixed()
    container = Container(fixed, alignment="center")
    container.layout(200, 100)
    assert fixed.measured == []
    assert fixed.layout_rect == (75, 40, 50, 20)

    outer = _fixed(50, 20)
    Container(outer, width=100, height=60).preferred_size()
    assert outer.measured == [], "a container fixed on both sides answers without its child"


def test_a_stack_does_not_measure_a_child_sized_by_the_parent() -> None:
    fixed = _fixed()
    filling = _Probe(width=Sizing.weight(), height=Sizing.weight())
    stack = Stack([fixed, filling])
    stack.layout(200, 100)

    assert fixed.measured == [] and filling.measured == []
    assert fixed.layout_rect == (0, 0, 50, 20)
    assert filling.layout_rect == (0, 0, 200, 100)


def test_a_grid_does_not_measure_a_child_in_fixed_tracks() -> None:
    in_fixed = _fixed()
    in_auto = _fixed()
    grid = Grid(
        rows=[30, "auto"],
        columns=[60],
        children=[GridItem(in_fixed, row=0, column=0), GridItem(in_auto, row=1, column=0)],
    )
    grid.layout(200, 100)

    assert in_fixed.measured == []
    assert in_auto.measured, "an auto track takes its size from the child"
    item = in_fixed.parent
    assert item is not None and item.layout_rect == (0, 0, 60, 30), "the item takes the cell"


# ---- The cut ------------------------------------------------------------------
def test_past_the_limit_a_child_sized_by_the_parent_is_left_pending(no_time_left) -> None:
    app = _App()
    fixed = _fixed()
    auto = _Probe(width=Sizing.auto(), height=Sizing.auto())
    column = Column([fixed, auto])
    column.mount(app)
    _frame(column, 200, 100)

    assert fixed.laid_out == [], "nothing below the pending child ran"
    assert fixed.layout_rect == (0, 0, 50, 20), "it keeps the rect its parent decided"
    assert fixed._layout_pending
    assert auto.laid_out == [(0, 0)], "a child sized by its content is laid out whatever the time"
    assert has_pending_layout()
    assert not has_idle_work(), "a pending subtree is not idle work"


def test_the_limit_counts_from_the_start_of_the_layout() -> None:
    boxes = [_fixed() for _ in range(5)]
    column = Column(boxes)
    column.mount(_App())

    # The frame began a second ago: what ran before the layout took that long.
    begin_frame(perf_counter() - 1.0)
    try:
        layout_frame(column, 200, 100, root_pass=True)
    finally:
        end_frame()

    assert all(box.laid_out == [(50, 20)] for box in boxes)
    assert not has_pending_layout()


# ---- The frames after ---------------------------------------------------------
def test_the_next_frame_lays_a_pending_child_out_with_no_idle_time_between(no_time_left, monkeypatch) -> None:
    fixed = _fixed()
    column = Column([fixed])
    column.mount(_App())
    _frame(column, 200, 100)
    assert fixed._layout_pending and not column.needs_layout

    _give_time(monkeypatch)
    _frame(column, 200, 100, root_pass=False)

    assert fixed.laid_out == [(50, 20)], "at the rect its parent decided"
    assert fixed.layout_rect == (0, 0, 50, 20), "nothing moved"
    assert not fixed._layout_pending and not has_pending_layout()
    assert not column.needs_layout, "the parent's pass stands"

    column.paint(None, 0, 0, 200, 100)
    assert fixed.painted == 1


def test_the_frames_after_fill_the_tree_top_down_and_each_within_the_limit(no_time_left, monkeypatch) -> None:
    inner = [_fixed() for _ in range(3)]
    rows = [Row([box], width=Sizing.weight(), height=Sizing.fixed(20)) for box in inner]
    column = Column(rows, width=Sizing.fixed(200), height=Sizing.fixed(100))
    column.mount(_App())
    _frame(column, 200, 100)
    assert all(row._layout_pending for row in rows)

    # The limit runs out while the first row is laid out: the row's own child
    # is left pending in turn, and the other rows wait for the frame after.
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.5)
    clock = [0.0, 0.0]
    monkeypatch.setattr(layout_utils, "perf_counter", lambda: clock.pop(0) if clock else float("inf"))
    _frame(column, 200, 100, root_pass=False)
    assert not rows[0]._layout_pending and rows[1]._layout_pending
    assert inner[0]._layout_pending, "the limit cuts inside the row too"

    # The next frame finishes that row before it starts the rows after it.
    clock[:] = [0.0, 0.0]
    _frame(column, 200, 100, root_pass=False)
    assert not inner[0]._layout_pending and rows[1]._layout_pending

    monkeypatch.setattr(layout_utils, "perf_counter", perf_counter)
    _give_time(monkeypatch)
    _frame(column, 200, 100, root_pass=False)
    assert not has_pending_layout()
    assert [box.layout_rect for box in inner] == [(0, 0, 50, 20)] * 3


def test_a_clean_child_left_pending_at_a_new_size_is_laid_out_by_the_next_frame(no_time_left, monkeypatch) -> None:
    weighted = _Probe(width=Sizing.weight(), height=Sizing.weight())
    column = Column([weighted])
    column.mount(_App())
    column.layout(200, 100)  # outside a frame: the child is clean at 200x100

    _frame(column, 300, 100)
    assert weighted._layout_pending and weighted.layout_rect == (0, 0, 300, 100)
    assert not weighted.needs_layout, "nothing below it changed"

    _give_time(monkeypatch)
    _frame(column, 300, 100)
    assert weighted.laid_out == [(200, 100), (300, 100)], "the rect did not change again, and it is still laid out"
    assert not has_pending_layout()


def test_a_pass_with_time_lays_a_pending_child_out_though_it_is_clean_at_that_size(no_time_left, monkeypatch) -> None:
    first = _Probe(width=Sizing.weight(), height=Sizing.weight())
    second = _Probe(width=Sizing.weight(), height=Sizing.weight())
    column = Column([first, second])
    column.mount(_App())
    column.layout(200, 100)  # outside a frame: both clean
    _frame(column, 300, 100)
    assert first._layout_pending and not first.needs_layout

    # The pass has time for one child, and the child after it is dirty:
    # nothing is left for the pending subtrees after the pass.
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.5)
    clock = [0.0, 0.0]
    monkeypatch.setattr(layout_utils, "perf_counter", lambda: clock.pop(0) if clock else float("inf"))
    second.mark_needs_layout()
    _frame(column, 300, 100)
    assert not first._layout_pending, "the pass reached it in time"
    assert first.laid_out == [(200, 50), (300, 50)]


def test_a_pending_child_taken_out_of_the_tree_stays_dirty(no_time_left, monkeypatch) -> None:
    weighted = _Probe(width=Sizing.weight(), height=Sizing.weight())
    column = Column([weighted])
    column.mount(_App())
    column.layout(200, 100)  # outside a frame: clean at 200x100
    _frame(column, 300, 100)
    assert weighted._layout_pending and not weighted.needs_layout

    column.remove_child(weighted)
    _give_time(monkeypatch)
    _frame(column, 300, 100, root_pass=False)
    assert not has_pending_layout()
    assert weighted.laid_out == [(200, 100)], "no frame shows it: it is not laid out"
    assert weighted.needs_layout, "the pass that takes it back lays it out"


def test_a_root_whose_layout_raises_does_not_keep_the_pending_children_waiting(no_time_left, monkeypatch) -> None:
    class Raising(Column):
        fail = False

        def layout(self, width: int, height: int) -> None:
            if self.fail:
                raise RuntimeError("the root's layout failed")
            super().layout(width, height)

    fixed = _fixed()
    root = Raising([fixed])
    root.mount(_App())
    _frame(root, 200, 100)
    assert fixed._layout_pending

    _give_time(monkeypatch)
    root.fail = True
    with pytest.raises(RuntimeError):
        _frame(root, 200, 100)
    assert fixed.laid_out == [(50, 20)]
    assert not has_pending_layout()


def test_a_pass_clears_the_pending_mark_of_a_child_with_its_own_layout(no_time_left, monkeypatch) -> None:
    class OwnLayout(Box):
        """A widget whose ``layout`` does not reach the kernel's."""

        def layout(self, width: int, height: int) -> None:
            self.set_layout_rect(0, 0, width, height)

    child = OwnLayout(width=Sizing.fixed(50), height=Sizing.fixed(20))
    column = Column([child])
    column.mount(_App())
    _frame(column, 200, 100)
    assert child._layout_pending

    # The pass has time for the child; nothing is left for the pending subtrees after it.
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.5)
    clock = [0.0, 0.0]
    monkeypatch.setattr(layout_utils, "perf_counter", lambda: clock.pop(0) if clock else float("inf"))
    column.mark_needs_layout()
    _frame(column, 200, 100)
    assert not child._layout_pending, "the pass laid it out"


def test_a_pending_child_laid_out_by_a_later_pass_is_not_laid_out_again(no_time_left, monkeypatch) -> None:
    fixed = _fixed()
    column = Column([fixed])
    column.mount(_App())
    _frame(column, 200, 100)

    column.layout(200, 100)  # outside a frame: the pass descends
    assert fixed.laid_out == [(50, 20)]
    _give_time(monkeypatch)
    _frame(column, 200, 100, root_pass=False)
    assert fixed.laid_out == [(50, 20)], "the frame found nothing left to do"


# ---- What a pending child shows -----------------------------------------------
def _in_a_grid(child: Widget) -> Grid:
    return Grid(rows=[100], columns=[200], children=[GridItem(child, row=0, column=0)])


# The parents that leave a child pending, and whether a wider parent gives the child a wider rect.
PARENTS: List[Tuple[Callable[[Widget], Widget], bool]] = [
    (lambda child: Column([child]), True),
    (lambda child: Row([child]), True),
    (lambda child: Stack([child]), True),
    (lambda child: Deck([child]), True),
    (lambda child: Container(child), True),
    (_in_a_grid, False),
]
PARENT_IDS = ["column", "row", "stack", "deck", "container", "grid"]


@pytest.mark.parametrize("make", [make for make, _ in PARENTS], ids=PARENT_IDS)
def test_a_pending_child_never_laid_out_is_painted_as_nothing(make, no_time_left) -> None:
    probe = _fixed()
    parent = make(probe)
    parent.mount(_App())
    _frame(parent, 200, 100)
    pending = parent.children_snapshot()[0]
    assert pending._layout_pending

    parent.paint(None, 0, 0, 200, 100)

    assert probe.painted == 0
    assert pending.last_rect is not None, "the parent still placed it"


@pytest.mark.parametrize(("make", "resizes"), PARENTS, ids=PARENT_IDS)
def test_a_pending_child_is_painted_at_the_size_of_its_last_layout(make, resizes, no_time_left) -> None:
    probe = _Probe(width=Sizing.weight(), height=Sizing.weight())
    parent = make(probe)
    parent.mount(_App())
    parent.layout(200, 100)  # outside a frame: the whole tree is laid out
    pending = parent.children_snapshot()[0]
    assert probe.layout_rect is not None and pending.layout_rect is not None
    old_size = probe.layout_rect[2:]

    probe.mark_needs_layout()
    _frame(parent, 300, 100)
    rect = pending.layout_rect
    assert pending._layout_pending
    assert (rect[2:] != pending._laid_out_size) is resizes

    parent.paint(None, 0, 0, 300, 100)

    assert [at[2:] for at in probe.painted_at] == [old_size]
    assert pending.last_rect == rect, "its last rect is the rect it has now"


def _red_page() -> Tuple[Column, Box]:
    page = Box(width=Sizing.weight(), height=Sizing.weight(), background_color=(255, 0, 0, 255))
    column = Column([page])
    column.mount(_App())
    column.layout(100, 100)  # outside a frame: the page is laid out at 100x100
    return column, page


def _paint_on_white(root: Widget, width: int, height: int) -> Callable[[int, int], Tuple[int, int, int]]:
    surface = make_raster_surface(200, 200)
    canvas = surface.getCanvas()
    canvas.clear(0xFFFFFFFF)
    root.paint(canvas, 0, 0, width, height)
    # The surface's own channel order differs between platforms.
    pixels = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    return lambda x, y: (int(pixels[y, x, 0]), int(pixels[y, x, 1]), int(pixels[y, x, 2]))


RED = (255, 0, 0)
WHITE = (255, 255, 255)


def test_a_pending_child_that_grew_leaves_a_band(no_time_left) -> None:
    column, page = _red_page()
    _frame(column, 150, 100)
    assert page._layout_pending and page.layout_rect == (0, 0, 150, 100)

    color_at = _paint_on_white(column, 150, 100)

    assert color_at(50, 50) == RED, "its last layout shows"
    assert color_at(125, 50) == WHITE, "the part it grew by is not painted"


def test_a_pending_child_that_shrank_is_cut_at_its_rect(no_time_left) -> None:
    column, page = _red_page()
    _frame(column, 60, 100)
    assert page._layout_pending and page.layout_rect == (0, 0, 60, 100)

    color_at = _paint_on_white(column, 60, 100)

    assert color_at(30, 50) == RED
    assert color_at(80, 50) == WHITE, "its last layout does not reach beyond the rect it has now"


def test_a_pending_child_is_cut_only_on_the_sides_it_shrank_on(no_time_left) -> None:
    class Overflowing(Box):
        """A box that draws a band to the left of its rect, as a shadow of something inside it would."""

        def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
            super().paint(canvas, x, y, width, height)
            blue = skia.Paint()
            blue.setColor(0xFF0000FF)
            canvas.drawRect(skia.Rect.MakeXYWH(x - 10, y, 10, height), blue)

    page = Overflowing(width=Sizing.weight(), height=Sizing.weight(), background_color=(255, 0, 0, 255))
    column = Column([page], padding=20)
    column.mount(_App())
    column.layout(140, 140)
    _frame(column, 100, 140)
    assert page._layout_pending and page.layout_rect == (20, 20, 60, 100)

    color_at = _paint_on_white(column, 100, 140)

    assert color_at(15, 50) == (0, 0, 255), "what it draws beyond a side that did not shrink stays"
    assert color_at(50, 50) == RED
    assert color_at(90, 50) == WHITE, "the side that shrank is cut"


def test_a_pending_child_laid_out_by_another_path_is_painted_at_that_size(no_time_left) -> None:
    probe = _Probe(width=Sizing.weight(), height=Sizing.weight())
    column = Column([probe])
    column.mount(_App())
    column.layout(200, 100)
    # As a parent that lays its child out itself does.
    probe.layout(120, 100)
    probe.set_layout_rect(0, 0, 120, 100)

    _frame(column, 300, 100)
    assert probe._layout_pending
    column.paint(None, 0, 0, 300, 100)

    assert [at[2:] for at in probe.painted_at] == [(120, 100)]


def test_a_pending_child_with_a_recording_is_drawn_without_its_paint(no_time_left) -> None:
    class Recorded(Box):
        painted = 0

        @replay_safe
        def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
            self.painted += 1
            super().paint(canvas, x, y, width, height)

    page = Recorded(width=Sizing.weight(), height=Sizing.weight(), background_color=(255, 0, 0, 255))
    column = Column([page])
    column.mount(_App())
    column.layout(100, 100)
    _paint_on_white(column, 100, 100)
    assert page.painted == 1 and page._replay_picture is not None

    _frame(column, 150, 100)
    assert page._layout_pending
    color_at = _paint_on_white(column, 150, 100)

    assert page.painted == 1
    assert color_at(50, 50) == RED and color_at(125, 50) == WHITE


def test_a_change_below_a_pending_child_shows_once_it_is_laid_out(no_time_left, monkeypatch) -> None:
    class Undeclared(Box):
        """A box whose paint is not declared safe to replay: nothing holding it is recorded."""

        def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
            super().paint(canvas, x, y, width, height)

    row = Row(
        [Box(width=Sizing.fixed(20), height=Sizing.fixed(20), background_color=(255, 0, 0, 255))],
        width=Sizing.weight(),
        height=Sizing.fixed(20),
    )
    page = Column(
        [row, Undeclared(width=Sizing.fixed(5), height=Sizing.fixed(5))],
        width=Sizing.weight(),
        height=Sizing.weight(),
    )
    column = Column([page])
    column.mount(_App())
    column.layout(100, 100)
    _paint_on_white(column, 100, 100)

    row.add_child(Box(width=Sizing.fixed(20), height=Sizing.fixed(20), background_color=(0, 255, 0, 255)))
    _frame(column, 100, 100)
    assert page._layout_pending
    # The page stays pending over several frames: each paints the row from the layout it had.
    for _ in range(3):
        assert _paint_on_white(column, 100, 100)(30, 10) == WHITE
        _frame(column, 100, 100, root_pass=False)

    _give_time(monkeypatch)
    _frame(column, 100, 100, root_pass=False)
    assert not page._layout_pending

    assert _paint_on_white(column, 100, 100)(30, 10) == (0, 255, 0)
    assert _paint_on_white(column, 100, 100)(30, 10) == (0, 255, 0), "and on the frames after"


def test_a_pending_child_is_not_recorded(no_time_left) -> None:
    page = Box(width=Sizing.weight(), height=Sizing.weight(), background_color=(255, 0, 0, 255))
    container = Container(page)  # a container that never replays its child
    container.mount(_App())
    container.layout(100, 100)
    _frame(container, 150, 100)
    assert page._layout_pending

    assert _paint_on_white(container, 150, 100)(50, 50) == RED
    assert _paint_on_white(container, 150, 100)(50, 50) == RED

    assert page._replay_picture is None


def test_a_widget_added_below_a_pending_child_is_not_painted(no_time_left, caplog) -> None:
    first = _fixed()
    inner = Column([first], width=Sizing.weight(), height=Sizing.weight())
    column = Column([inner])
    column.mount(_App())
    column.layout(200, 100)

    late = _fixed()
    inner.add_child(late)
    _frame(column, 300, 100)
    assert inner._layout_pending and inner.layout_rect == (0, 0, 300, 100)
    with caplog.at_level(logging.WARNING):
        column.paint(None, 0, 0, 300, 100)

    assert first.painted == 1 and late.painted == 0
    assert caplog.records == [], "its rect comes with the next layout: nothing is reported"
    assert late.laid_out == [], "a paint lays nothing out"
    assert inner._layout_pending and inner.layout_rect == (0, 0, 300, 100), "the next frame still lays it out"


def test_a_scroll_viewport_below_a_pending_child_paints_its_last_layout(no_time_left) -> None:
    probe = _fixed()
    scroller = VerticalScrollable(Column([probe]), width=Sizing.weight(), height=Sizing.weight())
    column = Column([scroller])
    column.mount(_App())
    column.layout(200, 100)

    _frame(column, 300, 100)
    assert scroller._layout_pending
    column.paint(None, 0, 0, 300, 100)

    assert [at[2:] for at in probe.painted_at] == [(50, 20)]
    assert scroller._viewport.viewport_rect == (0, 0, 200, 100), "the viewport of its last layout"


def test_a_navigator_left_pending_paints_its_last_layout(no_time_left) -> None:
    screen = _fixed()
    navigator = Navigator(screen)
    deck = Deck([navigator])  # a page takes the whole deck, whatever its sizing
    deck.mount(_App())
    deck.layout(200, 100)

    _frame(deck, 300, 100)
    assert navigator._layout_pending
    deck.paint(None, 0, 0, 300, 100)

    assert [at[2:] for at in screen.painted_at] == [(200, 100)], "a screen takes the navigator's size"


def test_an_overlay_left_pending_paints_its_last_layout(no_time_left) -> None:
    probe = _fixed()
    overlay = Overlay()
    column = Column([overlay])
    column.mount(_App())
    overlay.show(probe, passthrough=True)
    column.layout(200, 100)

    _frame(column, 300, 100)
    assert overlay._layout_pending
    column.paint(None, 0, 0, 300, 100)

    assert [at[2:] for at in probe.painted_at] == [(50, 20)]


def test_a_pending_subtree_never_laid_out_is_not_hit(no_time_left, monkeypatch) -> None:
    # A painted box catches a hit on its own surface.
    fixed = _Probe(width=Sizing.fixed(50), height=Sizing.fixed(20), background_color=(200, 0, 0, 255))
    row = Row([fixed], width=Sizing.fixed(50), height=Sizing.fixed(20))
    column = Column([row])
    column.mount(_App())
    _frame(column, 200, 100)

    assert column.hit_test(10, 10) is not fixed, "nothing below it has a rect"
    _give_time(monkeypatch)
    _frame(column, 200, 100, root_pass=False)
    assert column.hit_test(10, 10) is fixed


def test_a_pending_subtree_is_hit_through_its_last_layout(no_time_left) -> None:
    fixed = _Probe(width=Sizing.fixed(50), height=Sizing.fixed(20), background_color=(200, 0, 0, 255))
    row = Row([fixed], width=Sizing.weight(), height=Sizing.fixed(20))
    column = Column([row])
    column.mount(_App())
    column.layout(200, 100)

    _frame(column, 300, 100)
    assert row._layout_pending

    assert column.hit_test(10, 10) is fixed, "the widget its last layout shows there"


# ---- Outside a frame ----------------------------------------------------------
def test_outside_a_frame_a_pass_leaves_nothing_pending(no_time_left) -> None:
    fixed = _fixed()
    column = Column([fixed])
    column.mount(_App())
    column.layout(200, 100)

    assert fixed.laid_out == [(50, 20)]
    assert not has_pending_layout()


def test_outside_a_frame_the_layout_finishes_what_a_frame_left_pending(no_time_left) -> None:
    inner = _fixed()
    row = Row([inner], width=Sizing.weight(), height=Sizing.fixed(20))
    column = Column([row], width=Sizing.fixed(200), height=Sizing.fixed(100))
    column.mount(_App())
    _frame(column, 200, 100)
    assert row._layout_pending

    layout_frame(column, 200, 100, root_pass=False)  # a headless render: no frame is under way
    assert inner.laid_out == [(50, 20)]
    assert not has_pending_layout()


# ---- The budget ---------------------------------------------------------------
def test_light_children_are_laid_out_within_the_limit() -> None:
    boxes = [_fixed() for _ in range(5)]
    column = Column(boxes)
    column.mount(_App())
    _frame(column, 200, 100)

    assert all(box.laid_out == [(50, 20)] for box in boxes)
    assert not has_pending_layout()


# ---- The pages of a Deck ------------------------------------------------------
def test_a_deck_lays_the_selected_page_out_first(monkeypatch) -> None:
    hidden = _Probe(width=Sizing.weight(), height=Sizing.weight())
    selected = _Probe(width=Sizing.weight(), height=Sizing.weight())
    deck = Deck([hidden, selected], index=1)
    deck.mount(_App())

    # The limit runs out after one page.
    clock = [0.0, 0.0]
    monkeypatch.setattr(layout_utils, "perf_counter", lambda: clock.pop(0) if clock else float("inf"))
    _frame(deck, 200, 100)
    assert selected.laid_out == [(200, 100)] and not selected._layout_pending
    assert hidden.laid_out == [] and hidden._layout_pending
    assert hidden.layout_rect == (0, 0, 200, 100), "the hidden page keeps the rect a later frame lays it out at"

    monkeypatch.setattr(layout_utils, "perf_counter", perf_counter)
    _frame(deck, 200, 100, root_pass=False)
    assert hidden.laid_out == [(200, 100)], "a switch shows a page that is ready"
    assert not has_pending_layout()
