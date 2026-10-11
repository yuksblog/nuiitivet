"""The pool of Pythons that run the ``@worker`` functions marked ``parallel``, and the rule that hands them calls.

One pool serves every such function on a target. What starts a Python differs,
a child process on the desktop and a Web Worker in the browser; the rule does
not: the number on a function is the ceiling on its concurrent calls, the pool
is everyone's, and ``warm`` is everyone's pre-start.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from typing import Callable, Optional, Protocol

from .codec import Json
from .function import result_of
from .writer import CallWriter


class Worker(Protocol):
    """One Python the pool hands calls to."""

    def post(self, call_id: int, name: str, values: dict[str, Json]) -> None:
        """Hand the worker one call: its number, the function's dotted name, the data arguments encoded."""

    def end(self) -> None:
        """End the worker. The pool has forgotten it already, so nothing it still sends is read."""


class Transport(Protocol):
    """Starts the Pythons of one target."""

    @property
    def machine_limit(self) -> int:
        """How many workers the machine runs at once; the pool never grows past it."""

    def start(self, slot: Slot) -> Worker:
        """Start one worker that reports to *slot*.

        Raises:
            Exception: If no worker can be started. The pool then fails every
                call until it is retired.
        """


class Slot:
    """The pool's record of one worker, and where the worker's events arrive.

    ``ready``, ``message`` and ``exit`` run on any thread; the pool handles
    them on the thread of its event loop.
    """

    __slots__ = ("worker", "is_ready", "call", "stale", "_pool")

    def __init__(self, pool: Pool) -> None:
        """Initialize Slot.

        Args:
            pool: The pool the worker belongs to.
        """
        self._pool = pool
        self.worker: Optional[Worker] = None
        self.is_ready = False
        self.call: Optional[_Call] = None
        # Marked by a retire while the worker runs a call: ended once it answers.
        self.stale = False

    def ready(self) -> None:
        """The worker has imported its modules and reads calls."""
        self._pool._deliver(_Event("ready", self, None))

    def message(self, text: str) -> None:
        """The worker sent one message of the call it runs, as JSON text."""
        self._pool._deliver(_Event("message", self, text))

    def exit(self, reason: str) -> None:
        """The worker ended on its own: before it was ready, or while it ran a call."""
        self._pool._deliver(_Event("exit", self, reason))


class _Event:
    __slots__ = ("kind", "slot", "payload")

    def __init__(self, kind: str, slot: Slot, payload: Optional[str]) -> None:
        self.kind = kind
        self.slot = slot
        self.payload = payload


class _Call:
    __slots__ = ("id", "name", "ceiling", "values", "writers", "future", "slot")

    def __init__(
        self,
        call_id: int,
        name: str,
        ceiling: int,
        values: dict[str, Json],
        writers: dict[str, CallWriter],
        future: asyncio.Future[Json],
    ) -> None:
        self.id = call_id
        self.name = name
        self.ceiling = ceiling
        self.values = values
        self.writers = writers
        self.future = future
        self.slot: Optional[Slot] = None


class Pool:
    """The workers of one target and the calls waiting for them.

    A call runs when fewer calls of its function are running than its ceiling
    and a worker is idle, or one can still be started; otherwise it waits, in
    order. A worker starts when a call needs it, up to the largest ceiling and
    the machine's limit. Cancelling a running call ends its worker. A worker
    that ends on its own fails its call with ``ConnectionError``; one that
    never becomes ready fails every call until the pool is retired.
    """

    def __init__(self, transport: Transport, *, ceiling: Callable[[], int], baseline: int = 0) -> None:
        """Initialize Pool.

        Args:
            transport: What starts a worker on this target.
            ceiling: The largest ``parallel`` among the functions that use the
                pool, read whenever the pool may grow.
            baseline: Workers kept running whether or not a call needs them:
                one in the browser, where the page starts one while loading;
                none on the desktop.
        """
        self._transport = transport
        self._ceiling = ceiling
        self._baseline = baseline
        self._kept = baseline
        self._slots: list[Slot] = []
        self._queue: deque[_Call] = deque()
        self._next_id = 0
        self._failure: Optional[str] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._events: deque[_Event] = deque()
        self._lock = threading.Lock()
        self._woken = False

    @property
    def size(self) -> int:
        """How many workers the pool holds, the starting ones included."""
        return len(self._slots)

    @property
    def limit(self) -> int:
        """How many workers the pool may hold now."""
        return max(1, min(max(self._ceiling(), self._baseline), self._transport.machine_limit))

    @property
    def failure(self) -> Optional[str]:
        """Why a worker could not start, while that failure stands."""
        return self._failure

    async def call(self, name: str, ceiling: int, values: dict[str, Json], writers: dict[str, CallWriter]) -> Json:
        """Run one call on a worker and return the encoded result.

        Args:
            name: The function's module and name, dotted.
            ceiling: How many calls of that function may run at once.
            values: The data arguments by name, encoded.
            writers: Where each ``WriteOnlyObservable`` parameter's writes go.

        Raises:
            ConnectionError: If the worker ended before it answered, or none
                could be started.
        """
        self._loop = asyncio.get_running_loop()
        self._drain()
        if self._failure is not None:
            raise ConnectionError(f"{name}: the worker did not start: {self._failure}")
        call = _Call(self._next_id, name, ceiling, values, writers, self._loop.create_future())
        self._next_id += 1
        self._queue.append(call)
        self._pump()
        try:
            return await call.future
        except asyncio.CancelledError:
            slot = call.slot
            if slot is not None:
                # A busy worker reads nothing until its function returns, so
                # the one way to stop the call is to end the worker.
                slot.call = None
                call.slot = None
                self._end(slot)
                self._pump()
            elif call in self._queue:
                self._queue.remove(call)
            raise

    def warm(self, count: int) -> None:
        """Keep *count* workers running from now on, starting the missing ones at once.

        Args:
            count: How many workers to keep, within the pool's limit.
        """
        self._kept = max(self._kept, count)
        self._drain()
        self._fill()

    def retire(self) -> None:
        """End every idle worker now and each busy one after its call; the next call starts a fresh one.

        Also forgets a start failure, so the next call tries again.
        """
        self._drain()
        self._failure = None
        self._kept = self._baseline
        for slot in list(self._slots):
            if slot.call is None:
                self._end(slot)
            else:
                slot.stale = True

    # -- events, from any thread ---------------------------------------------

    def _deliver(self, event: _Event) -> None:
        with self._lock:
            self._events.append(event)
            if self._woken or self._loop is None:
                return
            self._woken = True
        try:
            self._loop.call_soon_threadsafe(self._drain_and_pump)
        except RuntimeError:
            # The loop is closed: the app is exiting, or a test's loop is gone.
            with self._lock:
                self._woken = False

    def _drain_and_pump(self) -> None:
        self._drain()
        self._pump()

    def _drain(self) -> None:
        with self._lock:
            self._woken = False
        while True:
            with self._lock:
                if not self._events:
                    return
                event = self._events.popleft()
            self._handle(event)

    def _handle(self, event: _Event) -> None:
        slot = event.slot
        if slot not in self._slots:
            # Ended by the pool; whatever it still sent is not read.
            return
        if event.kind == "ready":
            slot.is_ready = True
        elif event.kind == "message":
            self._message(slot, event.payload or "")
        else:
            self._exit(slot, event.payload or "")

    def _message(self, slot: Slot, text: str) -> None:
        message = json.loads(text)
        call = slot.call
        if call is None or call.id != message["id"]:
            return
        if "w" in message:
            call.writers[message["w"]].receive(message["v"])
            return
        slot.call = None
        call.slot = None
        if not call.future.done():
            try:
                call.future.set_result(result_of(message))
            except Exception as error:
                call.future.set_exception(error)
        if slot.stale:
            self._end(slot)

    def _exit(self, slot: Slot, reason: str) -> None:
        self._slots.remove(slot)
        call, slot.call = slot.call, None
        if call is not None:
            call.slot = None
            if not call.future.done():
                call.future.set_exception(
                    ConnectionError(f"{call.name}: the worker stopped before answering: {reason}")
                )
        if not slot.is_ready:
            self._fail(reason)

    def _fail(self, reason: str) -> None:
        self._failure = reason
        while self._queue:
            call = self._queue.popleft()
            if not call.future.done():
                call.future.set_exception(ConnectionError(f"{call.name}: the worker did not start: {reason}"))

    # -- the rule, on the loop's thread ---------------------------------------

    def _pump(self) -> None:
        if self._failure is not None:
            self._fail(self._failure)
            return
        running: dict[str, int] = {}
        for slot in self._slots:
            if slot.call is not None:
                running[slot.call.name] = running.get(slot.call.name, 0) + 1
        wanted = 0
        for call in list(self._queue):
            if running.get(call.name, 0) >= call.ceiling:
                continue
            # Counted whether or not a worker is idle yet: a call that waits
            # for a worker to start still takes one of its function's places.
            running[call.name] = running.get(call.name, 0) + 1
            idle = self._idle()
            if idle is None:
                wanted += 1
                continue
            self._queue.remove(call)
            self._dispatch(call, idle)
        starting = sum(1 for slot in self._slots if not slot.is_ready and slot.call is None)
        while wanted > starting and len(self._slots) < self.limit and self._start():
            starting += 1
        self._fill()

    def _fill(self) -> None:
        while len(self._slots) < min(self._kept, self.limit) and self._start():
            pass

    def _idle(self) -> Optional[Slot]:
        for slot in self._slots:
            if slot.is_ready and slot.call is None and not slot.stale:
                return slot
        return None

    def _dispatch(self, call: _Call, slot: Slot) -> None:
        slot.call = call
        call.slot = slot
        assert slot.worker is not None
        slot.worker.post(call.id, call.name, call.values)

    def _start(self) -> bool:
        if self._failure is not None:
            return False
        slot = Slot(self)
        self._slots.append(slot)
        try:
            slot.worker = self._transport.start(slot)
        except Exception as error:
            self._slots.remove(slot)
            self._fail(str(error))
            return False
        return True

    def _end(self, slot: Slot) -> None:
        self._slots.remove(slot)
        slot.call = None
        if slot.worker is not None:
            slot.worker.end()


__all__ = ["Pool", "Slot", "Transport", "Worker"]
