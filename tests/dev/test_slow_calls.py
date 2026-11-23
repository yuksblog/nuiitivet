"""Tests for the slow-call report: each kind of app call, the frame start, the once-per-function rule."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from nuiitivet._interaction.action import settle
from nuiitivet.common import logging_once
from nuiitivet.common.call_probe import call_probe, probed_steps, set_call_probe
from nuiitivet.common.logging_once import set_log_once_enabled
from nuiitivet.dev.runtime_capture import RuntimeLogCapture
from nuiitivet.dev.runtime_journal import RuntimeJournal
from nuiitivet.dev.slow_calls import SlowCallReporter
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.observable import State
from nuiitivet.observable.runtime import _ProbedCallback, _ProbedClock, _ThreadClock, get_clock, set_clock
from nuiitivet.rendering.size import Size
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.runtime.window import Window
from nuiitivet.testing.clock import HarnessClock
from nuiitivet.widgeting.callbacks import invoke_event_handler
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks, invoke_size_callback
from nuiitivet.widgets.raster_surface import RasterSurface

_LIMIT = 0.008
_SLOW = 0.020
_FAST = 0.005

# As the reporter prints it: relative to the directory the tests run from.
_THIS_FILE = os.path.relpath(__file__)


class _Timer:
    """A clock the test moves: a function is slow by advancing it."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def spend(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def timer() -> _Timer:
    return _Timer()


def _pass_the_first_frame(slow_calls: SlowCallReporter) -> None:
    """The reporter times nothing before the app's first frame starts."""
    slow_calls.begin_frame_start()
    slow_calls.end_frame_start()


@pytest.fixture
def reporter(timer: _Timer) -> Iterator[SlowCallReporter]:
    set_log_once_enabled(True)
    slow_calls = SlowCallReporter(limit=_LIMIT, timer=timer)
    slow_calls.install()
    _pass_the_first_frame(slow_calls)
    try:
        yield slow_calls
    finally:
        slow_calls.shutdown()
        set_log_once_enabled(True)
        logging_once._clear_log_once_keys_for_tests()


def _reports(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == "nuiitivet.dev.slow_calls"]


# --- Each kind of call ------------------------------------------------------------


def test_a_slow_event_handler_is_reported_with_its_name_and_duration(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def on_save() -> None:
        timer.spend(_SLOW)

    with caplog.at_level(logging.WARNING):
        invoke_event_handler(on_save, error_key="click_callback", error_msg="Click callback raised")

    (report,) = _reports(caplog)
    assert report.startswith("Slow event handler on the UI thread: ")
    assert f"on_save ({_THIS_FILE}:" in report
    assert "took 20.0 ms; the limit is 8.0 ms." in report


def test_a_slow_size_change_callback_is_reported(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def on_size_changed(_size: Size) -> None:
        timer.spend(_SLOW)

    with caplog.at_level(logging.WARNING):
        invoke_size_callback(on_size_changed, Size(10, 10), owner_name="Box")

    (report,) = _reports(caplog)
    assert report.startswith("Slow size-change callback on the UI thread: ")
    assert "on_size_changed" in report


def test_a_slow_clock_callback_is_reported(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def tick(_dt: float) -> None:
        timer.spend(_SLOW)

    previous = get_clock()
    harness = HarnessClock()
    set_clock(harness)
    try:
        assert isinstance(get_clock(), _ProbedClock)
        get_clock().schedule_once(tick, 0)
        with caplog.at_level(logging.WARNING):
            harness.pump()
    finally:
        set_clock(previous)

    (report,) = _reports(caplog)
    assert report.startswith("Slow clock callback on the UI thread: ")
    assert "tick" in report


def test_a_slow_draw_function_is_reported(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def draw_chart(_value: int, _width_px: int, _height_px: int) -> None:
        timer.spend(_SLOW)

    surface = RasterSurface.draw(State(0), draw_chart, width=20, height=10)
    surface.layout(20, 10)
    with caplog.at_level(logging.WARNING):
        flush_size_change_callbacks()

    (report,) = _reports(caplog)
    assert report.startswith("Slow draw function on the UI thread: ")
    assert "draw_chart" in report


def test_a_slow_build_is_reported(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    class Screen(ComposableWidget):
        def build(self) -> Widget:
            timer.spend(_SLOW)
            return Container()

    with caplog.at_level(logging.WARNING):
        Screen().evaluate_build()

    (report,) = _reports(caplog)
    assert report.startswith("Slow build on the UI thread: ")
    assert "Screen.build" in report


def test_a_slow_scope_is_reported_under_its_factory(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def rows() -> Widget:
        timer.spend(_SLOW)
        return Container()

    class Screen(ComposableWidget):
        def build(self) -> Widget:
            return self.render_scope("rows", rows)

    with caplog.at_level(logging.WARNING):
        Screen().evaluate_build()

    # The scope is built inside ``Screen.build``, which took no time of its own.
    (report,) = _reports(caplog)
    assert f"rows ({_THIS_FILE}:" in report


# --- An awaited function ----------------------------------------------------------


async def _drain() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_an_async_handler_that_blocks_is_reported(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    async def on_save() -> None:
        timer.spend(_SLOW)

    with caplog.at_level(logging.WARNING):
        invoke_event_handler(on_save, error_key="click_callback", error_msg="Click callback raised")
        await _drain()

    (report,) = _reports(caplog)
    assert report.startswith("Slow event handler on the UI thread: ")
    assert f"on_save ({_THIS_FILE}:" in report


async def test_an_async_handler_is_timed_after_its_await_too(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    async def on_save() -> None:
        await asyncio.sleep(0)
        timer.spend(_SLOW)

    with caplog.at_level(logging.WARNING):
        invoke_event_handler(on_save, error_key="click_callback", error_msg="Click callback raised")
        await _drain()

    (report,) = _reports(caplog)
    assert "on_save" in report


async def test_the_time_an_async_handler_waits_is_not_counted(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    async def on_save() -> None:
        await asyncio.sleep(0)

    with caplog.at_level(logging.WARNING):
        invoke_event_handler(on_save, error_key="click_callback", error_msg="Click callback raised")
        timer.spend(_SLOW)
        await _drain()

    assert _reports(caplog) == []


async def test_a_coroutine_draw_function_that_blocks_is_reported(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    async def draw_chart(_value: int, _width_px: int, _height_px: int) -> None:
        timer.spend(_SLOW)

    surface = RasterSurface.draw(State(0), draw_chart, width=20, height=10)
    surface.layout(20, 10)
    with caplog.at_level(logging.WARNING):
        flush_size_change_callbacks()
        await _drain()

    (report,) = _reports(caplog)
    assert report.startswith("Slow draw function on the UI thread: ")
    assert "draw_chart" in report


async def test_probed_steps_hand_through_the_result_the_exception_and_the_cancellation(
    reporter: SlowCallReporter,
) -> None:
    async def answer() -> int:
        await asyncio.sleep(0)
        return 42

    async def fail() -> None:
        await asyncio.sleep(0)
        raise ValueError("boom")

    cleaned: list[str] = []

    async def wait() -> None:
        try:
            await asyncio.sleep(10)
        finally:
            cleaned.append("done")

    assert await probed_steps("event handler", answer, answer()) == 42
    with pytest.raises(ValueError, match="boom"):
        await probed_steps("event handler", fail, fail())

    task = asyncio.ensure_future(probed_steps("event handler", wait, wait()))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cleaned == ["done"]


async def test_probed_steps_are_the_awaitable_itself_with_no_probe() -> None:
    async def answer() -> int:
        return 42

    coro = answer()
    assert probed_steps("event handler", answer, coro) is coro
    assert await coro == 42


# --- A call inside a call ---------------------------------------------------------


def test_a_call_is_not_blamed_for_the_slow_call_inside_it(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def build_rows() -> None:
        timer.spend(_SLOW)

    def on_click() -> None:
        reporter.call("build", build_rows)

    with caplog.at_level(logging.WARNING):
        reporter.call("event handler", on_click)

    (report,) = _reports(caplog)
    assert "build_rows" in report


def test_a_call_slow_besides_the_slow_call_inside_it_is_reported_with_its_own_time(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def build_rows() -> None:
        timer.spend(_SLOW)

    def on_click() -> None:
        timer.spend(0.010)
        reporter.call("build", build_rows)

    with caplog.at_level(logging.WARNING):
        reporter.call("event handler", on_click)

    rows, click = _reports(caplog)
    assert "build_rows" in rows and "took 20.0 ms" in rows
    assert "on_click" in click and "took 10.0 ms" in click


def test_a_call_made_slow_by_many_quick_calls_inside_it_is_reported(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def on_click() -> None:
        for _ in range(3):
            reporter.call("build", lambda: timer.spend(_FAST))

    with caplog.at_level(logging.WARNING):
        reporter.call("event handler", on_click)

    (report,) = _reports(caplog)
    assert "on_click" in report and "took 15.0 ms" in report


def test_a_slow_call_two_levels_down_is_taken_out_of_every_call_around_it(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def inner() -> None:
        timer.spend(_SLOW)

    def middle() -> None:
        reporter.call("build", inner)

    def outer() -> None:
        reporter.call("build", middle)

    with caplog.at_level(logging.WARNING):
        reporter.call("event handler", outer)

    (report,) = _reports(caplog)
    assert "inner" in report


# --- What is not reported ---------------------------------------------------------


def test_a_call_under_the_limit_is_not_reported(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        invoke_event_handler(lambda: timer.spend(_FAST), error_key="click_callback", error_msg="Click callback raised")

    assert _reports(caplog) == []


def test_the_builds_that_mount_the_app_are_not_timed(timer: _Timer, caplog: pytest.LogCaptureFixture) -> None:
    slow_calls = SlowCallReporter(limit=_LIMIT, timer=timer)

    def build() -> None:
        timer.spend(_SLOW)

    with caplog.at_level(logging.WARNING):
        slow_calls.call("build", build)
        assert _reports(caplog) == []

        # The first frame starts: from here on the same build is reported.
        slow_calls.begin_frame_start()
        slow_calls.end_frame_start()
        slow_calls.call("build", build)

    assert len(_reports(caplog)) == 1


def test_nothing_is_timed_while_paused(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        with reporter.paused():
            reporter.call("build", lambda: timer.spend(_SLOW))
        assert _reports(caplog) == []

        reporter.call("build", lambda: timer.spend(_SLOW))

    assert len(_reports(caplog)) == 1


def test_a_call_off_the_ui_thread_is_not_timed(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def work() -> None:
        reporter.call("event handler", lambda: timer.spend(_SLOW))

    with caplog.at_level(logging.WARNING):
        thread = threading.Thread(target=work)
        thread.start()
        thread.join()

    assert _reports(caplog) == []


def test_a_handler_that_raises_is_still_timed_and_still_contained(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def on_click() -> None:
        timer.spend(_SLOW)
        raise ValueError("boom")

    with caplog.at_level(logging.WARNING):
        invoke_event_handler(on_click, error_key="click_callback", error_msg="Click callback raised")

    assert len(_reports(caplog)) == 1
    assert any(record.exc_info for record in caplog.records)


# --- Once per function ------------------------------------------------------------


def test_a_function_is_reported_once_until_reset(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def on_click() -> None:
        timer.spend(_SLOW)

    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            invoke_event_handler(on_click, error_key="click_callback", error_msg="Click callback raised")
        assert len(_reports(caplog)) == 1

        reporter.reset()
        invoke_event_handler(on_click, error_key="click_callback", error_msg="Click callback raised")
        assert len(_reports(caplog)) == 2


def test_the_verbose_runtime_log_reports_every_slow_call(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def on_click() -> None:
        timer.spend(_SLOW)

    set_log_once_enabled(False)
    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            invoke_event_handler(on_click, error_key="click_callback", error_msg="Click callback raised")

    assert len(_reports(caplog)) == 3


# --- The frame start ---------------------------------------------------------------


def test_a_frame_start_over_the_limit_in_total_names_its_slowest_calls(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def draw_a() -> None:
        timer.spend(_FAST)

    def draw_b() -> None:
        timer.spend(_FAST + 0.001)

    with caplog.at_level(logging.WARNING):
        reporter.begin_frame_start()
        reporter.call("draw function", draw_a)
        reporter.call("draw function", draw_b)
        reporter.end_frame_start()

    (report,) = _reports(caplog)
    assert report.startswith("Slow frame start on the UI thread: 2 calls took 11.0 ms in total; the limit is 8.0 ms.")
    assert report.index("draw_b") < report.index("draw_a")


def test_a_frame_start_with_a_slow_call_reports_the_call_only(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        reporter.begin_frame_start()
        reporter.call("draw function", lambda: timer.spend(_SLOW))
        reporter.call("draw function", lambda: timer.spend(_FAST))
        reporter.end_frame_start()

    (report,) = _reports(caplog)
    assert report.startswith("Slow draw function on the UI thread: ")


def test_a_frame_start_counts_a_nested_call_once(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def inner() -> None:
        timer.spend(_FAST)

    def outer() -> None:
        reporter.call("build", inner)

    with caplog.at_level(logging.WARNING):
        reporter.begin_frame_start()
        reporter.call("build", outer)
        reporter.end_frame_start()

    assert _reports(caplog) == []


def test_calls_outside_a_frame_start_are_not_added_up(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        reporter.call("event handler", lambda: timer.spend(_FAST))
        reporter.call("event handler", lambda: timer.spend(_FAST))
        reporter.end_frame_start()

    assert _reports(caplog) == []


def test_a_frame_start_begun_inside_a_call_still_adds_up_its_calls(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def pump_a_frame() -> None:
        reporter.begin_frame_start()
        reporter.call("draw function", lambda: timer.spend(_FAST))
        reporter.call("draw function", lambda: timer.spend(_FAST))
        reporter.end_frame_start()

    with caplog.at_level(logging.WARNING):
        reporter.call("event handler", pump_a_frame)

    assert any(report.startswith("Slow frame start on the UI thread: 2 calls") for report in _reports(caplog))


def test_settle_tells_the_probe_of_each_of_its_passes() -> None:
    steps: list[str] = []
    probe = SimpleNamespace(
        begin_frame_start=lambda: steps.append("begin"),
        end_frame_start=lambda: steps.append("end"),
        call=lambda _kind, fn, *args: fn(*args),
    )
    root = Column([])
    app: Any = SimpleNamespace(
        width=200,
        height=100,
        root=root,
        invalidate=lambda immediate=False: None,
        _pointer_capture_manager=PointerCaptureManager(),
    )
    root.mount(app)
    set_call_probe(probe)  # type: ignore[arg-type]
    try:
        settle(app)
    finally:
        set_call_probe(None)
        root.unmount()

    assert steps == ["begin", "end", "begin", "end"]


def test_settle_reports_the_frame_start_it_stands_in_for(
    reporter: SlowCallReporter, timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    def draw_a(_value: int, _width_px: int, _height_px: int) -> None:
        timer.spend(_FAST)

    def draw_b(_value: int, _width_px: int, _height_px: int) -> None:
        timer.spend(_FAST)

    root = Column(
        [
            RasterSurface.draw(State(0), draw_a, width=20, height=10),
            RasterSurface.draw(State(0), draw_b, width=20, height=10),
        ]
    )
    app: Any = SimpleNamespace(
        width=200,
        height=100,
        root=root,
        invalidate=lambda immediate=False: None,
        _pointer_capture_manager=PointerCaptureManager(),
    )
    root.mount(app)
    try:
        with caplog.at_level(logging.WARNING):
            settle(app)
    finally:
        root.unmount()

    (report,) = _reports(caplog)
    assert report.startswith("Slow frame start on the UI thread: 2 calls took 10.0 ms in total")


def test_the_window_brackets_its_frame_queues() -> None:
    steps: list[str] = []
    probe = SimpleNamespace(
        begin_frame_start=lambda: steps.append("begin"),
        end_frame_start=lambda: steps.append("end"),
    )
    window: Any = SimpleNamespace(_run_frame_queues=lambda: steps.append("queues"))

    set_call_probe(probe)  # type: ignore[arg-type]
    try:
        Window._flush_frame_queues(window)
    finally:
        set_call_probe(None)

    assert steps == ["begin", "queues", "end"]


# --- The runtime log and the plain run --------------------------------------------


def test_the_runtime_log_holds_the_report(reporter: SlowCallReporter, timer: _Timer) -> None:
    def on_save() -> None:
        timer.spend(_SLOW)

    journal = RuntimeJournal()
    capture = RuntimeLogCapture(journal)
    capture.install()
    try:
        invoke_event_handler(on_save, error_key="click_callback", error_msg="Click callback raised")
    finally:
        capture.shutdown()

    (event,) = journal.recent()
    assert event.level == "WARNING"
    assert event.thread == threading.current_thread().name
    assert "on_save" in event.message
    assert "20.0 ms" in event.message


def test_a_plain_run_has_no_probe_and_an_unwrapped_clock() -> None:
    assert call_probe() is None

    previous = get_clock()
    harness = HarnessClock()
    set_clock(harness)
    try:
        assert get_clock() is harness
    finally:
        set_clock(previous)


def test_install_wraps_the_clock_in_place_and_shutdown_puts_it_back(timer: _Timer) -> None:
    installed = get_clock()
    slow_calls = SlowCallReporter(limit=_LIMIT, timer=timer)

    slow_calls.install()
    assert call_probe() is slow_calls
    wrapper = get_clock()
    assert isinstance(wrapper, _ProbedClock) and wrapper.inner is installed

    slow_calls.shutdown()
    assert call_probe() is None
    assert get_clock() is installed


def test_a_callback_armed_after_install_is_timed_whichever_came_first(
    timer: _Timer, caplog: pytest.LogCaptureFixture
) -> None:
    # The clock was installed before the reporter, as a backend may do.
    previous = get_clock()
    harness = HarnessClock()
    set_clock(harness)
    slow_calls = SlowCallReporter(limit=_LIMIT, timer=timer)
    slow_calls.install()
    _pass_the_first_frame(slow_calls)
    try:
        get_clock().schedule_once(lambda _dt: timer.spend(_SLOW), 0)
        with caplog.at_level(logging.WARNING):
            harness.pump()
    finally:
        slow_calls.shutdown()
        set_clock(previous)

    (report,) = _reports(caplog)
    assert report.startswith("Slow clock callback on the UI thread: ")


def test_a_callback_handed_over_from_a_probed_clock_is_wrapped_once() -> None:
    def tick(_dt: float) -> None:
        pass

    armed: list[Any] = []
    inner: Any = SimpleNamespace(schedule_once=lambda fn, _delay: armed.append(fn))

    _ProbedClock(inner).schedule_once(_ProbedCallback(tick), 0)

    assert armed[0].fn is tick


def test_callbacks_armed_on_the_fallback_clock_still_reach_the_ui_clock(timer: _Timer) -> None:
    def before(_dt: float) -> None:
        pass

    def after(_dt: float) -> None:
        pass

    previous = get_clock()
    fallback = _ThreadClock()
    set_clock(fallback)
    fallback.schedule_once(before, 60.0)
    slow_calls = SlowCallReporter(limit=_LIMIT, timer=timer)
    slow_calls.install()
    harness = HarnessClock()
    try:
        get_clock().schedule_once(after, 60.0)
        set_clock(harness)
        assert fallback.pending_count() == 0
        # Each is wrapped once, and the plain function still cancels it.
        get_clock().unschedule(before)
        harness.unschedule(after)
        assert harness.cancel_all() == []
    finally:
        slow_calls.shutdown()
        fallback.cancel_all()
        harness.cancel_all()
        set_clock(previous)


def test_the_limit_is_half_a_frame(timer: _Timer, caplog: pytest.LogCaptureFixture) -> None:
    slow_calls = SlowCallReporter(timer=timer)
    _pass_the_first_frame(slow_calls)
    with caplog.at_level(logging.WARNING):
        slow_calls.call("event handler", lambda: timer.spend(1.0 / 60.0 * 0.4))
        assert _reports(caplog) == []
        slow_calls.call("event handler", lambda: timer.spend(1.0 / 60.0 * 0.6))

    (report,) = _reports(caplog)
    assert "the limit is 8.3 ms." in report


# --- The probed clock --------------------------------------------------------------


def test_unschedule_cancels_what_the_probed_clock_armed(reporter: SlowCallReporter) -> None:
    fired: list[float] = []

    class Owner:
        def tick(self, dt: float) -> None:
            fired.append(dt)

    owner = Owner()
    previous = get_clock()
    harness = HarnessClock()
    set_clock(harness)
    try:
        clock = get_clock()
        clock.schedule_once(owner.tick, 0)
        clock.schedule_interval(owner.tick, 0.01)
        clock.unschedule(owner.tick)
        harness.pump()
    finally:
        set_clock(previous)

    assert fired == []


def test_the_wrapped_clock_cancels_what_the_probed_clock_armed(reporter: SlowCallReporter) -> None:
    fired: list[float] = []

    class Owner:
        def tick(self, dt: float) -> None:
            fired.append(dt)

    owner = Owner()
    previous = get_clock()
    harness = HarnessClock()
    set_clock(harness)
    try:
        get_clock().schedule_once(owner.tick, 0)
        harness.unschedule(owner.tick)
        harness.pump()
    finally:
        set_clock(previous)

    assert fired == []
