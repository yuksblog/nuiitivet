"""The pool's rule, against a transport the test drives: ceilings, growth, warm, cancel, exits and retire.

The transport never starts a Python. A fake worker records what the pool
posts, and the test plays the worker's side: ready, a write, the answer, an
exit.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Optional

import pytest

from nuiitivet.observable import Observable, runtime
from nuiitivet.remote.codec import codec_for
from nuiitivet.remote.pool import Pool, Slot
from nuiitivet.remote.writer import CallWriter
from tests.remote.test_server_function import ManualClock


class FakeWorker:
    def __init__(self, slot: Slot) -> None:
        self.slot = slot
        self.posted: list[tuple[int, str, dict[str, Any]]] = []
        self.ended = False

    def post(self, call_id: int, name: str, values: dict[str, Any]) -> None:
        self.posted.append((call_id, name, values))

    def end(self) -> None:
        self.ended = True

    # -- the worker's side, played by the test --

    def ready(self) -> None:
        self.slot.ready()

    def write(self, parameter: str, value: Any) -> None:
        self.slot.message(json.dumps({"id": self.posted[-1][0], "w": parameter, "v": value}))

    def answer(self, result: Any) -> None:
        self.slot.message(json.dumps({"id": self.posted[-1][0], "r": result}))

    def fail(self, message: str) -> None:
        error = {"type": "ValueError", "message": message, "builtin": True}
        self.slot.message(json.dumps({"id": self.posted[-1][0], "e": error}))

    def die(self, reason: str = "exit code 3") -> None:
        self.slot.exit(reason)


class FakeTransport:
    def __init__(self, machine_limit: int = 8) -> None:
        self.machine_limit = machine_limit
        self.workers: list[FakeWorker] = []
        self.refuse: Optional[str] = None

    def start(self, slot: Slot) -> FakeWorker:
        if self.refuse is not None:
            raise RuntimeError(self.refuse)
        worker = FakeWorker(slot)
        self.workers.append(worker)
        return worker


class Setup:
    def __init__(self, machine_limit: int = 8, baseline: int = 0) -> None:
        self.transport = FakeTransport(machine_limit)
        self.ceiling = 3
        self.pool = Pool(self.transport, ceiling=lambda: self.ceiling, baseline=baseline)

    def call(self, name: str = "a", ceiling: int = 1, **writers: CallWriter) -> "asyncio.Task[Any]":
        return asyncio.ensure_future(self.pool.call(name, ceiling, {"n": len(self.workers)}, writers))

    @property
    def workers(self) -> list[FakeWorker]:
        return self.transport.workers


async def settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


@pytest.fixture
def setup() -> Setup:
    return Setup()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> ManualClock:
    manual = ManualClock()
    monkeypatch.setattr(runtime, "clock", manual)
    return manual


# -- one call -----------------------------------------------------------------


async def test_a_call_starts_a_worker_and_is_posted_once_it_is_ready(setup: Setup) -> None:
    task = setup.call()
    await settle()
    [worker] = setup.workers
    assert worker.posted == []

    worker.ready()
    await settle()
    assert worker.posted == [(0, "a", {"n": 0})]

    worker.answer(5)
    assert await task == 5


async def test_an_error_message_raises_in_the_caller(setup: Setup) -> None:
    task = setup.call()
    await settle()
    setup.workers[0].ready()
    await settle()

    setup.workers[0].fail("bad input")
    with pytest.raises(ValueError, match="bad input"):
        await task


async def test_progress_reaches_the_writer_while_the_call_runs(setup: Setup, clock: ManualClock) -> None:
    progress = Observable(0.0)
    task = setup.call(progress=CallWriter(progress, codec_for(float)))
    await settle()
    setup.workers[0].ready()
    await settle()

    setup.workers[0].write("progress", 0.5)
    await settle()
    clock.tick()

    assert progress.value == 0.5
    assert not task.done()
    setup.workers[0].answer(1)
    await task


async def test_events_from_another_thread_reach_the_loop(setup: Setup) -> None:
    task = setup.call()
    await settle()
    [worker] = setup.workers

    threading.Thread(target=worker.ready).start()
    for _ in range(200):
        if worker.posted:
            break
        await asyncio.sleep(0.01)
    assert worker.posted
    threading.Thread(target=worker.answer, args=(7,)).start()

    assert await task == 7


# -- the ceiling and the pool -------------------------------------------------


async def test_calls_of_a_function_run_up_to_its_ceiling_and_the_next_waits(setup: Setup) -> None:
    tasks = [setup.call("a", ceiling=2) for _ in range(3)]
    await settle()
    assert len(setup.workers) == 2
    first, second = setup.workers
    first.ready()
    second.ready()
    await settle()
    assert len(first.posted) == 1 and len(second.posted) == 1

    first.answer(1)
    await settle()

    assert len(setup.workers) == 2
    assert len(first.posted) == 2
    second.answer(2)
    first.answer(3)
    assert [await task for task in tasks] == [1, 2, 3]


async def test_a_second_function_waits_when_the_pool_is_full(setup: Setup) -> None:
    a_tasks = [setup.call("a", ceiling=3) for _ in range(3)]
    await settle()
    for worker in setup.workers:
        worker.ready()
    await settle()
    assert len(setup.workers) == 3

    b_task = setup.call("b", ceiling=1)
    await settle()
    assert len(setup.workers) == 3
    assert all(len(worker.posted) == 1 for worker in setup.workers)

    setup.workers[1].answer(0)
    await settle()
    assert setup.workers[1].posted[-1][1] == "b"
    setup.workers[1].answer("b done")
    setup.workers[0].answer(0)
    setup.workers[2].answer(0)
    assert await b_task == "b done"
    await asyncio.gather(*a_tasks)


async def test_the_pool_never_grows_past_the_machine() -> None:
    setup = Setup(machine_limit=2)
    tasks = [setup.call("a", ceiling=3) for _ in range(3)]
    await settle()

    assert len(setup.workers) == 2
    assert setup.pool.limit == 2
    for task in tasks:
        task.cancel()


async def test_the_pool_holds_one_worker_when_no_function_is_numbered(setup: Setup) -> None:
    setup.ceiling = 0
    tasks = [setup.call("a", ceiling=1), setup.call("b", ceiling=1)]
    await settle()

    assert len(setup.workers) == 1
    for task in tasks:
        task.cancel()


async def test_warm_starts_workers_before_any_call_and_replaces_one_that_ends(setup: Setup) -> None:
    setup.pool.warm(2)
    assert len(setup.workers) == 2
    first, second = setup.workers
    first.ready()
    second.ready()

    task = setup.call()
    await settle()
    assert first.posted and not second.posted

    second.die()
    await settle()
    assert len(setup.workers) == 3
    first.answer(1)
    assert await task == 1


async def test_the_baseline_worker_is_replaced_as_soon_as_it_ends() -> None:
    setup = Setup(baseline=1)
    task = setup.call()
    await settle()
    setup.workers[0].ready()
    await settle()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert setup.workers[0].ended
    assert len(setup.workers) == 2
    assert setup.pool.size == 1


# -- cancel -------------------------------------------------------------------


async def test_cancelling_a_running_call_ends_its_worker(setup: Setup) -> None:
    task = setup.call()
    await settle()
    setup.workers[0].ready()
    await settle()

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert setup.workers[0].ended
    assert setup.pool.size == 0


async def test_cancelling_a_waiting_call_only_forgets_it(setup: Setup) -> None:
    first = setup.call("a", ceiling=1)
    second = setup.call("a", ceiling=1)
    await settle()
    [worker] = setup.workers
    worker.ready()
    await settle()

    second.cancel()
    with pytest.raises(asyncio.CancelledError):
        await second
    worker.answer(1)
    assert await first == 1
    await settle()

    assert not worker.ended
    assert len(worker.posted) == 1


async def test_a_message_from_an_ended_worker_is_ignored(setup: Setup) -> None:
    task = setup.call()
    await settle()
    old = setup.workers[0]
    old.ready()
    await settle()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    old.answer("late")
    old.die()
    await settle()
    next_task = setup.call()
    await settle()
    setup.workers[1].ready()
    await settle()
    setup.workers[1].answer("fresh")

    assert await next_task == "fresh"
    assert setup.pool.failure is None


# -- a worker that ends on its own --------------------------------------------


async def test_a_worker_that_dies_fails_its_call_and_the_next_call_starts_another(setup: Setup) -> None:
    task = setup.call()
    await settle()
    setup.workers[0].ready()
    await settle()

    setup.workers[0].die("exit code 3")
    with pytest.raises(ConnectionError, match="a: the worker stopped before answering: exit code 3"):
        await task

    next_task = setup.call()
    await settle()
    assert len(setup.workers) == 2
    setup.workers[1].ready()
    await settle()
    setup.workers[1].answer(1)
    assert await next_task == 1


async def test_a_worker_that_never_becomes_ready_fails_every_call_until_the_pool_is_retired(setup: Setup) -> None:
    task = setup.call()
    await settle()
    setup.workers[0].die("ImportError: no module named jobs")
    with pytest.raises(ConnectionError, match="a: the worker did not start: ImportError"):
        await task

    with pytest.raises(ConnectionError, match="did not start"):
        await setup.call()
    assert len(setup.workers) == 1

    setup.pool.retire()
    task = setup.call()
    await settle()
    assert len(setup.workers) == 2
    task.cancel()


async def test_a_start_that_raises_fails_the_call(setup: Setup) -> None:
    setup.transport.refuse = "no interpreter"

    with pytest.raises(ConnectionError, match="a: the worker did not start: no interpreter"):
        await setup.call()


# -- retire -------------------------------------------------------------------


async def test_retire_ends_idle_workers_now_and_busy_ones_after_their_call(setup: Setup) -> None:
    setup.pool.warm(2)
    busy, idle = setup.workers
    busy.ready()
    idle.ready()
    task = setup.call()
    await settle()
    assert busy.posted

    setup.pool.retire()
    assert idle.ended
    assert not busy.ended
    assert setup.pool.size == 1

    busy.answer(1)
    assert await task == 1
    assert busy.ended
    assert setup.pool.size == 0

    next_task = setup.call()
    await settle()
    assert len(setup.workers) == 3
    next_task.cancel()
