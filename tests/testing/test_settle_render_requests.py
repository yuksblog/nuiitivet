"""A render request runs in every settle pass and does not extend the settle loop."""

from __future__ import annotations

import threading
from typing import Any, Callable

import pytest

from nuiitivet._interaction.action import LayoutNotConvergedError
from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.modifiers.size_changed import on_size_changed
from nuiitivet.observable import State
from nuiitivet.rendering.size import Size
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks, queue_deferred_publish
from nuiitivet.widgets.raster_surface import RasterSurface

_TIMEOUT = 5.0
# More values than any settle's pass cap.
_PRODUCED = 20


def _pixels(width: int, height: int) -> bytes:
    return bytes(width * height * 4)


def _write_from_a_thread(data: State[int], value: int) -> None:
    """Write *value* from another thread, so it reaches the UI thread at the next pump."""
    writer = threading.Thread(target=lambda: setattr(data, "value", value))
    writer.start()
    writer.join()


def _join_surface_threads() -> None:
    for thread in threading.enumerate():
        if thread.name == "RasterSurface.draw_in_thread":
            thread.join(_TIMEOUT)


class _Drawn(RasterSurface):
    """A surface that draws itself, with no data."""

    def __init__(self, draw: Callable[[int, int, int], bytes], **layout: Any) -> None:
        super().__init__(**layout)
        self._draw_fn = draw

    def draw_pixels(self, width_px: int, height_px: int) -> Any:
        return self._draw_fn(0, width_px, height_px)


@pytest.fixture(autouse=True)
def _drained_queue():
    """Keep queued publishes from leaking between tests."""
    flush_size_change_callbacks()
    try:
        yield
    finally:
        flush_size_change_callbacks()


def test_a_publish_that_cannot_change_the_layout_runs_and_reports_nothing() -> None:
    ran: list[str] = []
    key = object()

    queue_deferred_publish(key, lambda: ran.append("render"), affects_layout=False)

    assert flush_size_change_callbacks() is False
    assert ran == ["render"]


def test_a_publish_that_can_change_the_layout_reports_a_change() -> None:
    ran: list[str] = []
    key = object()

    queue_deferred_publish(key, lambda: ran.append("metrics"), affects_layout=True)

    assert flush_size_change_callbacks() is True
    assert ran == ["metrics"]


def test_settle_returns_while_a_producer_keeps_sending_values(nuiitivet_app: Any) -> None:
    data = State(0)
    drawn: list[int] = []

    def draw(value: int, w: int, h: int) -> bytes:
        drawn.append(value)
        if value < _PRODUCED:
            # Every draw hands the next value over: each pass has a new render.
            _write_from_a_thread(data, value + 1)
        return _pixels(w, h)

    app = nuiitivet_app(RasterSurface.draw(data, draw, width=200, height=100), size=(300, 200))

    for _ in range(_PRODUCED):
        app.settle()
        # The render this settle requested has run. The next value waits on the
        # clock: a write from another thread lands only at the next pump.
        assert drawn[-1] == data.value

    assert drawn == list(range(_PRODUCED + 1))


async def test_idle_returns_while_a_producer_keeps_sending_values(nuiitivet_app: Any) -> None:
    data = State(0)
    drawn: list[int] = []

    def draw(value: int, w: int, h: int) -> bytes:
        drawn.append(value)
        if value < _PRODUCED:
            _write_from_a_thread(data, value + 1)
        return _pixels(w, h)

    app = nuiitivet_app(RasterSurface.draw(data, draw, width=200, height=100), size=(300, 200))

    await app.idle()
    assert drawn[-1] == data.value

    await app.wait_for(lambda: drawn[-1] == _PRODUCED, timeout=_TIMEOUT)


async def test_a_draw_in_thread_surface_whose_data_changes_during_a_draw_settles(nuiitivet_app: Any) -> None:
    data = State(0)
    drawn: list[int] = []
    started = threading.Event()
    release = threading.Event()

    def draw(value: int, w: int, h: int) -> bytes:
        drawn.append(value)
        if value == 0:
            started.set()
            release.wait(_TIMEOUT)
        return _pixels(w, h)

    app = nuiitivet_app(RasterSurface.draw_in_thread(data, draw, width=200, height=100), size=(300, 200))
    try:
        assert started.wait(_TIMEOUT)
        data.value = 1
        # The render meets the running draw and waits for it.
        app.settle()
        release.set()

        await app.wait_for(lambda: drawn == [0, 1], timeout=_TIMEOUT)
        await app.idle()
    finally:
        release.set()
        _join_surface_threads()

    assert drawn == [0, 1]


def test_a_render_requested_by_a_size_callback_has_run_when_settle_returns(nuiitivet_app: Any) -> None:
    data = State(0)
    drawn: list[int] = []

    def draw(value: int, w: int, h: int) -> bytes:
        drawn.append(value)
        return _pixels(w, h)

    def on_size(size: Size) -> None:
        data.value = size.width

    def screen() -> Widget:
        return Column(
            children=[
                Container(width=Sizing.fixed(120), height=Sizing.fixed(10)).modifier(on_size_changed(on_size)),
                RasterSurface.draw(data, draw, width=200, height=100),
            ]
        )

    nuiitivet_app(screen, size=(300, 200))

    assert drawn[-1] == 120


def test_a_render_requested_by_a_render_has_run_when_settle_returns(nuiitivet_app: Any) -> None:
    data = State(0)
    follower_drawn: list[int] = []

    def draw_follower(value: int, w: int, h: int) -> bytes:
        follower_drawn.append(value)
        return _pixels(w, h)

    follower = RasterSurface.draw(data, draw_follower, width=200, height=50)

    def draw_leader(value: int, w: int, h: int) -> bytes:
        follower.request_render()
        return _pixels(w, h)

    leader = _Drawn(draw_leader, width=200, height=50)
    app = nuiitivet_app(Column(children=[leader, follower]), size=(300, 200))
    follower_drawn.clear()

    leader.request_render()
    app.settle()

    assert follower_drawn == [0]


class _Oscillating(ComposableWidget):
    """A box whose size callback, once armed, resizes the box it measures."""

    def __init__(self) -> None:
        super().__init__(width=Sizing.weight(1), height=Sizing.weight(1))
        self.armed = False
        self.box = Container(width=Sizing.fixed(100), height=Sizing.weight(1))

    def _on_size(self, size: Size) -> None:
        if self.armed:
            self.box.width_sizing = Sizing.fixed(100 if size.width != 100 else 300)

    def build(self) -> Widget:
        return Column(children=[self.box.modifier(on_size_changed(self._on_size))])


def test_a_size_callback_that_keeps_resizing_what_it_measures_still_raises(nuiitivet_app: Any) -> None:
    screen = _Oscillating()
    app = nuiitivet_app(screen, size=(800, 600))

    screen.armed = True
    screen.box.width_sizing = Sizing.fixed(300)

    with pytest.raises(LayoutNotConvergedError):
        app.settle()
