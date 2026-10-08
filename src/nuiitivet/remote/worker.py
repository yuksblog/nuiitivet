"""``@worker``: a function the app awaits, that runs away from the UI and stays on the client."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import Any, Callable, Coroutine, Optional, ParamSpec, TypeVar

from .codec import Json
from .function import RemoteFunction, register, result_of
from .scope import is_server_only
from .writer import CallWriter

P = ParamSpec("P")
R = TypeVar("R")


class WorkerFunction(RemoteFunction[P, R]):
    """One ``@worker`` function: on the web, its call runs on the page's Web Worker."""

    mark = "worker"

    def _check_module(self) -> None:
        if is_server_only(self.fn.__module__):
            raise self._error(
                f"module {self.fn.__module__} is server-only; a worker function runs in the browser, "
                "so its module must not call server_only()"
            )

    async def _call_on_web(self, values: dict[str, Json], writers: dict[str, CallWriter]) -> Json:
        return await _pool().call(self.name, values, writers)


class _Call:
    __slots__ = ("id", "name", "values", "writers", "future")

    def __init__(
        self,
        call_id: int,
        name: str,
        values: dict[str, Json],
        writers: dict[str, CallWriter],
        future: asyncio.Future[Json],
    ) -> None:
        self.id = call_id
        self.name = name
        self.values = values
        self.writers = writers
        self.future = future


class _Pool:
    """The page's worker and the calls waiting for it. The worker runs one call at a time.

    A call is handed to the worker only when the previous one has answered,
    so a queued call is cancelled by forgetting it. The running call is the
    one the worker cannot be told about: a busy worker reads no message, so
    cancelling it ends the worker, and the page starts a replacement.
    """

    def __init__(self) -> None:
        import js
        from pyodide.ffi import create_proxy

        host = getattr(js, "NV_WORKERS", None)
        if host is None:
            raise RuntimeError(
                "the page started no worker; a @worker function lives in a module under the app's directory"
            )
        self._host = host
        self._queue: deque[_Call] = deque()
        self._running: Optional[_Call] = None
        self._next_id = 0
        failure = host.failure
        self._failure: Optional[str] = failure if isinstance(failure, str) else None
        host.onReady = create_proxy(self._ready)
        host.onMessage = create_proxy(self._message)
        host.onExit = create_proxy(self._exit)

    async def call(self, name: str, values: dict[str, Json], writers: dict[str, CallWriter]) -> Json:
        if self._failure is not None:
            raise ConnectionError(f"{name}: the worker did not start: {self._failure}")
        call = _Call(self._next_id, name, values, writers, asyncio.get_running_loop().create_future())
        self._next_id += 1
        self._queue.append(call)
        self._pump()
        try:
            return await call.future
        except asyncio.CancelledError:
            if self._running is call:
                self._running = None
                self._host.restart()
            else:
                self._queue.remove(call)
            raise

    def _pump(self) -> None:
        if self._running is None and self._queue and self._host.ready:
            self._running = call = self._queue.popleft()
            self._host.post(call.id, call.name, json.dumps(call.values))

    def _ready(self) -> None:
        self._pump()

    def _message(self, text: str) -> None:
        message = json.loads(text)
        call = self._running
        if call is None or call.id != message["id"]:
            return
        if "w" in message:
            call.writers[message["w"]].receive(message["v"])
            return
        self._running = None
        if not call.future.done():
            try:
                call.future.set_result(result_of(message))
            except Exception as error:
                call.future.set_exception(error)
        self._pump()

    def _exit(self, reason: str, was_ready: bool) -> None:
        """The worker ended on its own: before it answered ready, or while a call ran."""
        running, self._running = self._running, None
        if running is not None and not running.future.done():
            error = ConnectionError(f"{running.name}: the worker stopped before answering: {reason}")
            running.future.set_exception(error)
        if was_ready:
            # The page starts a replacement, and the queue goes on when it is ready.
            return
        self._failure = reason
        while self._queue:
            call = self._queue.popleft()
            if not call.future.done():
                call.future.set_exception(ConnectionError(f"{call.name}: the worker did not start: {reason}"))


_the_pool: Optional[_Pool] = None


def _pool() -> _Pool:
    global _the_pool
    if _the_pool is None:
        _the_pool = _Pool()
    return _the_pool


def worker(fn: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    """Mark a function as one that runs on a Web Worker when the app is on the web.

    The app awaits it the same way on both targets::

        @nv.worker
        def count_primes(limit: int) -> int: ...

        count = await count_primes(100_000)

    On the desktop it runs on a worker thread. Either way it shares nothing
    with its caller: arguments and the result are copied, and may only be of
    the types a :func:`server` function accepts. ``WriteOnlyObservable[T]``
    and ``CancelToken`` parameters work as they do there.

    The function's module ships to the browser with the rest of the app, and
    the page's worker imports it when the page loads. The page runs one
    worker; a call made while another runs waits for it. Cancelling the
    awaiting task of a running call ends the worker, and the next call waits
    for its replacement to start.

    An exception reaches the caller: a built-in one as itself, any other as
    :class:`RemoteError`. ``ConnectionError`` says the worker stopped before
    it answered.

    Args:
        fn: A plain ``def`` at the top level of a module the browser gets,
            with every parameter and the return type annotated.

    Raises:
        TypeError: If *fn* breaks one of these rules.
    """
    return register(WorkerFunction(fn))


__all__ = ["WorkerFunction", "worker"]
