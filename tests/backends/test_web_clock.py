"""Tests for the browser backend's clock, against a stand-in for the page's timers."""

from typing import Any

from nuiitivet.backends.web.clock import BrowserClock


class _Page:
    def __init__(self) -> None:
        self.now = 0.0
        self.frames = 0
        self.timers: dict[int, float] = {}
        self._next = 0
        self.clock = BrowserClock(self._request_frame, self._set_timeout, self._clear_timeout, now=lambda: self.now)

    def _request_frame(self) -> None:
        self.frames += 1

    def _set_timeout(self, ms: float) -> Any:
        self._next += 1
        self.timers[self._next] = ms
        return self._next

    def _clear_timeout(self, handle: Any) -> None:
        self.timers.pop(handle, None)


class _Target:
    def __init__(self) -> None:
        self.fired: list[float] = []

    def fire(self, dt: float) -> None:
        self.fired.append(dt)


def test_a_far_deadline_takes_a_timer_and_a_near_one_a_frame() -> None:
    page = _Page()
    target = _Target()

    page.clock.schedule_once(target.fire, 1.0)
    assert list(page.timers.values()) == [1000.0]
    assert page.frames == 0

    page.clock.schedule_once(target.fire, 0.01)
    assert page.timers == {}
    assert page.frames == 1


def test_once_fires_when_due_and_only_once() -> None:
    page = _Page()
    target = _Target()
    page.clock.schedule_once(target.fire, 1.0)

    page.now = 0.5
    page.clock.tick()
    assert target.fired == []

    page.now = 1.25
    page.clock.tick()
    page.clock.tick()
    assert target.fired == [1.25]


def test_interval_repeats_and_skips_missed_ticks() -> None:
    page = _Page()
    target = _Target()
    page.clock.schedule_interval(target.fire, 0.1)

    page.now = 0.1
    page.clock.tick()
    page.now = 0.55
    page.clock.tick()
    page.clock.tick()

    assert len(target.fired) == 2


def test_unschedule_matches_an_equal_bound_method() -> None:
    page = _Page()
    target = _Target()
    page.clock.schedule_interval(target.fire, 0.1)
    page.clock.unschedule(target.fire)

    page.now = 1.0
    page.clock.tick()
    assert target.fired == []


def test_a_callback_can_unschedule_another_due_one() -> None:
    page = _Page()
    second = _Target()

    def first(dt: float) -> None:
        page.clock.unschedule(second.fire)

    page.clock.schedule_once(first, 0.1)
    page.clock.schedule_once(second.fire, 0.1)
    page.now = 0.2
    page.clock.tick()

    assert second.fired == []
