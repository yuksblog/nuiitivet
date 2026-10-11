"""``@worker``: a function the app awaits, that runs away from the UI and stays on the client."""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine, Optional, ParamSpec, Protocol, TypeVar, overload

from nuiitivet.common.target import is_web
from nuiitivet.observable.switched import CancelToken

from .codec import Json
from .function import RemoteFunction, register, registered
from .pool import Pool, Slot
from .scope import is_server_only
from .writer import CallWriter

P = ParamSpec("P")
R = TypeVar("R")


class WorkerFunction(RemoteFunction[P, R]):
    """One ``@worker`` function: a Web Worker runs its call on the web; a thread or a child process on the desktop."""

    mark = "worker"

    def __init__(
        self, fn: Callable[P, R], *, parallel: Optional[int] = None, process: bool = False, warm: bool = False
    ) -> None:
        """Initialize WorkerFunction.

        Args:
            fn: The function as the app wrote it.
            parallel: How many calls of it may run at once. ``None`` leaves
                a thread on the desktop unbounded and gives a child process,
                or the page's pool, one call at a time.
            process: Whether the desktop runs its calls in child processes
                instead of threads. The browser ignores it.
            warm: Whether the Pythons *parallel* allows start with the app.

        Raises:
            TypeError: If *fn* breaks a rule of the mark, or an option is not
                as described.
        """
        super().__init__(fn)
        if parallel is not None and (type(parallel) is not int or parallel < 1):
            raise self._error("parallel is how many calls may run at once: an int of 1 or more")
        if warm and parallel is None:
            raise self._error("warm starts the workers that parallel allows; give parallel too")
        self.parallel = parallel
        self.process = process
        self.warm = warm

    @property
    def ceiling(self) -> int:
        """How many calls may run at once on a pool: ``parallel``, or one."""
        return self.parallel or 1

    def _check_module(self) -> None:
        if is_server_only(self.fn.__module__):
            raise self._error(
                f"module {self.fn.__module__} is server-only; a worker function runs in the browser, "
                "so its module must not call server_only()"
            )

    async def _call_on_web(self, values: dict[str, Json], writers: dict[str, CallWriter]) -> Json:
        return await web_pool().call(self.name, self.ceiling, values, writers)

    async def _call_on_desktop(
        self, values: dict[str, Json], writers: dict[str, CallWriter], token: CancelToken
    ) -> Json:
        if self.process:
            return await process_pool().call(self.name, self.ceiling, values, writers)
        if self.parallel is None:
            return await super()._call_on_desktop(values, writers, token)
        return await thread_pool().call(self.name, self.ceiling, values, writers)


# -- the pools ------------------------------------------------------------------


class _WebTransport:
    """The page's Web Workers, through the host ``workers.mjs`` installs as ``NV_WORKERS``."""

    def __init__(self) -> None:
        import js

        host = getattr(js, "NV_WORKERS", None)
        if host is None:
            raise RuntimeError(
                "the page started no worker; a @worker function lives in a module under the app's directory"
            )
        self._host = host

    @property
    def machine_limit(self) -> int:
        return int(self._host.limit)

    def start(self, slot: Slot) -> _WebWorker:
        from pyodide.ffi import create_proxy

        handle = self._host.start()
        handle.onReady = create_proxy(slot.ready)
        handle.onMessage = create_proxy(slot.message)
        handle.onExit = create_proxy(slot.exit)
        # The worker the page booted while loading may have answered already.
        if handle.ready:
            slot.ready()
        elif isinstance(handle.failure, str):
            slot.exit(handle.failure)
        return _WebWorker(handle)


class _WebWorker:
    __slots__ = ("_handle",)

    def __init__(self, handle: Any) -> None:
        self._handle = handle

    def post(self, call_id: int, name: str, values: dict[str, Json]) -> None:
        self._handle.post(call_id, name, json.dumps(values))

    def end(self) -> None:
        self._handle.end()


_web_pool: Optional[Pool] = None
_process_pool: Optional[Pool] = None
_thread_pool: Optional[Pool] = None


def _worker_functions() -> list[WorkerFunction[Any, Any]]:
    return [function for function in registered() if isinstance(function, WorkerFunction)]


def _in_processes() -> list[WorkerFunction[Any, Any]]:
    return [function for function in _worker_functions() if function.process]


def _on_capped_threads() -> list[WorkerFunction[Any, Any]]:
    return [function for function in _worker_functions() if function.parallel is not None and not function.process]


def _largest_ceiling(functions: Callable[[], list[WorkerFunction[Any, Any]]]) -> Callable[[], int]:
    return lambda: max((function.parallel or 0 for function in functions()), default=0)


def web_pool() -> Pool:
    """The page's pool of Web Workers, created at its first use. Every worker function uses it."""
    global _web_pool
    if _web_pool is None:
        _web_pool = Pool(_WebTransport(), ceiling=_largest_ceiling(_worker_functions), baseline=1)
    return _web_pool


def process_pool() -> Pool:
    """The desktop's pool of child processes, created at its first use. The functions marked ``process`` use it."""
    global _process_pool
    if _process_pool is None:
        from .process import ProcessTransport

        _process_pool = Pool(ProcessTransport(_modules), ceiling=_largest_ceiling(_in_processes), baseline=0)
    return _process_pool


def thread_pool() -> Pool:
    """The desktop's pool of threads, created at its first use. The functions marked ``parallel`` alone use it."""
    global _thread_pool
    if _thread_pool is None:
        from .threads import ThreadTransport

        _thread_pool = Pool(ThreadTransport(), ceiling=_largest_ceiling(_on_capped_threads), baseline=0)
    return _thread_pool


def _modules() -> list[str]:
    """The modules a child process imports: those of the functions marked ``process``, the entry script aside."""
    return sorted({function.fn.__module__ for function in _in_processes()} - {"__main__"})


def warm_pool() -> None:
    """Start the Pythons the functions marked ``warm`` ask for. ``App.run()`` calls it.

    In the browser every such function warms the page's workers; on the
    desktop only one marked ``process`` has Pythons to warm.
    """
    functions = _worker_functions() if is_web() else _in_processes()
    count = max((function.parallel or 0 for function in functions if function.warm), default=0)
    if count:
        (web_pool() if is_web() else process_pool()).warm(count)


def retire_pool() -> None:
    """End the desktop pools' workers, an idle one now and a busy one after its call; the next call starts afresh."""
    for pool in (_process_pool, _thread_pool):
        if pool is not None:
            pool.retire()


# -- the mark -------------------------------------------------------------------


class _Mark(Protocol):
    """What ``worker(...)`` with options returns: the decorator itself."""

    def __call__(self, fn: Callable[P, R], /) -> Callable[P, Coroutine[Any, Any, R]]: ...


@overload
def worker(fn: Callable[P, R], /) -> Callable[P, Coroutine[Any, Any, R]]: ...


@overload
def worker(*, parallel: Optional[int] = None, process: bool = False, warm: bool = False) -> _Mark: ...


def worker(
    fn: Optional[Callable[P, R]] = None,
    /,
    *,
    parallel: Optional[int] = None,
    process: bool = False,
    warm: bool = False,
) -> Any:
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
    the worker the page starts while loading imports it. Without ``parallel``
    the page runs the calls one at a time on that worker. Cancelling the
    awaiting task of a running call ends the worker, and the next call waits
    for its replacement to start.

    ``parallel`` is the ceiling on the calls that run at once, and
    ``process`` moves the desktop's calls from threads to child processes::

        @nv.worker(parallel=3)                # three threads at most; three Web Workers
        def count_primes(limit: int) -> int: ...

        @nv.worker(process=True)              # one child process, one call at a time
        def count_primes(limit: int) -> int: ...

        @nv.worker(parallel=3, process=True)  # three child processes; three Web Workers

    The number is the function's ceiling, the pool of Pythons is shared by
    every such function, and ``warm=True`` starts that many with the app
    instead of at the first call that needs them. Cancelling a running call
    in a child process or a Web Worker ends it; on a thread it sets the
    function's ``CancelToken``, as without a number.

    An exception reaches the caller: a built-in one as itself, any other as
    :class:`RemoteError`. ``ConnectionError`` says the worker stopped before
    it answered.

    Args:
        fn: A plain ``def`` at the top level of a module the browser gets,
            with every parameter and the return type annotated.
        parallel: How many calls may run at once; an int of 1 or more.
            Without it a thread is unbounded and a child process, or the
            page's worker, takes one call at a time.
        process: Run the desktop's calls in child processes instead of
            threads. The browser ignores it.
        warm: Start the Pythons *parallel* allows when the app starts.

    Raises:
        TypeError: If *fn* breaks one of these rules.
    """

    def mark(fn: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
        return register(WorkerFunction(fn, parallel=parallel, process=process, warm=warm))

    return mark if fn is None else mark(fn)


__all__ = ["WorkerFunction", "process_pool", "retire_pool", "thread_pool", "warm_pool", "web_pool", "worker"]
