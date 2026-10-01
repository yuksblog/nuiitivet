import time

import pytest

from nuiitivet.backends.pyglet.event_loop import ResponsiveEventLoop
from nuiitivet.runtime.renderer import RendererError


class _DummyWindow:
    has_exit = False

    def switch_to(self):
        return None

    def dispatch_pending_events(self):
        return None


def test_request_draw_inside_callback_is_preserved():
    recorded = []

    def _draw(dt: float) -> None:
        recorded.append(dt)
        loop.request_draw()

    loop = ResponsiveEventLoop(_draw, draw_fps=None)

    # Pretend a draw was requested by user code.
    loop._draw_pending = True

    loop._perform_draw(0.016, time.perf_counter())

    assert recorded, "Draw callback should be invoked"
    assert loop._draw_pending is True, "request_draw() inside callback must schedule another frame"


def test_perform_draw_lets_a_renderer_error_through():
    def _draw(dt: float) -> None:
        raise RendererError("renderer='gpu' was requested but GPU frame rendering failed.")

    loop = ResponsiveEventLoop(_draw, draw_fps=None)
    loop._draw_pending = True

    with pytest.raises(RendererError):
        loop._perform_draw(0.016, time.perf_counter())


def test_perform_draw_swallows_other_exceptions():
    def _draw(dt: float) -> None:
        raise ValueError("transient")

    loop = ResponsiveEventLoop(_draw, draw_fps=None)
    loop._draw_pending = True

    loop._perform_draw(0.016, time.perf_counter())  # logged once, loop goes on
    assert loop._draw_pending is False


def _noop_draw(dt: float) -> None:
    return None


# ---------------------------------------------------------------------------
# _should_draw semantics
# ---------------------------------------------------------------------------


def test_should_draw_on_demand_only_when_pending():
    """With no cadence, draw exactly when a request is pending."""
    loop = ResponsiveEventLoop(_noop_draw, draw_fps=None)
    now = time.perf_counter()

    loop._draw_pending = False
    assert loop._should_draw(now) is False

    loop._draw_pending = True
    assert loop._should_draw(now) is True


def test_should_draw_cadence_is_a_throttle_not_a_trigger():
    """With a cadence, a clean tree never draws even past the deadline."""
    loop = ResponsiveEventLoop(_noop_draw, draw_fps=30.0)
    now = time.perf_counter()

    # Deadline already elapsed, but nothing is pending -> no frame.
    loop._draw_pending = False
    loop._next_draw_deadline = now - 1.0
    assert loop._should_draw(now) is False, "cadence must not force a frame on a clean tree"


def test_should_draw_cadence_throttles_pending_requests():
    """A pending request waits for the throttle deadline before drawing."""
    loop = ResponsiveEventLoop(_noop_draw, draw_fps=30.0)
    now = time.perf_counter()
    loop._draw_pending = True

    # Deadline in the future -> throttled, do not draw yet.
    loop._next_draw_deadline = now + 1.0
    assert loop._should_draw(now) is False

    # Deadline reached -> draw.
    loop._next_draw_deadline = now - 0.001
    assert loop._should_draw(now) is True


# ---------------------------------------------------------------------------
# _compute_sleep_timeout: idle must not spin at the cadence rate
# ---------------------------------------------------------------------------


class _StubClock:
    def __init__(self, sleep_time, dt=0.016):
        self._sleep_time = sleep_time
        self._dt = dt
        self.ticks = 0

    def get_sleep_time(self, sleep_idle):
        return self._sleep_time

    def update_time(self):
        return self._dt

    def call_scheduled_functions(self, dt):
        self.ticks += 1


def _timeout_with_clock(loop, sleep_time, now):
    loop.clock = _StubClock(sleep_time)  # type: ignore[assignment]
    return loop._compute_sleep_timeout(now)


def test_compute_sleep_timeout_idle_cadence_does_not_wake_for_draw():
    """A clean tree with a cadence must sleep on the clock, not the deadline."""
    loop = ResponsiveEventLoop(_noop_draw, draw_fps=30.0)
    now = time.perf_counter()
    loop._draw_pending = False
    loop._next_draw_deadline = now  # deadline reached, but nothing pending

    # No clock events pending -> sleep indefinitely (None), never at 30fps.
    assert _timeout_with_clock(loop, None, now) is None


def test_compute_sleep_timeout_pending_cadence_wakes_at_deadline():
    loop = ResponsiveEventLoop(_noop_draw, draw_fps=30.0)
    now = time.perf_counter()
    loop._draw_pending = True
    loop._next_draw_deadline = now + 0.02

    timeout = _timeout_with_clock(loop, None, now)
    assert timeout is not None
    assert abs(timeout - 0.02) < 1e-6


def test_compute_sleep_timeout_pending_on_demand_wakes_immediately():
    loop = ResponsiveEventLoop(_noop_draw, draw_fps=None)
    now = time.perf_counter()
    loop._draw_pending = True

    assert _timeout_with_clock(loop, None, now) == 0.0


def test_compute_sleep_timeout_idle_on_demand_uses_clock():
    """Idle on-demand loop wakes for scheduled clock events (e.g. animations)."""
    loop = ResponsiveEventLoop(_noop_draw, draw_fps=None)
    now = time.perf_counter()
    loop._draw_pending = False

    # A pending clock event (animation tick) must still wake the loop.
    assert _timeout_with_clock(loop, 0.005, now) == 0.005
    # Nothing scheduled -> sleep indefinitely.
    assert _timeout_with_clock(loop, None, now) is None


# ---------------------------------------------------------------------------
# idle(): the only draw point while the OS owns the loop (live resize)
# ---------------------------------------------------------------------------


def _idle_loop(draw_fps, sleep_time=None):
    recorded = []

    def _draw(dt: float) -> None:
        recorded.append(dt)

    loop = ResponsiveEventLoop(_draw, draw_fps=draw_fps)
    loop.clock = _StubClock(sleep_time)  # type: ignore[assignment]
    return loop, recorded


def test_idle_serves_a_pending_frame_once():
    loop, recorded = _idle_loop(draw_fps=None)
    loop._draw_pending = True

    loop.idle()
    loop.idle()

    assert len(recorded) == 1, "a pending frame is drawn once, then the tree is clean"
    assert loop._draw_pending is False


def test_idle_ticks_the_clock_without_a_pending_frame():
    loop, recorded = _idle_loop(draw_fps=None)
    loop._draw_pending = False

    loop.idle()

    assert recorded == []
    assert loop.clock.ticks == 1  # type: ignore[attr-defined]


def test_idle_keeps_the_cadence_throttle():
    loop, recorded = _idle_loop(draw_fps=30.0)
    now = time.perf_counter()
    loop._draw_pending = True
    loop._next_draw_deadline = now + 1.0

    timeout = loop.idle()

    assert recorded == [], "a throttled frame waits for its deadline even from idle()"
    assert loop._draw_pending is True
    assert timeout is not None and 0.0 < timeout <= 1.0, "the wake is the throttle deadline"


def test_idle_does_not_reenter_the_draw():
    recorded = []

    def _draw(dt: float) -> None:
        recorded.append(dt)
        loop.request_draw()
        loop.idle()  # a callback inside the frame pumps the loop again

    loop = ResponsiveEventLoop(_draw, draw_fps=None)
    loop.clock = _StubClock(None)  # type: ignore[assignment]
    loop._draw_pending = True

    loop.idle()

    assert len(recorded) == 1, "the nested idle() must not draw inside the frame"
    assert loop._draw_pending is True, "the nested request survives for the next iteration"


def test_idle_returns_the_loop_sleep_timeout():
    loop, _ = _idle_loop(draw_fps=None, sleep_time=None)
    loop._draw_pending = False
    assert loop.idle() is None

    loop, _ = _idle_loop(draw_fps=None, sleep_time=0.005)
    loop._draw_pending = False
    assert loop.idle() == 0.005


class _StubPlatformLoop:
    def __init__(self):
        self.timers = []

    def set_timer(self, func, interval):
        self.timers.append((func, interval))


def test_blocking_timer_draws_through_idle_and_rearms(monkeypatch):
    import pyglet

    platform_loop = _StubPlatformLoop()
    monkeypatch.setattr(pyglet.app, "platform_event_loop", platform_loop, raising=False)

    loop, recorded = _idle_loop(draw_fps=None, sleep_time=None)
    loop._draw_pending = True

    loop._blocking_timer()

    assert len(recorded) == 1, "the Win32 timer serves the frame through the draw gate"
    assert platform_loop.timers == [(loop._blocking_timer, None)], "re-armed with idle()'s timeout"
