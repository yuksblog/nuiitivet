"""``@worker(process=True)`` on the desktop: the calls run in child processes, through the real transport.

The functions live in ``process_jobs``, which each child imports by name. A
function that must wait does so on a file the test creates, so the test
decides when it goes on.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import os
from pathlib import Path
from typing import Callable, Iterator

import pytest

from nuiitivet.observable import Observable, runtime
from nuiitivet.remote import RemoteError
from nuiitivet.remote.function import lookup
from nuiitivet.remote.worker import WorkerFunction, process_pool, retire_pool, warm_pool, worker
from tests.remote import process_jobs as jobs
from tests.remote.models import Order
from tests.remote.test_server_function import ManualClock

_TIMEOUT = 30.0


@pytest.fixture(autouse=True, scope="module")
def _no_children_left() -> Iterator[None]:
    yield
    retire_pool()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> ManualClock:
    manual = ManualClock()
    monkeypatch.setattr(runtime, "clock", manual)
    return manual


async def until(condition: Callable[[], bool], clock: ManualClock | None = None) -> None:
    deadline = asyncio.get_running_loop().time() + _TIMEOUT
    while not condition():
        assert asyncio.get_running_loop().time() < deadline, "the condition never held"
        if clock is not None:
            clock.tick()
        await asyncio.sleep(0.01)


def child_pids() -> set[int]:
    return {child.pid for child in multiprocessing.active_children() if child.pid is not None}


# -- the call -----------------------------------------------------------------


async def test_a_function_marked_process_runs_in_another_process_and_a_bare_one_on_a_thread() -> None:
    assert await jobs.pid() != os.getpid()
    assert await jobs.pid_alone() != os.getpid()
    assert await jobs.pid_on_thread() == os.getpid()


async def test_arguments_and_result_are_copies() -> None:
    sent = Order(1, ["a"])

    returned = await jobs.keep(sent)

    assert sent.items == ["a"]
    assert returned == Order(1, ["a", "added in the worker"])


async def test_a_builtin_exception_reaches_the_caller_as_itself() -> None:
    with pytest.raises(ValueError, match="bad input"):
        await jobs.fail_builtin()


async def test_any_other_exception_reaches_the_caller_as_remote_error() -> None:
    with pytest.raises(RemoteError) as caught:
        await jobs.fail_custom(7)

    assert (caught.value.type_name, caught.value.message) == ("NotFound", "no order 7")


async def test_progress_arrives_while_the_call_runs(clock: ManualClock, tmp_path: Path) -> None:
    progress = Observable(0.0)
    task = asyncio.ensure_future(jobs.report(str(tmp_path / "go"), progress))

    await until(lambda: progress.value == 0.5, clock)

    assert not task.done()
    (tmp_path / "go").touch()
    assert await task != os.getpid()
    clock.tick()
    assert progress.value == 1.0


# -- the ceiling --------------------------------------------------------------


async def test_two_calls_run_at_once_in_two_processes_and_the_third_waits(clock: ManualClock, tmp_path: Path) -> None:
    progress = [Observable(0.0) for _ in range(3)]
    gates = [tmp_path / f"go{index}" for index in range(3)]
    tasks = [asyncio.ensure_future(jobs.report(str(gate), each)) for gate, each in zip(gates, progress)]

    await until(lambda: progress[0].value == 0.5 and progress[1].value == 0.5, clock)
    await asyncio.sleep(0.2)
    clock.tick()
    assert progress[2].value == 0.0
    assert process_pool().size == 2

    gates[0].touch()
    first = await tasks[0]
    await until(lambda: progress[2].value == 0.5, clock)
    gates[1].touch()
    gates[2].touch()
    second, third = await asyncio.gather(tasks[1], tasks[2])

    assert first != second
    assert third in (first, second)


async def test_warm_starts_the_processes_with_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    retire_pool()
    function = lookup(f"{jobs.__name__}.pid")
    assert isinstance(function, WorkerFunction)
    monkeypatch.setattr(function, "warm", True)

    warm_pool()

    assert process_pool().size == 2
    assert await jobs.pid() != os.getpid()


# -- cancel, a death, and retire ----------------------------------------------


async def test_cancelling_ends_the_process_of_a_function_that_never_polls_its_token(clock: ManualClock) -> None:
    started = Observable(0)
    task = asyncio.ensure_future(jobs.forever(started))
    await until(lambda: started.value != 0, clock)
    victim = started.value

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await until(lambda: victim not in child_pids())

    assert await jobs.pid() != victim


async def test_a_process_that_dies_fails_its_call_and_the_next_call_works() -> None:
    with pytest.raises(ConnectionError, match=r"crash: the worker stopped before answering: exit code 3"):
        await jobs.crash()

    assert await jobs.pid() != os.getpid()


async def test_retire_ends_the_processes_and_the_next_call_starts_a_fresh_one() -> None:
    before = await jobs.pid()

    retire_pool()
    await until(lambda: before not in child_pids())

    assert await jobs.pid() != before


# -- the mark -----------------------------------------------------------------


def plain() -> None:
    pass


def test_the_mark_takes_its_forms() -> None:
    assert isinstance(lookup(f"{jobs.__name__}.pid_on_thread"), WorkerFunction)
    numbered = lookup(f"{jobs.__name__}.pid")
    assert isinstance(numbered, WorkerFunction)
    assert (numbered.parallel, numbered.process, numbered.warm, numbered.ceiling) == (2, True, False, 2)
    alone = lookup(f"{jobs.__name__}.pid_alone")
    assert isinstance(alone, WorkerFunction)
    assert (alone.parallel, alone.process, alone.ceiling) == (None, True, 1)

    worker()(plain)
    bare = lookup(f"{__name__}.plain")
    assert isinstance(bare, WorkerFunction)
    assert (bare.parallel, bare.process, bare.warm, bare.ceiling) == (None, False, False, 1)


def test_parallel_is_a_positive_int_and_warm_needs_it() -> None:
    with pytest.raises(TypeError, match=r"@worker .*plain: parallel is how many calls may run at once"):
        worker(parallel=0)(plain)
    with pytest.raises(TypeError, match="parallel is how many calls"):
        worker(parallel=True)(plain)  # type: ignore[call-overload]
    with pytest.raises(TypeError, match=r"@worker .*plain: warm starts the workers that parallel allows"):
        worker(warm=True)(plain)
