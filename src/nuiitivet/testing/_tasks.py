"""Tracking the async work a harness caused -- by registration, not inspection.

``idle()`` has to answer "is anything still running?". The obvious source is
``asyncio.all_tasks()``, and it is the wrong one: it returns every not-yet-done
task, including **the test's own coroutine**, which is by definition not done
while it is the one asking. Excluding ``current_task()`` fixes that instance but
not the shape of the problem -- an app that starts a polling task on mount owns
one that never completes -- and filtering a global set means guessing which tasks
count. Guessing high makes ``idle()`` time out; guessing low makes it return
against a half-settled tree, which is a flaky test rather than a loud one.

So the framework reports the tasks it creates
(:func:`nuiitivet.widgeting.callbacks.spawn_task`) and this registry records
them. Tests never see a task.
"""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional, Set


class TaskRegistry:
    """The tasks one harness caused, and whether they are still moving."""

    def __init__(self) -> None:
        self._tasks: Set["asyncio.Task[Any]"] = set()
        self._observed: Set["asyncio.Task[Any]"] = set()
        self._errors: List[BaseException] = []
        self._moves = 0

    # -- recording ---------------------------------------------------------

    def record(self, task: "asyncio.Task[Any]") -> None:
        """Note a task the framework just created. The observer hook's target."""
        self._tasks.add(task)
        self._moves += 1
        task.add_done_callback(self._on_done)

    def _on_done(self, task: "asyncio.Task[Any]") -> None:
        self._tasks.discard(task)
        self._observed.discard(task)
        self._moves += 1
        if task.cancelled():
            return
        # Retrieved here, always: an exception nobody reads is reported by
        # asyncio at collection time, outside any test and attached to no
        # traceback the author can use. Under a harness the handler wrapper
        # re-raises rather than containing, so this is where a failing handler
        # is caught and held for the next idle()/wait_for()/close().
        error = task.exception()
        if error is not None:
            self._errors.append(error)

    # -- what idle() asks --------------------------------------------------

    def in_flight(self) -> Set["asyncio.Task[Any]"]:
        """Recorded tasks that have not finished."""
        return {task for task in self._tasks if not task.done()}

    def take_progress(self) -> int:
        """Movement since the last call: tasks created plus tasks finished.

        ``idle()``'s **only** progress signal, deliberately not the clock's. A
        repeating timer -- a 60 Hz animation ticker, a spinner -- never stops
        firing, so counting clock callbacks would mean ``idle()`` could never
        return while anything on screen is animating.
        """
        moves, self._moves = self._moves, 0
        return moves

    def take_error(self) -> Optional[BaseException]:
        """The first unreported handler failure, or ``None``."""
        if not self._errors:
            return None
        return self._errors.pop(0)

    # -- what the teardown report asks -------------------------------------

    def mark_observed(self) -> None:
        """Record that the test waited and saw these tasks still pending.

        Called by ``idle()`` and ``wait_for()`` when they return. A task the
        test *watched* park -- a handler blocked on an open dialog -- is the app
        at rest and must not be reported at teardown; a task created afterwards
        and never waited on is the missing ``await app.idle()``.
        """
        self._observed = set(self._tasks)

    def unobserved_in_flight(self) -> List["asyncio.Task[Any]"]:
        """In-flight tasks created since the last :meth:`mark_observed`."""
        return [
            task
            for task in self._tasks
            if not task.done() and task not in self._observed
        ]


def describe_task(task: "asyncio.Task[Any]") -> str:
    """A one-line identity for a task, for a diagnostic message."""
    name = task.get_name()
    coro = task.get_coro()
    qualname = getattr(coro, "__qualname__", None) or getattr(coro, "__name__", None)
    frame = getattr(coro, "cr_frame", None)
    where = ""
    if frame is not None:
        where = f" at {frame.f_code.co_filename}:{frame.f_lineno}"
    return f"{name} <{qualname or coro!r}>{where}"


def untracked_tasks(known: Set["asyncio.Task[Any]"]) -> List["asyncio.Task[Any]"]:
    """Pending tasks on this loop that no registry knows about.

    Excludes the caller's own task, or the diagnostic accuses the test of being
    the thing it is waiting for. These are listed, never waited on: a handler
    that called ``asyncio.create_task()`` directly is outside the gate on
    purpose, and widening the gate to catch it brings back the guessing.
    """
    try:
        current = asyncio.current_task()
        pending = asyncio.all_tasks()
    except RuntimeError:  # pragma: no cover - no running loop
        return []
    return [
        task
        for task in pending
        if task is not current and task not in known and not task.done()
    ]


__all__ = ["TaskRegistry", "describe_task", "untracked_tasks"]
