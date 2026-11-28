"""The RasterSurface asks for pixels at its device size, at the next frame, and paints them."""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import MagicMock

import pytest

import nuiitivet.widgets.raster_surface as raster_mod
from nuiitivet.layout.column import Column
from nuiitivet.observable import State, runtime
from nuiitivet.testing import AppHarness
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks
from nuiitivet.widgets.raster_surface import RasterSurface

_TIMEOUT = 5.0


class _FakeImage:
    def __init__(self, width: int, height: int) -> None:
        self.size = (width, height)


@pytest.fixture
def fake_skia(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int]]:
    """Builds no real image: records the size each raster was made at."""
    made: list[tuple[int, int]] = []

    def make_raster_image(pixels: object, width: int, height: int) -> _FakeImage:
        if memoryview(pixels).nbytes != width * height * 4:  # type: ignore[arg-type]
            raise ValueError("wrong size")
        made.append((width, height))
        return _FakeImage(width, height)

    monkeypatch.setattr(raster_mod, "make_raster_image", make_raster_image)
    monkeypatch.setattr(raster_mod, "make_rect", lambda x, y, w, h: (x, y, w, h))
    monkeypatch.setattr(raster_mod, "_linear_sampling", lambda: ())
    return made


def _on_display(monkeypatch: pytest.MonkeyPatch, ratio: float) -> None:
    monkeypatch.setattr(raster_mod, "find_window", lambda _widget: SimpleNamespace(pixel_ratio=ratio))


def _pixels(width: int, height: int) -> bytes:
    return bytes(width * height * 4)


class _Drawn(RasterSurface):
    """A surface that draws itself, as a widget author writes one."""

    def __init__(self, draw: Callable[[int, int], Any], **layout: Any) -> None:
        super().__init__(**layout)
        self._draw_fn = draw

    def draw_pixels(self, width_px: int, height_px: int) -> Any:
        return self._draw_fn(width_px, height_px)


def _painted(surface: RasterSurface, width: int, height: int) -> Any:
    """The image the surface paints into a rect of that size, or ``None``."""
    canvas = MagicMock()
    surface.paint(canvas, 0, 0, width, height)
    if not canvas.drawImageRect.called:
        return None
    return canvas.drawImageRect.call_args[0][0]


# --- The size asked for, and when ------------------------------------------------


def test_draw_is_asked_for_the_content_rect_in_device_pixels(
    fake_skia: list[tuple[int, int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _on_display(monkeypatch, 2.0)
    asked: list[tuple[int, int]] = []

    def draw(_value: int, w: int, h: int) -> bytes:
        asked.append((w, h))
        return _pixels(w, h)

    surface = RasterSurface.draw(State(0), draw, width=220, height=120, padding=10)
    surface.layout(220, 120)

    # Layout only queues; the pixels are made at the next frame start.
    assert asked == []
    flush_size_change_callbacks()
    assert asked == [(400, 200)]
    assert fake_skia == [(400, 200)]
    assert surface.pixel_ratio == 2.0


def test_a_layout_at_the_same_size_asks_nothing(
    fake_skia: list[tuple[int, int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _on_display(monkeypatch, 1.0)
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = _Drawn(draw, width=100, height=50)

    surface.layout(100, 50)
    flush_size_change_callbacks()
    surface.layout(100, 50)
    flush_size_change_callbacks()

    assert draw.call_count == 1


def test_a_resize_asks_again_and_the_old_raster_is_stretched_meanwhile(
    fake_skia: list[tuple[int, int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _on_display(monkeypatch, 1.0)
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = _Drawn(draw, width="wt", height="wt")
    surface.layout(100, 50)
    flush_size_change_callbacks()

    surface.layout(300, 150)
    canvas = MagicMock()
    surface.paint(canvas, 0, 0, 300, 150)

    # The frame of the resize paints the 100x50 raster over the new rect.
    image, src, dst = canvas.drawImageRect.call_args[0]
    assert image.size == (100, 50)
    assert src == (0, 0, 100, 50)
    assert dst == (0, 0, 300, 150)
    flush_size_change_callbacks()
    assert draw.call_args_list[-1].args == (300, 150)


def test_without_a_window_the_ratio_is_one(fake_skia: list[tuple[int, int]]) -> None:
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = _Drawn(draw, width=80, height=40)

    surface.layout(80, 40)
    flush_size_change_callbacks()

    assert draw.call_args.args == (80, 40)
    assert surface.pixel_ratio == 1.0


def test_a_request_before_layout_waits_for_the_size(fake_skia: list[tuple[int, int]]) -> None:
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = _Drawn(draw, width=80, height=40)

    surface.request_render()
    flush_size_change_callbacks()
    assert draw.call_count == 0

    surface.layout(80, 40)
    flush_size_change_callbacks()
    assert draw.call_count == 1


def test_requests_in_one_frame_make_one_raster(fake_skia: list[tuple[int, int]]) -> None:
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = _Drawn(draw, width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    surface.request_render()
    surface.request_render()
    surface.request_render()
    flush_size_change_callbacks()

    assert draw.call_count == 2


# --- What is shown -----------------------------------------------------------------


def test_a_surface_made_directly_shows_nothing(fake_skia: list[tuple[int, int]]) -> None:
    surface = RasterSurface(width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    assert fake_skia == []
    assert _painted(surface, 80, 40) is None


def test_draw_from_data_passes_the_value_and_follows_changes(fake_skia: list[tuple[int, int]]) -> None:
    data: State[int] = State(1)
    seen: list[tuple[int, int, int]] = []

    def draw(value: int, w: int, h: int) -> bytes:
        seen.append((value, w, h))
        return _pixels(w, h)

    surface = RasterSurface.draw(data, draw, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    data.value = 2
    flush_size_change_callbacks()

    assert seen == [(1, 80, 40), (2, 80, 40)]


def test_a_buffer_of_the_wrong_size_leaves_the_surface_as_it_was(fake_skia: list[tuple[int, int]]) -> None:
    surface = _Drawn(lambda w, h: bytes(7), width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    assert _painted(surface, 80, 40) is None


def test_none_empties_the_surface(fake_skia: list[tuple[int, int]]) -> None:
    pixels: list[bytes | None] = [_pixels(80, 40)]
    surface = _Drawn(lambda w, h: pixels[0], width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    pixels[0] = None
    surface.request_render()
    flush_size_change_callbacks()

    assert _painted(surface, 80, 40) is None


def test_the_raster_is_painted_into_the_content_rect(
    fake_skia: list[tuple[int, int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _on_display(monkeypatch, 2.0)
    surface = _Drawn(lambda w, h: _pixels(w, h), width=100, height=60, padding=(10, 5))
    surface.layout(100, 60)
    flush_size_change_callbacks()

    canvas = MagicMock()
    surface.paint(canvas, 20, 30, 100, 60)

    _image, src, dst = canvas.drawImageRect.call_args[0]
    assert src == (0, 0, 160, 100)
    assert dst == (30, 35, 80, 50)


# --- draw with a coroutine function ----------------------------------------------


class _ManualClock:
    """Holds what a thread scheduled until the test ticks; safe to schedule from two threads."""

    def __init__(self) -> None:
        self._scheduled: list[Callable[[float], None]] = []
        self._lock = threading.Lock()

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        with self._lock:
            self._scheduled.append(fn)

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        raise NotImplementedError

    def unschedule(self, fn: Callable[[float], None]) -> None:
        with self._lock:
            self._scheduled = [each for each in self._scheduled if each != fn]

    def tick(self) -> None:
        with self._lock:
            due, self._scheduled = self._scheduled, []
        for fn in due:
            fn(0.0)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _ManualClock:
    manual = _ManualClock()
    monkeypatch.setattr(runtime, "clock", manual)
    return manual


async def _settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


class _GatedTasks:
    """A coroutine draw function whose calls return when the test releases them."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []
        self._gates: dict[int, asyncio.Event] = {}

    async def __call__(self, value: int, w: int, h: int) -> bytes:
        self.calls.append((value, w, h))
        await self._gates.setdefault(value, asyncio.Event()).wait()
        return _pixels(w, h)

    def finish(self, value: int) -> None:
        self._gates.setdefault(value, asyncio.Event()).set()


async def test_a_coroutine_draw_function_is_awaited_and_no_frame_waits(fake_skia: list[tuple[int, int]]) -> None:
    runs = _GatedTasks()
    surface = RasterSurface.draw(State(1), runs, width=80, height=40)
    surface.layout(80, 40)

    flush_size_change_callbacks()
    await _settle()

    # The frame start returned with the call still running.
    assert runs.calls == [(1, 80, 40)]
    assert _painted(surface, 80, 40) is None
    runs.finish(1)
    await _settle()
    assert _painted(surface, 80, 40).size == (80, 40)


async def test_changes_during_a_coroutine_call_are_drawn_once_with_the_newest(
    fake_skia: list[tuple[int, int]],
) -> None:
    data: State[int] = State(1)
    runs = _GatedTasks()
    surface = RasterSurface.draw(data, runs, width="wt", height="wt")
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    await _settle()

    data.value = 2
    flush_size_change_callbacks()
    data.value = 3
    surface.layout(160, 80)
    flush_size_change_callbacks()
    await _settle()
    assert runs.calls == [(1, 80, 40)]

    runs.finish(1)
    await _settle()
    flush_size_change_callbacks()
    await _settle()

    # Value 2 was never drawn; the next call took the newest value and size.
    assert runs.calls == [(1, 80, 40), (3, 160, 80)]
    assert _painted(surface, 160, 80).size == (80, 40)
    runs.finish(3)
    await _settle()
    assert _painted(surface, 160, 80).size == (160, 80)


async def test_a_coroutine_call_that_raises_keeps_the_raster(fake_skia: list[tuple[int, int]]) -> None:
    data: State[int] = State(1)

    async def draw(value: int, w: int, h: int) -> bytes:
        if value == 2:
            raise RuntimeError("boom")
        return _pixels(w, h)

    surface = RasterSurface.draw(data, draw, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    await _settle()

    data.value = 2
    flush_size_change_callbacks()
    await _settle()
    assert _painted(surface, 80, 40).size == (80, 40)

    data.value = 3
    flush_size_change_callbacks()
    await _settle()
    assert fake_skia == [(80, 40), (80, 40)]


# --- draw_in_thread ------------------------------------------------------------------


class _GatedThreads:
    """A draw function whose calls return when the test releases them, and say which thread ran them."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []
        self.threads: list[str] = []
        self.fail: set[int] = set()
        self._gates: dict[int, threading.Event] = {}
        self._lock = threading.Lock()

    def _gate(self, value: int) -> threading.Event:
        with self._lock:
            return self._gates.setdefault(value, threading.Event())

    def __call__(self, value: int, w: int, h: int) -> bytes:
        self.calls.append((value, w, h))
        self.threads.append(threading.current_thread().name)
        assert self._gate(value).wait(_TIMEOUT)
        if value in self.fail:
            raise RuntimeError("boom")
        return _pixels(w, h)

    def finish(self, value: int) -> None:
        """Release the call for ``value`` and wait until its thread has handed the result over."""
        self._gate(value).set()
        for thread in threading.enumerate():
            if thread.name == "RasterSurface.draw_in_thread":
                thread.join(_TIMEOUT)


def _started(runs: _GatedThreads, count: int) -> None:
    """Wait until ``count`` calls have begun."""
    deadline = threading.Event()
    for _ in range(int(_TIMEOUT / 0.001)):
        if len(runs.calls) >= count:
            return
        deadline.wait(0.001)
    raise AssertionError(f"{count} calls expected, {len(runs.calls)} began")


def test_draw_in_thread_calls_the_function_off_the_ui_thread(
    fake_skia: list[tuple[int, int]], clock: _ManualClock
) -> None:
    runs = _GatedThreads()
    surface = RasterSurface.draw_in_thread(State(1), runs, width=80, height=40)
    surface.layout(80, 40)

    flush_size_change_callbacks()
    _started(runs, 1)

    assert runs.calls == [(1, 80, 40)]
    assert runs.threads == ["RasterSurface.draw_in_thread"]
    # Nothing is shown until the call returns and the UI thread takes the result.
    assert _painted(surface, 80, 40) is None
    runs.finish(1)
    assert _painted(surface, 80, 40) is None
    clock.tick()
    assert _painted(surface, 80, 40).size == (80, 40)


def test_changes_during_a_thread_call_are_drawn_once_with_the_newest(
    fake_skia: list[tuple[int, int]], clock: _ManualClock
) -> None:
    data: State[int] = State(1)
    runs = _GatedThreads()
    surface = RasterSurface.draw_in_thread(data, runs, width="wt", height="wt")
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    _started(runs, 1)

    data.value = 2
    flush_size_change_callbacks()
    data.value = 3
    surface.layout(160, 80)
    flush_size_change_callbacks()
    # One call at a time: neither change started a second one.
    assert runs.calls == [(1, 80, 40)]

    runs.finish(1)
    clock.tick()
    # The first result is shown, stretched over the new rect, while the next call runs.
    assert _painted(surface, 160, 80).size == (80, 40)
    flush_size_change_callbacks()
    _started(runs, 2)
    assert runs.calls == [(1, 80, 40), (3, 160, 80)]

    runs.finish(3)
    clock.tick()
    assert _painted(surface, 160, 80).size == (160, 80)
    flush_size_change_callbacks()
    assert len(runs.calls) == 2


def test_a_thread_call_that_raises_keeps_the_raster_and_the_next_change_draws(
    fake_skia: list[tuple[int, int]], clock: _ManualClock
) -> None:
    data: State[int] = State(1)
    runs = _GatedThreads()
    runs.fail.add(2)
    surface = RasterSurface.draw_in_thread(data, runs, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    _started(runs, 1)
    runs.finish(1)
    clock.tick()

    data.value = 2
    flush_size_change_callbacks()
    _started(runs, 2)
    runs.finish(2)
    clock.tick()
    assert _painted(surface, 80, 40).size == (80, 40)

    data.value = 3
    flush_size_change_callbacks()
    _started(runs, 3)
    runs.finish(3)
    clock.tick()
    assert fake_skia == [(80, 40), (80, 40)]


def test_draw_in_thread_reads_the_value_on_the_ui_thread(fake_skia: list[tuple[int, int]], clock: _ManualClock) -> None:
    readers: list[str] = []

    class _Watched(State[int]):
        @property
        def value(self) -> int:
            readers.append(threading.current_thread().name)
            return 7

        @value.setter
        def value(self, new: int) -> None:
            raise AssertionError("the surface never writes its data")

    runs = _GatedThreads()
    surface = RasterSurface.draw_in_thread(_Watched(7), runs, width=80, height=40)
    surface.layout(80, 40)
    readers.clear()
    flush_size_change_callbacks()
    _started(runs, 1)
    runs.finish(7)

    assert runs.calls == [(7, 80, 40)]
    assert readers and set(readers) == {threading.current_thread().name}


def test_draw_in_thread_refuses_a_coroutine_function() -> None:
    async def draw(value: int, w: int, h: int) -> bytes:
        return _pixels(w, h)

    with pytest.raises(TypeError):
        RasterSurface.draw_in_thread(State(1), draw, width=80, height=40)


def test_where_no_thread_starts_the_surface_stays_empty_and_asks_again(
    fake_skia: list[tuple[int, int]], clock: _ManualClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(self: threading.Thread) -> None:
        raise RuntimeError("can't start new thread")

    data: State[int] = State(1)
    draw = MagicMock(side_effect=lambda value, w, h: _pixels(w, h))
    surface = RasterSurface.draw_in_thread(data, draw, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    with monkeypatch.context() as patched:
        patched.setattr(threading.Thread, "start", refuse)
        flush_size_change_callbacks()
    assert draw.call_count == 0
    assert _painted(surface, 80, 40) is None

    # The failed start did not leave the surface waiting for a call that never ran.
    data.value = 2
    flush_size_change_callbacks()
    for thread in threading.enumerate():
        if thread.name == "RasterSurface.draw_in_thread":
            thread.join(_TIMEOUT)
    clock.tick()
    assert _painted(surface, 80, 40).size == (80, 40)


def test_a_thread_function_that_returns_an_awaitable_is_refused_and_closed(
    fake_skia: list[tuple[int, int]], clock: _ManualClock, recwarn: pytest.WarningsRecorder
) -> None:
    async def worker(value: int, w: int, h: int) -> bytes:
        return _pixels(w, h)

    surface = RasterSurface.draw_in_thread(State(1), lambda v, w, h: worker(v, w, h), width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    for thread in threading.enumerate():
        if thread.name == "RasterSurface.draw_in_thread":
            thread.join(_TIMEOUT)
    clock.tick()

    assert fake_skia == []
    assert _painted(surface, 80, 40) is None
    # The coroutine was closed, so Python has no "never awaited" to report.
    assert not [w for w in recwarn.list if "never awaited" in str(w.message)]


def test_a_result_that_cannot_be_handed_over_does_not_stop_the_surface(
    fake_skia: list[tuple[int, int]], clock: _ManualClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(fn: Callable[[float], None], delay: float) -> None:
        raise RuntimeError("the clock is gone")

    data: State[int] = State(1)
    draw = MagicMock(side_effect=lambda value, w, h: _pixels(w, h))
    surface = RasterSurface.draw_in_thread(data, draw, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    with monkeypatch.context() as patched:
        patched.setattr(clock, "schedule_once", refuse)
        flush_size_change_callbacks()
        for thread in threading.enumerate():
            if thread.name == "RasterSurface.draw_in_thread":
                thread.join(_TIMEOUT)

    data.value = 2
    flush_size_change_callbacks()
    for thread in threading.enumerate():
        if thread.name == "RasterSurface.draw_in_thread":
            thread.join(_TIMEOUT)
    clock.tick()
    assert draw.call_args.args == (2, 80, 40)
    assert _painted(surface, 80, 40).size == (80, 40)


# --- Edges every way of drawing shares -------------------------------------------


def test_data_that_raises_when_read_is_a_failed_draw(fake_skia: list[tuple[int, int]]) -> None:
    broken = [False]

    class _Flaky(State[int]):
        @property
        def value(self) -> int:
            if broken[0]:
                raise RuntimeError("boom")
            return 1

        @value.setter
        def value(self, new: int) -> None:
            raise AssertionError("the surface never writes its data")

    surface = RasterSurface.draw(_Flaky(1), lambda value, w, h: _pixels(w, h), width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    broken[0] = True
    surface.request_render()
    # The failure stays inside the surface: the frame-start queue sees no exception.
    surface._render()

    assert _painted(surface, 80, 40).size == (80, 40)


def test_a_request_made_at_no_size_is_drawn_when_the_size_comes_back(fake_skia: list[tuple[int, int]]) -> None:
    data: State[int] = State(1)
    seen: list[int] = []

    def draw(value: int, w: int, h: int) -> bytes:
        seen.append(value)
        return _pixels(w, h)

    surface = RasterSurface.draw(data, draw, width="wt", height="wt")
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    surface.layout(0, 0)
    data.value = 2
    flush_size_change_callbacks()
    assert seen == [1]

    surface.layout(80, 40)
    flush_size_change_callbacks()
    assert seen == [1, 2]


async def test_unmounting_cancels_the_call_being_awaited(fake_skia: list[tuple[int, int]]) -> None:
    data: State[int] = State(1)
    cancelled: list[int] = []
    calls: list[int] = []

    async def draw(value: int, w: int, h: int) -> bytes:
        calls.append(value)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append(value)
            raise
        return _pixels(w, h)

    surface = RasterSurface.draw(data, draw, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    await _settle()
    data.value = 2
    flush_size_change_callbacks()

    surface.unmount()
    await _settle()
    flush_size_change_callbacks()
    await _settle()

    assert cancelled == [1]
    # The change that waited for the call is not drawn for a surface nobody shows.
    assert calls == [1]


def test_a_thread_result_that_lands_after_unmount_is_not_shown_and_starts_nothing(
    fake_skia: list[tuple[int, int]], clock: _ManualClock
) -> None:
    data: State[int] = State(1)
    runs = _GatedThreads()
    surface = RasterSurface.draw_in_thread(data, runs, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    _started(runs, 1)
    data.value = 2
    flush_size_change_callbacks()

    surface.unmount()
    runs.finish(1)
    clock.tick()
    flush_size_change_callbacks()

    assert _painted(surface, 80, 40) is None
    assert runs.calls == [(1, 80, 40)]


# --- Mounted again -------------------------------------------------------------------


def test_a_surface_mounted_again_draws_the_current_value_and_follows_changes(
    fake_skia: list[tuple[int, int]],
) -> None:
    data: State[int] = State(1)
    seen: list[int] = []

    def draw(value: int, w: int, h: int) -> bytes:
        seen.append(value)
        return _pixels(w, h)

    surface = RasterSurface.draw(data, draw, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    surface.unmount()
    data.value = 2
    flush_size_change_callbacks()
    assert seen == [1]

    surface.mount(None)
    # The same size as before the unmount: the layout alone queues nothing.
    surface.layout(80, 40)
    flush_size_change_callbacks()
    assert seen == [1, 2]
    data.value = 3
    flush_size_change_callbacks()
    assert seen == [1, 2, 3]


def test_a_thread_surface_mounted_again_draws_the_current_value_and_follows_changes(
    fake_skia: list[tuple[int, int]], clock: _ManualClock
) -> None:
    data: State[int] = State(1)
    runs = _GatedThreads()
    surface = RasterSurface.draw_in_thread(data, runs, width=80, height=40)
    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    _started(runs, 1)
    runs.finish(1)
    clock.tick()
    surface.unmount()
    data.value = 2

    surface.mount(None)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    _started(runs, 2)
    runs.finish(2)
    clock.tick()
    data.value = 3
    flush_size_change_callbacks()
    _started(runs, 3)
    runs.finish(3)
    clock.tick()

    assert [value for value, _w, _h in runs.calls] == [1, 2, 3]
    assert fake_skia == [(80, 40), (80, 40), (80, 40)]


@pytest.mark.parametrize("make", [RasterSurface.draw, RasterSurface.draw_in_thread])
def test_only_a_mounted_surface_holds_a_subscription_on_its_data(
    make: Callable[..., RasterSurface],
) -> None:
    data: State[int] = State(1)
    surface = make(data, lambda value, w, h: _pixels(w, h), width=80, height=40)
    assert data._subs == []

    for _ in range(2):
        surface.mount(None)
        assert len(data._subs) == 1
        surface.unmount()
        assert data._subs == []


async def test_a_surface_built_once_by_a_column_builder_follows_its_data_when_it_comes_back() -> None:
    """The issue's reproduction: one surface leaves the list and comes back."""
    drawn: list[int] = []

    def draw(value: int, w: int, h: int) -> bytes:
        drawn.append(value)
        return _pixels(w, h)

    value: State[int] = State(1)
    shown: State[list[str]] = State(["surface"])
    surface = RasterSurface.draw_in_thread(value, draw, width=100, height=100, key="surface")

    class _Pane(ComposableWidget):
        def build(self) -> Widget:
            return Column.builder(shown, lambda _item, _index: surface, key_fn=lambda item, _index: item)

    with AppHarness(_Pane, size=(300, 300)) as app:
        await app.wait_for(lambda: drawn == [1])
        shown.value = []
        await app.idle()
        value.value = 2
        shown.value = ["surface"]
        await app.wait_for(lambda: drawn == [1, 2])
        value.value = 3
        await app.wait_for(lambda: drawn == [1, 2, 3])
