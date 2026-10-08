"""``@server`` on the desktop: the call, its copies, progress, cancellation and errors.

The functions that block wait on an event the test sets, so a test decides the
order of the function's steps and the caller's and never sleeps.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Callable

import pytest

from dataclasses import dataclass

from nuiitivet.observable import Observable, runtime
from nuiitivet.observable.switched import CancelToken
from nuiitivet.remote import RemoteError, WriteOnlyObservable, server, server_only
from nuiitivet.remote.scope import is_server_only
from tests.remote.models import Order

server_only()

_TIMEOUT = 5.0


class ManualClock:
    """Holds scheduled callbacks until the test runs them, as a frame would."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._scheduled: list[Callable[[float], None]] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        with self._lock:
            self._scheduled.append(fn)

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        raise NotImplementedError

    def unschedule(self, fn: Callable[[float], None]) -> None:
        with self._lock:
            self._scheduled = [each for each in self._scheduled if each != fn]

    def tick(self) -> None:
        with self._lock:
            due, self._scheduled = self._scheduled, []
        for fn in due:
            fn(0.0)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> ManualClock:
    manual = ManualClock()
    monkeypatch.setattr(runtime, "clock", manual)
    return manual


class OrderNotFound(Exception):
    pass


@dataclass
class ServerSideOnly:
    id: int


class Gate:
    """Two events: the function reports where it is, the test lets it go on."""

    def __init__(self) -> None:
        self.reached = threading.Event()
        self.release = threading.Event()

    def wait_here(self) -> None:
        self.reached.set()
        assert self.release.wait(_TIMEOUT)

    async def until_reached(self) -> None:
        assert await asyncio.to_thread(self.reached.wait, _TIMEOUT)


_gate = Gate()
_seen: dict[str, Any] = {}


@pytest.fixture(autouse=True)
def _fresh_gate() -> None:
    global _gate
    _gate = Gate()
    _seen.clear()


@server
def add(a: int, b: int = 10) -> int:
    _seen["thread"] = threading.current_thread()
    return a + b


@server
def keep(order: Order) -> Order:
    _seen["order"] = order
    order.items.append("added on the server")
    return order


@server
def fail_builtin() -> None:
    raise ValueError("bad input")


@server
def fail_custom(order_id: int) -> None:
    raise OrderNotFound(f"no order {order_id}")


@server
def wrong_result() -> int:
    return "text"  # type: ignore[return-value]


@server
def report(progress: WriteOnlyObservable[float], status: WriteOnlyObservable[str]) -> int:
    progress.value = 0.25
    status.value = "reading"
    progress.value = 0.5
    _gate.wait_here()
    progress.value = 1.0
    status.value = "done"
    return 3


@server
def read_back(progress: WriteOnlyObservable[float]) -> None:
    _ = progress.value


@server
def write_wrong(progress: WriteOnlyObservable[float]) -> None:
    progress.value = "half"  # type: ignore[assignment]


@server
def fail_after_progress(progress: WriteOnlyObservable[float]) -> None:
    progress.value = 0.9
    raise ValueError("late")


@server
def cancellable(progress: WriteOnlyObservable[float], cancel: CancelToken = CancelToken()) -> None:
    _seen["token"] = cancel
    progress.value = 0.1
    _gate.wait_here()
    _seen["cancelled"] = cancel.cancelled
    progress.value = 0.9
    _seen["finished"] = True


# -- the call -----------------------------------------------------------------


async def test_the_call_returns_the_result() -> None:
    assert await add(1, 2) == 3
    assert await add(1) == 11
    assert await add(a=1, b=5) == 6


async def test_the_function_runs_off_the_calling_thread() -> None:
    await add(1, 2)

    assert _seen["thread"] is not threading.current_thread()


async def test_arguments_and_result_are_copies() -> None:
    sent = Order(1, ["a"])

    returned = await keep(sent)

    assert _seen["order"] is not sent
    assert sent.items == ["a"]
    assert returned == Order(1, ["a", "added on the server"])
    assert returned is not _seen["order"]


async def test_an_argument_of_another_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="a: expected int, got str"):
        await add("1", 2)  # type: ignore[arg-type]


async def test_a_result_of_another_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="return value: expected int, got str"):
        await wrong_result()


# -- errors -------------------------------------------------------------------


async def test_a_builtin_exception_reaches_the_caller_as_itself() -> None:
    with pytest.raises(ValueError, match="bad input"):
        await fail_builtin()


async def test_any_other_exception_reaches_the_caller_as_server_error() -> None:
    with pytest.raises(RemoteError) as caught:
        await fail_custom(7)

    assert caught.value.type_name == "OrderNotFound"
    assert caught.value.message == "no order 7"


# -- progress -----------------------------------------------------------------


async def test_progress_arrives_while_the_call_is_running(clock: ManualClock) -> None:
    progress, status = Observable(0.0), Observable("")
    task = asyncio.ensure_future(report(progress, status))

    await _gate.until_reached()
    assert progress.value == 0.0
    clock.tick()

    # Two writes happened before the frame; the Observable takes the newest.
    assert progress.value == 0.5
    assert status.value == "reading"
    assert not task.done()
    _gate.release.set()
    assert await task == 3


async def test_the_last_write_has_landed_when_the_call_returns(clock: ManualClock) -> None:
    progress, status = Observable(0.0), Observable("")
    _gate.release.set()

    await report(progress, status)

    assert progress.value == 1.0
    assert status.value == "done"


async def test_a_write_before_an_exception_has_landed_when_it_is_raised(clock: ManualClock) -> None:
    progress = Observable(0.0)

    with pytest.raises(ValueError):
        await fail_after_progress(progress)

    assert progress.value == 0.9


async def test_the_function_cannot_read_the_observable() -> None:
    with pytest.raises(AttributeError, match="cannot be read"):
        await read_back(Observable(0.0))


async def test_a_write_of_another_type_fails_in_the_function() -> None:
    with pytest.raises(TypeError, match="expected float, got str"):
        await write_wrong(Observable(0.0))


async def test_a_progress_argument_must_be_an_observable() -> None:
    with pytest.raises(TypeError, match="progress takes an Observable"):
        await read_back(0.5)  # type: ignore[arg-type]


# -- cancellation -------------------------------------------------------------


async def test_cancelling_the_caller_sets_the_token_and_drops_later_writes(clock: ManualClock) -> None:
    progress = Observable(0.0)
    task = asyncio.ensure_future(cancellable(progress))
    await _gate.until_reached()
    clock.tick()
    assert progress.value == 0.1

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    _gate.release.set()
    for _ in range(500):
        if _seen.get("finished"):
            break
        await asyncio.sleep(0.01)
    clock.tick()

    assert _seen["cancelled"] is True
    assert progress.value == 0.1


async def test_the_token_is_not_set_by_a_call_that_completes() -> None:
    _gate.release.set()

    await cancellable(Observable(0.0))

    assert _seen["cancelled"] is False


async def test_the_caller_cannot_pass_the_token() -> None:
    with pytest.raises(TypeError):
        await cancellable(Observable(0.0), CancelToken())


# -- definition ---------------------------------------------------------------


def _plain(a: int) -> int:
    return a


def _no_annotation(a) -> int:  # type: ignore[no-untyped-def]
    return 0


def _no_return(a: int):  # type: ignore[no-untyped-def]
    return None


def _bad_type(a: set[int]) -> None:
    return None


def _var_args(*a: int) -> None:
    return None


def _token_without_default(cancel: CancelToken) -> None:
    return None


def _bare_writer(progress: WriteOnlyObservable) -> None:  # type: ignore[type-arg]
    return None


def _server_side_type(order: ServerSideOnly) -> None:
    return None


async def _coroutine(a: int) -> int:
    return a


class _Holder:
    def method(self, a: int) -> int:
        return a


@pytest.mark.parametrize(
    ("fn", "message"),
    [
        (_no_annotation, "parameter a needs an annotation"),
        (_no_return, "the return type needs an annotation"),
        (_bad_type, "parameter a: set"),
        (_var_args, r"\*a is not allowed"),
        (_token_without_default, "parameter cancel needs a default"),
        (_bare_writer, "parameter progress needs its value type"),
        (_server_side_type, "ServerSideOnly is defined in the server-only module"),
        (_coroutine, "plain def"),
        (_Holder.method, "module level"),
        (lambda a: a, "module level"),
    ],
)
def test_a_function_that_breaks_a_rule_is_refused_when_defined(fn: Any, message: str) -> None:
    with pytest.raises(TypeError, match=message):
        server(fn)


def test_a_nested_function_is_refused() -> None:
    def inner(a: int) -> int:
        return a

    with pytest.raises(TypeError, match="module level"):
        server(inner)


def test_a_function_in_a_plain_module_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_plain, "__module__", "some_app.views")
    assert not is_server_only("some_app.views")

    assert asyncio.run(server(_plain)(3)) == 3


def test_the_caller_sees_the_signature_without_the_token() -> None:
    import inspect

    assert list(inspect.signature(cancellable).parameters) == ["progress"]


# -- server_only --------------------------------------------------------------


def test_server_only_covers_the_calling_module() -> None:
    assert is_server_only(__name__)
    assert not is_server_only(__name__ + "_other")


def test_server_only_in_a_package_covers_its_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    from nuiitivet.remote import scope

    monkeypatch.setattr(scope, "_server_only", {"app.backend"})

    assert is_server_only("app.backend")
    assert is_server_only("app.backend.orders")
    assert is_server_only("app.backend.db.models")
    assert not is_server_only("app")
    assert not is_server_only("app.backend_tools")


def test_server_only_refuses_to_load_in_a_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "emscripten")

    with pytest.raises(RuntimeError, match="server-only and was loaded in the browser"):
        server_only()
