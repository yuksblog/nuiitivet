"""Inside a frame a lazy container's pass stops building at a share of the frame.

The rest of the view holds placeholders and leaves the container pending: the
next frame lays it out again and builds on. Idle time may build them sooner,
the view first. Outside a frame, where no loop runs, a pass builds every item
in view.
"""

from __future__ import annotations

from time import perf_counter
from typing import List

import pytest

from nuiitivet.layout import layout_utils
from nuiitivet.layout import lazy as lazy_module
from nuiitivet.layout.column import Column
from nuiitivet.layout.layout_utils import has_pending_layout, layout_frame
from nuiitivet.layout.scrollable import VerticalScrollable
from nuiitivet.layout.spacer import Spacer
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgeting import frame_clock, idle_work
from nuiitivet.widgeting.frame_clock import begin_frame, end_frame
from nuiitivet.widgeting.idle_work import has_idle_work, run_idle_work
from nuiitivet.widgets.box import Box


class _App:
    def __init__(self) -> None:
        self._pointer_capture_manager = PointerCaptureManager()

    def invalidate(self, immediate: bool = False) -> None:
        del immediate


class _Log:
    def __init__(self) -> None:
        self.built: List[int] = []

    def builder(self, item, index):
        self.built.append(index)
        return Box(width=Sizing.fixed(60), height=Sizing.fixed(20))


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
def no_time_to_build(monkeypatch):
    """The budget is spent before the first item: a pass inside a frame builds nothing."""
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.0)


class _Clock:
    """A clock each build moves on by a fixed step: a frame's share holds a known count of builds."""

    def __init__(self, step: float) -> None:
        self.now = 0.0
        self.step = step

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def three_builds_a_frame(monkeypatch):
    """Half of a 60 Hz frame is 8.3 ms; a build takes 3 ms, so a frame's layout builds three items."""
    clock = _Clock(0.003)
    monkeypatch.setattr(layout_utils, "perf_counter", clock)
    monkeypatch.setattr(lazy_module, "perf_counter", clock)
    monkeypatch.setattr(frame_clock, "_interval", 1 / 60)
    return clock


class _SlowLog(_Log):
    def __init__(self, clock: _Clock) -> None:
        super().__init__()
        self.clock = clock

    def builder(self, item, index):
        self.clock.now += self.clock.step
        return super().builder(item, index)


def _column(log: _Log, count: int = 1000, *, in_a_frame: bool = False):
    column = Column.lazy(list(range(count)), log.builder, item_height=20)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    if in_a_frame:
        _frame(scroller)
    else:
        scroller.layout(200, 100)
    return column, scroller


def _frame(scroller, offset: float | None = None) -> None:
    """One frame of the loop: a scroll, if any, then the layout; the root's pass only after a scroll."""
    if offset is not None:
        scroller._controller.scroll_to(offset)
    begin_frame(perf_counter())
    try:
        layout_frame(scroller, 200, 100, root_pass=offset is not None or scroller.layout_rect is None)
    finally:
        end_frame()


def _placeholders_in_view(column) -> List[int]:
    lazy = column._lazy
    first, stop = lazy._visible
    return [index for index in lazy.provider.placeholder_indices() if first <= index < stop]


def test_a_pass_past_the_budget_holds_the_view_with_placeholders(no_time_to_build):
    log = _Log()
    column, scroller = _column(log)
    assert log.built == [0, 1, 2, 3, 4], "outside a frame the layout built its view"

    _frame(scroller, 200)
    assert log.built == [0, 1, 2, 3, 4], "inside the frame the pass built nothing"
    assert _placeholders_in_view(column) == [10, 11, 12, 13, 14]
    placeholders = [child for child in column._laid_out_children if isinstance(child, Spacer)]
    assert [child.layout_rect for child in placeholders] == [(0, 20 * i, 0, 20) for i in range(10, 15)], (
        "each placeholder sits at its item's slot and takes no width"
    )
    assert column._layout_pending, "the next frame lays the container out again"
    assert has_pending_layout()


def test_the_first_layout_inside_a_frame_keeps_the_budget_too(no_time_to_build):
    log = _Log()
    column, _scroller = _column(log, in_a_frame=True)
    assert log.built == []
    assert _placeholders_in_view(column) == [0, 1, 2, 3, 4]


def test_outside_a_frame_a_pass_builds_everything(no_time_to_build):
    log = _Log()
    column, scroller = _column(log)
    _frame(scroller, 200)
    log.built.clear()

    scroller._controller.scroll_to(300)
    scroller.layout(200, 100)  # no frame under way: a test, a headless render
    assert log.built == [15, 16, 17, 18, 19]
    assert _placeholders_in_view(column) == []
    assert not column._layout_pending, "the pass the viewport ran itself ended the pending state"


def test_frames_that_follow_fill_the_view_with_no_idle_time(three_builds_a_frame):
    log = _SlowLog(three_builds_a_frame)
    column, scroller = _column(log)
    log.built.clear()

    _frame(scroller, 200)  # a draw is pending at every frame: the loop runs no idle work
    assert log.built == [10, 11, 12]
    assert _placeholders_in_view(column) == [13, 14]
    assert has_pending_layout()

    _frame(scroller)
    assert log.built == [10, 11, 12, 13, 14], "the next frame built on, in the scroll's direction"
    assert _placeholders_in_view(column) == []
    assert not any(isinstance(child, Spacer) for child in column._laid_out_children)
    assert not has_pending_layout(), "a filled view asks for no more frames"


def test_idle_time_fills_the_view_first_and_the_next_frame_shows_it(no_time_to_build, monkeypatch):
    log = _Log()
    column, scroller = _column(log)
    _frame(scroller, 200)
    log.built.clear()

    assert run_idle_work(1.0) is False
    assert log.built[:5] == [10, 11, 12, 13, 14], "the view, in the scroll's direction, before the lead"
    assert column._lazy.provider.placeholder_indices() == []
    assert has_pending_layout(), "the frame that shows them was asked for already"

    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.5)
    _frame(scroller)
    assert not any(isinstance(child, Spacer) for child in column._laid_out_children)
    assert not has_pending_layout()


def test_a_placeholder_that_cannot_be_built_asks_for_no_frame(three_builds_a_frame, monkeypatch):
    log = _SlowLog(three_builds_a_frame)
    column, scroller = _column(log)
    _frame(scroller, 200)
    assert has_pending_layout()

    monkeypatch.setattr(column._lazy.provider, "build_item", lambda index: None)
    _frame(scroller)
    assert _placeholders_in_view(column) == [13, 14]
    assert not has_pending_layout()


def test_an_item_idle_time_builds_in_view_asks_for_a_layout_without_pending(three_builds_a_frame, monkeypatch):
    log = _SlowLog(three_builds_a_frame)
    column, scroller = _column(log)
    _frame(scroller, 200)
    provider = column._lazy.provider
    build_item = provider.build_item
    monkeypatch.setattr(provider, "build_item", lambda index: None)
    _frame(scroller)
    assert not column._layout_pending and not column.needs_layout
    monkeypatch.setattr(provider, "build_item", build_item)

    run_idle_work(1.0)
    assert _placeholders_in_view(column) == []
    assert column.needs_layout, "replacing the placeholders dirtied the container"


def test_a_container_laid_out_again_while_pending_waits_in_the_queue_once(no_time_to_build):
    log = _Log()
    column, scroller = _column(log)
    for offset in (200, 220, 240):
        _frame(scroller, offset)  # the root's pass reaches the pending container each time
    assert column._layout_pending
    assert [ref() for ref in layout_utils._pending].count(column) == 1


def test_light_rows_build_within_the_budget():
    log = _Log()
    column, scroller = _column(log, in_a_frame=True)
    for offset in (100, 200, 300):
        _frame(scroller, offset)
        assert _placeholders_in_view(column) == [], "five boxes take far less than half a frame"


def test_a_fling_that_slows_to_a_stop_leaves_no_placeholder(no_time_to_build, monkeypatch):
    log = _Log()
    column, scroller = _column(log)
    for offset in (100, 200, 300, 380, 440, 480, 500):
        _frame(scroller, offset)
    assert column._lazy.provider.placeholder_indices(), "the frames left placeholders behind"

    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.5)
    _frame(scroller)
    assert _placeholders_in_view(column) == [], "the frame after the fling filled the view"
    assert not has_pending_layout()
    assert run_idle_work(1.0) is False
    assert column._lazy.provider.placeholder_indices() == [], "idle time filled the kept range"
    assert not has_idle_work()
