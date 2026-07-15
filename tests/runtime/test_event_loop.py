import time

from nuiitivet.backends.pyglet.event_loop import ResponsiveEventLoop


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

    window = _DummyWindow()
    loop = ResponsiveEventLoop(window, _draw, draw_fps=None)

    # Pretend a draw was requested by user code.
    loop._draw_pending = True

    loop._perform_draw(0.016, time.perf_counter())

    assert recorded, "Draw callback should be invoked"
    assert loop._draw_pending is True, "request_draw() inside callback must schedule another frame"


def _noop_draw(dt: float) -> None:
    return None


# ---------------------------------------------------------------------------
# _should_draw semantics
# ---------------------------------------------------------------------------


def test_should_draw_on_demand_only_when_pending():
    """With no cadence, draw exactly when a request is pending."""
    loop = ResponsiveEventLoop(_DummyWindow(), _noop_draw, draw_fps=None)
    now = time.perf_counter()

    loop._draw_pending = False
    assert loop._should_draw(now) is False

    loop._draw_pending = True
    assert loop._should_draw(now) is True


def test_should_draw_cadence_is_a_throttle_not_a_trigger():
    """With a cadence, a clean tree never draws even past the deadline."""
    loop = ResponsiveEventLoop(_DummyWindow(), _noop_draw, draw_fps=30.0)
    now = time.perf_counter()

    # Deadline already elapsed, but nothing is pending -> no frame.
    loop._draw_pending = False
    loop._next_draw_deadline = now - 1.0
    assert loop._should_draw(now) is False, "cadence must not force a frame on a clean tree"


def test_should_draw_cadence_throttles_pending_requests():
    """A pending request waits for the throttle deadline before drawing."""
    loop = ResponsiveEventLoop(_DummyWindow(), _noop_draw, draw_fps=30.0)
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
    def __init__(self, sleep_time):
        self._sleep_time = sleep_time

    def get_sleep_time(self, sleep_idle):
        return self._sleep_time


def _timeout_with_clock(loop, sleep_time, now):
    loop.clock = _StubClock(sleep_time)  # type: ignore[assignment]
    return loop._compute_sleep_timeout(now)


def test_compute_sleep_timeout_idle_cadence_does_not_wake_for_draw():
    """A clean tree with a cadence must sleep on the clock, not the deadline."""
    loop = ResponsiveEventLoop(_DummyWindow(), _noop_draw, draw_fps=30.0)
    now = time.perf_counter()
    loop._draw_pending = False
    loop._next_draw_deadline = now  # deadline reached, but nothing pending

    # No clock events pending -> sleep indefinitely (None), never at 30fps.
    assert _timeout_with_clock(loop, None, now) is None


def test_compute_sleep_timeout_pending_cadence_wakes_at_deadline():
    loop = ResponsiveEventLoop(_DummyWindow(), _noop_draw, draw_fps=30.0)
    now = time.perf_counter()
    loop._draw_pending = True
    loop._next_draw_deadline = now + 0.02

    timeout = _timeout_with_clock(loop, None, now)
    assert timeout is not None
    assert abs(timeout - 0.02) < 1e-6


def test_compute_sleep_timeout_pending_on_demand_wakes_immediately():
    loop = ResponsiveEventLoop(_DummyWindow(), _noop_draw, draw_fps=None)
    now = time.perf_counter()
    loop._draw_pending = True

    assert _timeout_with_clock(loop, None, now) == 0.0


def test_compute_sleep_timeout_idle_on_demand_uses_clock():
    """Idle on-demand loop wakes for scheduled clock events (e.g. animations)."""
    loop = ResponsiveEventLoop(_DummyWindow(), _noop_draw, draw_fps=None)
    now = time.perf_counter()
    loop._draw_pending = False

    # A pending clock event (animation tick) must still wake the loop.
    assert _timeout_with_clock(loop, 0.005, now) == 0.005
    # Nothing scheduled -> sleep indefinitely.
    assert _timeout_with_clock(loop, None, now) is None
