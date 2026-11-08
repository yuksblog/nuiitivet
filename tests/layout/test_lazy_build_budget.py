"""Inside a frame a lazy container's pass stops building at a share of the frame.

The rest of the view holds placeholders, which idle time replaces, the view
first. Outside a frame, where no loop runs, a pass builds every item in view.
"""

from __future__ import annotations

from time import perf_counter
from typing import List

import pytest

from nuiitivet.layout import lazy as lazy_module
from nuiitivet.layout.column import Column
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
    frame_clock._started_at = None
    yield
    idle_work._tasks.clear()
    frame_clock._started_at = None


@pytest.fixture
def no_time_to_build(monkeypatch):
    """The budget is spent before the first item: a pass inside a frame builds nothing."""
    monkeypatch.setattr(lazy_module, "BUILD_SHARE", 0.0)


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
    """One frame of the loop: a scroll, if any, then the layout pass."""
    if offset is not None:
        scroller._controller.scroll_to(offset)
    begin_frame(perf_counter())
    try:
        scroller.layout(200, 100)
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
    assert has_idle_work(), "idle time fills them"


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


def test_idle_time_fills_the_view_first_and_asks_for_a_layout(no_time_to_build):
    log = _Log()
    column, scroller = _column(log)
    _frame(scroller, 200)
    log.built.clear()

    assert run_idle_work(1.0) is False
    assert log.built[:5] == [10, 11, 12, 13, 14], "the view, in the scroll's direction, before the lead"
    assert column._lazy.provider.placeholder_indices() == []
    assert column.needs_layout, "the built items need a frame to show"

    scroller.layout(200, 100)
    assert not any(isinstance(child, Spacer) for child in column._laid_out_children)


def test_light_rows_build_within_the_budget():
    log = _Log()
    column, scroller = _column(log, in_a_frame=True)
    for offset in (100, 200, 300):
        _frame(scroller, offset)
        assert _placeholders_in_view(column) == [], "five boxes take far less than half a frame"


def test_a_fling_that_slows_to_a_stop_leaves_no_placeholder(no_time_to_build):
    log = _Log()
    column, scroller = _column(log)
    for offset in (100, 200, 300, 380, 440, 480, 500):
        _frame(scroller, offset)
    assert column._lazy.provider.placeholder_indices(), "the frames left placeholders behind"

    assert run_idle_work(1.0) is False
    assert column._lazy.provider.placeholder_indices() == [], "in view and in the kept range"
    scroller.layout(200, 100)
    assert not any(isinstance(child, Spacer) for child in column._laid_out_children)
    assert not has_idle_work()
