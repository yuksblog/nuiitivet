"""``switch_map`` with a coroutine function: a task per run, cancelled when superseded."""

from __future__ import annotations

import asyncio

import pytest

from nuiitivet.observable import Observable
from nuiitivet.observable import runtime


class ManualClock:
    def __init__(self) -> None:
        self.scheduled: list = []

    def schedule_once(self, fn, delay) -> None:
        self.scheduled.append(fn)

    def schedule_interval(self, fn, interval) -> None:
        raise NotImplementedError

    def unschedule(self, fn) -> None:
        self.scheduled = [each for each in self.scheduled if each != fn]

    def tick(self) -> None:
        due, self.scheduled = self.scheduled, []
        for fn in due:
            fn(0.0)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> ManualClock:
    manual = ManualClock()
    monkeypatch.setattr(runtime, "clock", manual)
    return manual


class GatedRuns:
    """A coroutine ``fn`` whose runs finish when the test releases them."""

    def __init__(self) -> None:
        self.release: dict[str, asyncio.Event] = {}
        self.cancelled: list[str] = []
        self.calls: list[str] = []

    async def __call__(self, value: str) -> str:
        self.calls.append(value)
        gate = self.release.setdefault(value, asyncio.Event())
        try:
            await gate.wait()
        except asyncio.CancelledError:
            self.cancelled.append(value)
            raise
        return f"result:{value}"

    def finish(self, value: str) -> None:
        self.release.setdefault(value, asyncio.Event()).set()


async def _settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_the_result_lands_through_the_clock(clock: ManualClock) -> None:
    source = Observable("")
    runs = GatedRuns()
    results = source.switch_map(runs, initial="<none>")

    source.value = "a"
    await _settle()
    assert runs.calls == ["a"]
    runs.finish("a")
    await _settle()
    assert results.value == "<none>"
    clock.tick()

    assert results.value == "result:a"


async def test_a_newer_value_cancels_the_run_in_flight(clock: ManualClock) -> None:
    source = Observable("")
    runs = GatedRuns()
    results = source.switch_map(runs, initial="<none>")

    source.value = "a"
    await _settle()
    source.value = "b"
    await _settle()
    assert runs.cancelled == ["a"]

    runs.finish("a")
    runs.finish("b")
    await _settle()
    clock.tick()

    assert results.value == "result:b"


async def test_dispose_cancels_the_run_in_flight(clock: ManualClock) -> None:
    source = Observable("")
    runs = GatedRuns()
    results = source.switch_map(runs, initial="<none>")
    source.value = "a"
    await _settle()

    results.dispose()
    await _settle()

    assert runs.cancelled == ["a"]


async def test_a_raising_run_publishes_nothing(clock: ManualClock) -> None:
    async def broken(value: str) -> str:
        raise RuntimeError("boom")

    source = Observable("")
    results = source.switch_map(broken, initial="<none>")

    source.value = "a"
    await _settle()
    clock.tick()

    assert results.value == "<none>"
