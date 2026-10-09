from __future__ import annotations

import asyncio
import dataclasses
import inspect
import logging
from collections.abc import Awaitable, Coroutine
from typing import Any, Callable, Optional, Set, Union

from nuiitivet.common.logging_once import exception_once_per_exc, warning_once
from nuiitivet.observable import detach_batch

logger = logging.getLogger(__name__)

#: Observers notified of every task :func:`spawn_task` creates. Installed by the
#: test harness and empty in production; a *set*, because one test may drive more
#: than one harness and each keeps its own registry.
_task_observers: Set[Callable[["asyncio.Task[Any]"], None]] = set()


@dataclasses.dataclass(frozen=True, eq=False)
class ContainedError:
    """An exception the framework caught from user code and carried on past.

    Compared by identity, not by value: one containment produces one record,
    handed to every listening sink, and two harnesses in one test have to agree
    on whether *this* failure has been reported yet. Two separate failures that
    happen to look alike are two failures.

    Attributes:
        exc: The original exception, traceback intact.
        owner: Who raised it -- the widget's type name, or the handler's
            ``owner_name``.
        site: Which containment reported it, so a test's message can say what
            the framework was doing rather than only what failed.
    """

    exc: BaseException
    owner: str
    site: str


#: Sinks notified of every exception the framework contains on behalf of user
#: code. Installed by the test harness and empty in production, exactly like
#: :data:`_task_observers`; a *set*, for the same reason.
_error_sinks: Set[Callable[[ContainedError], None]] = set()


def report_contained(exc: BaseException, *, owner: str, site: str) -> None:
    """Tell any listening harness that user code raised and was contained.

    Called from *inside* the ``except`` blocks that already log and swallow, and
    it changes none of them: the exception stays caught, stays logged, and the
    frame still survives. Containment is correct in production -- one broken
    callback must not kill the frame -- and wrong in a test, where it lets an
    ``on_click`` that raised read as an ``on_click`` that worked. Production
    pays one iteration over an empty set.

    A sink must not raise; it is called mid-containment, where an exception
    would take out the very frame the containment exists to protect.
    """
    if not _error_sinks:
        return
    contained = ContainedError(exc, owner, site)
    for sink in tuple(_error_sinks):
        try:
            sink(contained)
        except Exception:
            exception_once_per_exc(
                logger,
                f"contained_error_sink_exc:{site}",
                "A contained-error sink raised; the report was dropped (site=%s)",
                site,
            )


class UnschedulableAsyncWork(BaseException):
    """Async work was requested with no event loop to run it on.

    Raised only while a test harness is observing (see :data:`_task_observers`).
    In production the same situation is logged and the work is dropped, because
    one unschedulable callback must not kill the frame -- but a test that carries
    on would be asserting against a handler that never ran, which is the failure
    this package exists to remove.

    **A BaseException on purpose.** Containment does not live at one layer: an
    event handler is invoked inside ``PointerInputNode._invoke_callback``, which
    runs inside a dispatch that ``runtime.app_events`` wraps in its own
    ``except Exception`` -- and there are dozens more such sites. Raising an
    ordinary exception here reaches none of them; it becomes one log line, once
    per process, which is the silence this is meant to break. Like
    ``KeyboardInterrupt`` and ``asyncio.CancelledError``, this is a signal to the
    runner rather than an error the app can handle, so it declines to be caught.
    ``pytest.raises`` accepts it unchanged.
    """


class PendingTask:
    """Async work spawned before the event loop runs.

    The runner starts it as a task when it enters the loop, in spawn order.
    Until then ``cancel()`` closes the coroutine, so the work never runs, and
    ``done()`` reports that. Once started, both forward to the task.
    """

    __slots__ = ("_coro", "_owner_name", "_task", "_closed", "_done_callbacks")

    def __init__(self, coro: "Coroutine[Any, Any, Any]", owner_name: str) -> None:
        self._coro = coro
        self._owner_name = owner_name
        self._task: Optional["asyncio.Task[Any]"] = None
        self._closed = False
        self._done_callbacks: list[Callable[["PendingTask"], None]] = []

    @property
    def owner_name(self) -> str:
        """Who spawned the work, as given to :func:`spawn_task`."""
        return self._owner_name

    def cancel(self) -> bool:
        """Cancel the work. Returns ``False`` when it had already finished."""
        if self._task is not None:
            return self._task.cancel()
        if self._closed:
            return False
        _pending.remove(self)
        self._close()
        return True

    def done(self) -> bool:
        """Whether the work has finished, or was cancelled before it started."""
        if self._task is not None:
            return self._task.done()
        return self._closed

    def add_done_callback(self, fn: Callable[["PendingTask"], None]) -> None:
        """Call *fn* with this handle when the work finishes or is cancelled.

        Called at once when it already has.
        """
        if self._task is not None:
            self._forward_done(self._task, fn)
        elif self._closed:
            fn(self)
        else:
            self._done_callbacks.append(fn)

    def _forward_done(self, task: "asyncio.Task[Any]", fn: Callable[["PendingTask"], None]) -> None:
        def _done(_task: "asyncio.Future[Any]") -> None:
            fn(self)

        task.add_done_callback(_done)

    def _start(self, loop: "asyncio.AbstractEventLoop") -> "asyncio.Task[Any]":
        task = loop.create_task(self._coro)
        self._task = task
        callbacks, self._done_callbacks = self._done_callbacks, []
        for fn in callbacks:
            self._forward_done(task, fn)
        return task

    def _close(self) -> None:
        self._closed = True
        self._coro.close()
        callbacks, self._done_callbacks = self._done_callbacks, []
        for fn in callbacks:
            fn(self)


#: Work spawned while no loop was running, in spawn order. The runner drains it
#: on entering the loop, or when it knows no loop will come.
_pending: list[PendingTask] = []


def spawn_task(
    coro: "Coroutine[Any, Any, Any]", *, owner_name: str = "<unknown>"
) -> "asyncio.Task[Any] | PendingTask":
    """Schedule framework-owned async work. The one place tasks are born.

    Every task the framework creates goes through here -- async event handlers,
    ``Navigator`` pops, overlay dismissals gated on ``will_pop``, back-button
    handling -- so that the no-loop policy is written down once and so a test
    harness can observe in-flight work by registration rather than by inspecting
    ``asyncio.all_tasks()`` and guessing which tasks are its own.

    Args:
        coro: The coroutine to run. Always consumed: scheduled, kept until the
            loop runs, or closed.
        owner_name: Who asked, for the diagnostic when the work is dropped.

    Returns:
        The scheduled task, or a :class:`PendingTask` when no event loop is
        running yet. Callers that need to cancel the work later (e.g. on
        unmount) should keep it.

    Raises:
        UnschedulableAsyncWork: No running loop, *and* a test harness is
            observing.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        if _task_observers:
            # Closed, or it is collected unawaited and Python blames framework
            # code for a warning the caller cannot see.
            coro.close()
            raise UnschedulableAsyncWork(
                f"async work from {owner_name} could not be scheduled: no event loop "
                "is running, so it never ran and never will. The test would be "
                "asserting on a handler that did nothing. Make the test 'async def' "
                "and 'await app.idle()' after the action -- the harness runs it on a "
                "real loop, exactly as production does."
            )
        pending = PendingTask(coro, owner_name)
        _pending.append(pending)
        return pending
    task = loop.create_task(coro)
    for observe in tuple(_task_observers):
        observe(task)
    return task


def start_pending_tasks() -> None:
    """Start the work spawned before the loop ran, in spawn order.

    Called by the runner from inside the running loop. Work spawned by the
    started tasks goes straight to the loop, so one pass empties the list.
    """
    loop = asyncio.get_running_loop()
    pending, _pending[:] = list(_pending), []
    for item in pending:
        task = item._start(loop)
        for observe in tuple(_task_observers):
            observe(task)


def drop_pending_tasks() -> None:
    """Close the work spawned before the loop ran, because no loop will run it.

    Logged once per owner.
    """
    pending, _pending[:] = list(_pending), []
    for item in pending:
        item._close()
        warning_once(
            logger,
            f"unschedulable_async_work:{item.owner_name}",
            "Async work from %s was dropped: no event loop ran.",
            item.owner_name,
        )


# ---------------------------------------------------------------------------
# Shared type aliases for user-facing event handler parameters.
# Each alias accepts both a synchronous and an async callable so that
# users can write either ``def on_click(): ...`` or
# ``async def on_click(): ...`` without mypy errors.
# ---------------------------------------------------------------------------

#: No-arg, fire-and-forget callback (e.g. on_click).
VoidCallback = Union[Callable[[], None], Callable[[], Awaitable[None]]]
#: Single ``bool`` argument callback (e.g. on_hover).
BoolCallback = Union[Callable[[bool], None], Callable[[bool], Awaitable[None]]]
#: Optional ``bool`` argument callback (e.g. on_change for tristate toggles).
OptionalBoolCallback = Union[
    Callable[[Optional[bool]], None],
    Callable[[Optional[bool]], Awaitable[None]],
]
#: Single ``str`` argument callback (e.g. on_change for text inputs).
StrCallback = Union[Callable[[str], None], Callable[[str], Awaitable[None]]]
#: Back-navigation guard callback — returns ``True`` to allow pop, ``False`` to cancel.
WillPopCallback = Union[Callable[[], bool], Callable[[], Awaitable[bool]]]


def invoke_event_handler(
    cb: Callable[..., Any],
    *args: Any,
    error_key: str,
    error_msg: str,
    owner_name: str = "<unknown>",
) -> "asyncio.Task[None] | PendingTask | None":
    """Invoke an event handler, scheduling it as a task if it is async.

    This helper handles:
    1. Synchronous execution.
    2. Asynchronous execution (scheduling as task).
    3. Detaching from the current batch context for async tasks.
    4. Error logging.

    Returns:
        The scheduled task when *cb* is async, a :class:`PendingTask` when it
        is async and the loop has not started yet, otherwise ``None``. Callers
        that need to cancel the handler later (e.g. on unmount) should keep it.

    Raises:
        UnschedulableAsyncWork: *cb* is async, no event loop is running, and a
            test harness is observing. Never in production.
    """
    # Only the synchronous call is contained here. Scheduling is deliberately
    # outside: UnschedulableAsyncWork is the harness's own signal, and catching
    # it below would turn it into a single log line -- once per process, since
    # exception_once_per_exc de-duplicates -- which is exactly the silence it
    # exists to break.
    try:
        result = cb(*args)
    except Exception as exc:
        exception_once_per_exc(
            logger,
            f"{error_key}_exc:{owner_name}",
            f"{error_msg} (owner=%s)",
            owner_name,
        )
        # The synchronous mirror of _run_handler's re-raise below. That one can
        # re-raise because the task is the harness's to await; this one is on
        # the frame's own call stack, where unwinding would abandon the rest of
        # the dispatch. So it is reported and the frame continues.
        report_contained(exc, owner=owner_name, site=error_key)
        return None

    if not inspect.isawaitable(result):
        return None

    wrapper = _run_handler(
        result, error_key=error_key, error_msg=error_msg, owner_name=owner_name
    )
    try:
        task = spawn_task(wrapper, owner_name=owner_name)
    except BaseException:
        # spawn_task closed the wrapper; the handler's own coroutine is nested
        # inside it and never started, so it needs closing on its own.
        _close_unstarted(result)
        raise
    if isinstance(task, PendingTask):
        # Same nesting: a wrapper closed before the loop ran leaves the
        # handler's coroutine unstarted. After a run the close is a no-op.
        task.add_done_callback(lambda _pending: _close_unstarted(result))
    return task


async def _run_handler(
    awaitable: Awaitable[Any],
    *,
    error_key: str,
    error_msg: str,
    owner_name: str,
) -> None:
    # Async tasks should not inherit the synchronous batch context because the
    # batch will likely exit before the task completes.
    detach_batch()
    try:
        await awaitable
    except asyncio.CancelledError:
        raise
    except Exception:
        exception_once_per_exc(
            logger,
            f"async_{error_key}_exc:{owner_name}",
            f"Async {error_msg} (owner=%s)",
            owner_name,
        )
        # Contained in production -- one broken handler must not kill the frame.
        # Under a test harness the containment is the bug: the task would
        # complete successfully and a handler that raised on line one would read
        # as a handler that worked. The harness retrieves it from the task.
        if _task_observers:
            raise


def _close_unstarted(awaitable: Awaitable[Any]) -> None:
    """Close *awaitable* if it is a coroutine that will now never run.

    Guarded, because ``inspect.isawaitable`` is also true for a ``Future`` and
    for anything with ``__await__``, neither of which has ``close()``.
    """
    if inspect.iscoroutine(awaitable):
        awaitable.close()
