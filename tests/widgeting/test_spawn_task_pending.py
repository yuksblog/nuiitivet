"""``spawn_task`` before the loop runs: the work waits, then starts in order.

The main window is mounted when the App is constructed and the runner starts
the asyncio loop afterwards, so a root widget's async ``on_mount`` is spawned
with no loop to run it. It is kept, and started when the runner enters the loop.
"""

from __future__ import annotations

import asyncio
import logging
import warnings

import pytest

from nuiitivet.widgeting import callbacks
from nuiitivet.widgeting.callbacks import (
    PendingTask,
    drop_pending_tasks,
    invoke_event_handler,
    spawn_task,
    start_pending_tasks,
)


def _spawn(ran: list[str], name: str) -> PendingTask:
    async def _work() -> None:
        ran.append(name)

    task = spawn_task(_work(), owner_name=name)
    assert isinstance(task, PendingTask)
    return task


def test_work_waits_until_the_loop_starts_it_in_spawn_order() -> None:
    ran: list[str] = []
    first = _spawn(ran, "first")
    second = _spawn(ran, "second")
    assert ran == []
    assert first.done() is False

    async def _enter_loop() -> None:
        start_pending_tasks()
        await asyncio.sleep(0)

    asyncio.run(_enter_loop())

    assert ran == ["first", "second"]
    assert first.done() is True and second.done() is True
    assert callbacks._pending == []


def test_cancel_before_the_loop_closes_the_work(recwarn) -> None:
    ran: list[str] = []
    warnings.simplefilter("always")
    task = _spawn(ran, "cancelled")
    finished: list[PendingTask] = []
    task.add_done_callback(finished.append)

    assert task.cancel() is True
    assert task.done() is True
    assert task.cancel() is False
    assert finished == [task]
    assert callbacks._pending == []

    async def _enter_loop() -> None:
        start_pending_tasks()
        await asyncio.sleep(0)

    asyncio.run(_enter_loop())
    assert ran == []
    assert not [w for w in recwarn.list if issubclass(w.category, RuntimeWarning)]


def test_cancel_after_the_start_forwards_to_the_task() -> None:
    cancelled = []

    async def _poll() -> None:
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    task = spawn_task(_poll(), owner_name="poll")
    assert isinstance(task, PendingTask)

    async def _enter_loop() -> None:
        start_pending_tasks()
        await asyncio.sleep(0)
        assert task.done() is False
        assert task.cancel() is True
        await asyncio.sleep(0)

    asyncio.run(_enter_loop())
    assert cancelled == [True]
    assert task.done() is True


def test_drop_closes_the_work_and_logs_once(caplog, recwarn) -> None:
    ran: list[str] = []
    warnings.simplefilter("always")
    task = _spawn(ran, "dropped")

    with caplog.at_level(logging.WARNING, logger=callbacks.__name__):
        drop_pending_tasks()

    assert task.done() is True
    assert callbacks._pending == []
    assert "Async work from dropped was dropped: no event loop ran." in caplog.text
    assert not [w for w in recwarn.list if issubclass(w.category, RuntimeWarning)]


def test_a_handler_dropped_before_the_loop_leaves_no_unawaited_coroutine(recwarn) -> None:
    """The handler's own coroutine is nested inside the wrapper, and closed with it."""
    ran = []
    warnings.simplefilter("always")

    async def _handler() -> None:  # pragma: no cover - never started
        ran.append(True)

    task = invoke_event_handler(_handler, error_key="test", error_msg="test handler", owner_name="test")
    assert isinstance(task, PendingTask)

    task.cancel()

    assert ran == []
    assert not [w for w in recwarn.list if issubclass(w.category, RuntimeWarning)]


@pytest.mark.asyncio
async def test_a_running_loop_gets_a_task_at_once() -> None:
    async def _work() -> None:
        return None

    task = spawn_task(_work(), owner_name="live")
    assert isinstance(task, asyncio.Task)
    await task
