"""A lazy container builds the items around the view while the loop is idle.

The layout pass builds only the items that entered the view. Idle time fills
a lead on each side: at rest a few items on both sides, while scrolling more
on the side the scroll heads for, and the items behind stay within the lead.
"""

from __future__ import annotations

from typing import List

import pytest

from nuiitivet.layout import lazy as lazy_module
from nuiitivet.layout.column import Column
from nuiitivet.layout.scrollable import VerticalScrollable
from nuiitivet.layout.uniform_flow import UniformFlow
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgeting import idle_work
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
def no_leftover_work():
    idle_work._tasks.clear()
    yield
    idle_work._tasks.clear()


def _column(log: _Log, count: int = 1000):
    column = Column.lazy(list(range(count)), log.builder, item_height=20)
    scroller = VerticalScrollable(column, width=200, height=100)
    scroller.mount(_App())
    scroller.layout(200, 100)
    return column, scroller


def _held(column) -> list:
    return [child.layout_rect for child in column._laid_out_children]


def test_the_pass_builds_the_view_and_idle_time_fills_both_sides_at_rest():
    log = _Log()
    column, scroller = _column(log)
    assert log.built == [0, 1, 2, 3, 4], "the pass built the five in view"
    assert has_idle_work(), "the lead is filled later"

    assert run_idle_work(1.0) is False, "the lead is filled in one wait"
    assert log.built == [0, 1, 2, 3, 4, 5, 6], "two ahead, none behind the first item"

    scroller.layout(200, 100)
    assert _held(column)[-1] == (0, 120, 60, 20), "the prefetched item is laid out at its slot"


def test_a_scroll_within_the_lead_builds_nothing_in_the_pass():
    log = _Log()
    column, scroller = _column(log)
    run_idle_work(1.0)
    log.built.clear()

    scroller._controller.scroll_to(20)
    scroller.layout(200, 100)
    assert log.built == [], "item 5 came into view already built"

    run_idle_work(1.0)
    assert log.built, "idle time rebuilt the lead ahead"


def test_the_lead_grows_with_the_scroll_speed_in_its_direction():
    log = _Log()
    column, scroller = _column(log)
    run_idle_work(1.0)
    log.built.clear()

    scroller._controller.scroll_to(100)  # five items per step
    scroller.layout(200, 100)
    run_idle_work(1.0)

    ahead = [i for i in log.built if i >= 10]
    behind = [i for i in log.built if i < 5]
    assert lazy_module.LEAD_STEPS * 5 > 5, "the lead the speed asks for exceeds one view"
    assert len(ahead) == 5, "one view's worth ahead: the lead's cap"
    assert behind == [], "nothing new behind while scrolling down"
    assert column._lazy._held == (0, 15), "the five behind kept within the lead"


def test_a_reversal_finds_the_items_behind_still_built():
    log = _Log()
    column, scroller = _column(log)
    for offset in (100, 200, 300):
        scroller._controller.scroll_to(offset)
        scroller.layout(200, 100)
        run_idle_work(1.0)
    log.built.clear()

    scroller._controller.scroll_to(260)  # two items back
    scroller.layout(200, 100)
    assert log.built == [], "the items behind were kept"


def test_a_deadline_stops_the_prefetch_and_keeps_the_task():
    log = _Log()
    column, scroller = _column(log)
    scroller._controller.scroll_to(200)
    scroller.layout(200, 100)
    log.built.clear()

    assert run_idle_work(0.0) is True, "no time: nothing built, the task stays"
    assert log.built == []
    assert has_idle_work()


def test_detach_cancels_the_prefetch():
    log = _Log()
    column, scroller = _column(log)
    assert has_idle_work()

    scroller.unmount()
    assert not has_idle_work()


def test_uniform_flow_prefetches_whole_rows():
    log = _Log()
    flow = UniformFlow.lazy(list(range(1000)), log.builder, columns=4)
    scroller = VerticalScrollable(flow, width=240, height=100)
    scroller.mount(_App())
    scroller.layout(240, 100)
    assert log.built == list(range(20)), "five rows of four, 20 px each from the sample"

    run_idle_work(1.0)
    assert log.built == list(range(28)), "two rows ahead"
