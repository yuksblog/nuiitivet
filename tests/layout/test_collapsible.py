"""Tests for Collapsible widget."""

from contextlib import contextmanager
from typing import Callable, Generator

from nuiitivet.animation.motion import LinearMotion
from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.observable import runtime as observable_runtime
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box

# ---------------------------------------------------------------------------
# Fake clock helper
# ---------------------------------------------------------------------------


class _FakeClock:
    def __init__(self) -> None:
        self._interval_callbacks: list[Callable[[float], None]] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        del fn, delay

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        del interval
        if fn not in self._interval_callbacks:
            self._interval_callbacks.append(fn)

    def unschedule(self, fn: Callable[[float], None]) -> None:
        self._interval_callbacks = [cb for cb in self._interval_callbacks if cb is not fn]

    def advance(self, dt: float) -> None:
        for cb in list(self._interval_callbacks):
            cb(dt)

    def advance_frames(self, count: int, fps: float = 60.0) -> None:
        dt = 1.0 / fps
        for _ in range(count):
            self.advance(dt)

    @property
    def active(self) -> int:
        return len(self._interval_callbacks)


@contextmanager
def _fake_clock() -> Generator[_FakeClock, None, None]:
    prev = observable_runtime.clock
    fake = _FakeClock()
    observable_runtime.set_clock(fake)
    try:
        yield fake
    finally:
        observable_runtime.set_clock(prev)


def _make_child(w: int = 100, h: int = 50) -> Box:
    return Box(width=Sizing.fixed(w), height=Sizing.fixed(h))


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_initial_size_snaps_to_natural_without_animation(nuiitivet_mount) -> None:
    with _fake_clock():
        widget = Collapsible(_make_child(100, 50))
        nuiitivet_mount(widget)
        assert widget.preferred_size() == (100, 50)


def test_opened_false_collapses_initial_size(nuiitivet_mount) -> None:
    with _fake_clock():
        widget = Collapsible(_make_child(100, 50), opened=False)
        nuiitivet_mount(widget)
        assert widget.preferred_size() == (0, 0)


def test_axis_horizontal_only_animates_width(nuiitivet_mount) -> None:
    with _fake_clock():
        opened = _ObservableValue(True)
        widget = Collapsible(_make_child(100, 50), opened=opened, axis="horizontal")
        nuiitivet_mount(widget)
        # Height passes through unchanged immediately even mid-animation.
        opened.value = False
        widget.preferred_size()
        _, h = widget.preferred_size()
        assert h == 50


# ---------------------------------------------------------------------------
# Animated open / close
# ---------------------------------------------------------------------------


def test_opened_toggle_animates_width_to_zero(nuiitivet_mount) -> None:
    with _fake_clock() as clock:
        opened = _ObservableValue(True)
        widget = Collapsible(
            _make_child(100, 50),
            opened=opened,
            axis="horizontal",
            motion=LinearMotion(0.2),
        )
        nuiitivet_mount(widget)
        assert widget.preferred_size()[0] == 100

        opened.value = False
        widget.preferred_size()  # triggers retarget to 0
        clock.advance_frames(6)  # ~0.1s of 0.2s
        mid_w = widget.preferred_size()[0]
        assert 0 < mid_w < 100

        clock.advance_frames(20)  # finish
        assert widget.preferred_size()[0] == 0


def test_distinct_motion_out_used_on_close(nuiitivet_mount) -> None:
    with _fake_clock() as clock:
        opened = _ObservableValue(True)
        widget = Collapsible(
            _make_child(100, 50),
            opened=opened,
            axis="horizontal",
            motion=LinearMotion(1.0),
            motion_out=LinearMotion(0.1),
        )
        nuiitivet_mount(widget)
        widget.preferred_size()

        opened.value = False
        widget.preferred_size()
        # motion_out is fast (0.1s); after ~0.12s it should be fully collapsed.
        clock.advance_frames(8)
        assert widget.preferred_size()[0] == 0


# ---------------------------------------------------------------------------
# Follow natural size changes (opened=True always)
# ---------------------------------------------------------------------------


def test_follows_child_natural_size_change(nuiitivet_mount) -> None:
    with _fake_clock() as clock:
        child = _make_child(100, 50)
        widget = Collapsible(child, motion=LinearMotion(0.2))
        nuiitivet_mount(widget)
        assert widget.preferred_size() == (100, 50)

        child.width_sizing = Sizing.fixed(200)
        widget.preferred_size()  # detect + retarget
        clock.advance_frames(20)
        assert widget.preferred_size()[0] == 200


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def test_unmount_stops_ticking_and_disposes(nuiitivet_mount) -> None:
    with _fake_clock() as clock:
        opened = _ObservableValue(True)
        widget = Collapsible(
            _make_child(100, 50),
            opened=opened,
            axis="horizontal",
            motion=LinearMotion(0.5),
        )
        nuiitivet_mount(widget)
        widget.preferred_size()
        opened.value = False
        widget.preferred_size()
        clock.advance_frames(2)
        assert clock.active > 0

        widget.unmount()
        # No active interval callbacks remain after unmount.
        assert clock.active == 0
