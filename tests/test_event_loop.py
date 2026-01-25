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
