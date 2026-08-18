"""Tests for Collapsible widget."""

from contextlib import contextmanager
from typing import Callable, Generator, Optional, Tuple

from nuiitivet.animation.motion import LinearMotion
from nuiitivet.layout.collapsible import Collapsible
from nuiitivet.layout.column import Column
from nuiitivet.observable import runtime as observable_runtime
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box
from nuiitivet.widgeting.widget import Widget

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


class _WrappingChild(Widget):
    """A child whose natural height depends on the width it is offered.

    Stands in for wrapping text: 400px of content reflowed into as many lines
    as the offered width needs. Measured with no constraint it is one long
    line, which is what makes it disagree across measure and layout passes.
    """

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        if max_width is None:
            return (400, 20)
        w = max(1, min(400, int(max_width)))
        lines = -(-400 // w)
        return (w, 20 * lines)


class _ClampingChild(Widget):
    """Reports at most the size it is offered, as a constrained child does."""

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        w = 100 if max_width is None else min(100, int(max_width))
        h = 50 if max_height is None else min(50, int(max_height))
        return (w, h)


def _frame(
    widget: Widget,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Tuple[int, int]:
    """Drive one parent frame: measure, then lay out at the measured size.

    This is what a parent actually does, and since #531 it is the only thing
    that moves a Collapsible's animation targets -- measuring alone never does.
    """
    size = widget.preferred_size(width, height)
    widget.layout(size[0], size[1])
    return size


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_initial_size_snaps_to_natural_without_animation(nuiitivet_mount) -> None:
    with _fake_clock() as clock:
        widget = Collapsible(_make_child(100, 50))
        nuiitivet_mount(widget)
        assert _frame(widget) == (100, 50)
        assert clock.active == 0


def test_opened_false_collapses_initial_size(nuiitivet_mount) -> None:
    with _fake_clock() as clock:
        widget = Collapsible(_make_child(100, 50), opened=False)
        nuiitivet_mount(widget)
        assert _frame(widget) == (0, 0)
        assert clock.active == 0


def test_axis_horizontal_only_animates_width(nuiitivet_mount) -> None:
    with _fake_clock():
        opened = _ObservableValue(True)
        widget = Collapsible(_make_child(100, 50), opened=opened, axis="horizontal")
        nuiitivet_mount(widget)
        # Height passes through unchanged immediately even mid-animation.
        opened.value = False
        _frame(widget)
        _, h = _frame(widget)
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
        assert _frame(widget)[0] == 100

        opened.value = False
        _frame(widget)  # layout retargets to 0
        clock.advance_frames(6)  # ~0.1s of 0.2s
        mid_w = _frame(widget)[0]
        assert 0 < mid_w < 100

        clock.advance_frames(20)  # finish
        assert _frame(widget)[0] == 0


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
        _frame(widget)

        opened.value = False
        _frame(widget)
        # motion_out is fast (0.1s); after ~0.13s it should be fully collapsed.
        clock.advance_frames(8)
        assert _frame(widget)[0] == 0


# ---------------------------------------------------------------------------
# Follow natural size changes (opened=True always)
# ---------------------------------------------------------------------------


def test_follows_child_natural_size_change(nuiitivet_mount) -> None:
    with _fake_clock() as clock:
        child = _make_child(100, 50)
        widget = Collapsible(child, motion=LinearMotion(0.2))
        nuiitivet_mount(widget)
        assert _frame(widget) == (100, 50)

        child.width_sizing = Sizing.fixed(200)
        _frame(widget)  # detect + retarget
        clock.advance_frames(20)
        assert _frame(widget)[0] == 200


# ---------------------------------------------------------------------------
# Measuring is a query, not a command (#531)
# ---------------------------------------------------------------------------


def test_measure_never_retargets(nuiitivet_mount) -> None:
    """Speculative measures must not move the target or start an animation."""
    with _fake_clock() as clock:
        widget = Collapsible(_WrappingChild(), axis="vertical", motion=LinearMotion(0.2))
        nuiitivet_mount(widget)
        settled = _frame(widget, 100)
        assert settled == (100, 80)  # the height the offered width wraps to

        # The constraints a parent speculates with vary; the animation must not.
        widget.preferred_size(400)
        widget.preferred_size(50)
        assert clock.active == 0
        assert widget.preferred_size(100) == settled

        # ...and time passing changes nothing either, because nothing is running.
        clock.advance_frames(20)
        assert widget.preferred_size(100) == settled


def test_target_stable_across_a_column_frame(nuiitivet_mount) -> None:
    """A Column measures its child twice per frame; the target must not flip.

    Column measures in ``preferred_size`` and again in ``layout``, and the
    Collapsible measures its own child once more. With a child whose size
    depends on the offered width, those used to resolve different targets.
    """
    with _fake_clock() as clock:
        collapsible = Collapsible(_WrappingChild(), axis="vertical", motion=LinearMotion(0.2))
        column = Column(children=[collapsible], width=Sizing.fixed(120), padding=(10, 0, 10, 0))
        nuiitivet_mount(column)

        _frame(column, 120, 300)
        # The wrapped size the parent was told about, not the unconstrained one.
        settled = collapsible.preferred_size(100)
        assert settled == (100, 80)
        assert clock.active == 0

        # A second identical frame must be a no-op.
        _frame(column, 120, 300)
        assert collapsible.preferred_size(100) == settled
        assert clock.active == 0


def test_collapsed_axis_ignores_the_size_the_parent_echoes_back(nuiitivet_mount) -> None:
    """An animated axis must not be measured against its own collapsed size.

    A Grid measures a child against the cell it was given, and that cell came
    from what this widget last reported. Feeding a collapsed axis its own zero
    back in would pin the target at zero, and the panel could never reopen.
    """
    with _fake_clock() as clock:
        opened = _ObservableValue(False)
        widget = Collapsible(
            _ClampingChild(),
            opened=opened,
            axis="vertical",
            motion=LinearMotion(0.2),
        )
        nuiitivet_mount(widget)
        # Closed, so the parent hands back a zero-high cell and measures in it.
        assert _frame(widget, 100, 0) == (100, 0)

        opened.value = True
        widget.preferred_size(100, 0)
        widget.layout(100, 0)
        clock.advance_frames(20)
        assert widget.preferred_size(100, 0) == (100, 50)


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
        _frame(widget)
        opened.value = False
        _frame(widget)
        clock.advance_frames(2)
        assert clock.active > 0

        widget.unmount()
        # No active interval callbacks remain after unmount.
        assert clock.active == 0
