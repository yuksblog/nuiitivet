"""``@worker`` on the desktop: the same call as ``@server``, from a module the browser gets."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest

from nuiitivet.observable import Observable, runtime
from nuiitivet.observable.switched import CancelToken
from nuiitivet.remote import RemoteError, WriteOnlyObservable, worker
from nuiitivet.remote.function import lookup
from nuiitivet.remote.worker import WorkerFunction
from tests.remote.models import Order
from tests.remote.test_server_function import ManualClock

_TIMEOUT = 5.0
_seen: dict[str, Any] = {}
_gate = threading.Event()


@pytest.fixture(autouse=True)
def _fresh() -> None:
    _seen.clear()
    _gate.clear()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> ManualClock:
    manual = ManualClock()
    monkeypatch.setattr(runtime, "clock", manual)
    return manual


class NotFound(Exception):
    pass


@worker
def add(a: int, b: int = 10) -> int:
    _seen["thread"] = threading.current_thread()
    return a + b


@worker
def keep(order: Order) -> Order:
    order.items.append("added in the worker")
    return order


@worker
def fail_builtin() -> None:
    raise ValueError("bad input")


@worker
def fail_custom(order_id: int) -> None:
    raise NotFound(f"no order {order_id}")


@worker
def report(progress: WriteOnlyObservable[float]) -> int:
    progress.value = 0.5
    assert _gate.wait(_TIMEOUT)
    progress.value = 1.0
    return 3


@worker
def until_cancelled(cancel: CancelToken = CancelToken()) -> None:
    assert _gate.wait(_TIMEOUT)
    _seen["cancelled"] = cancel.cancelled


# -- the call -----------------------------------------------------------------


async def test_the_call_returns_the_result_off_the_calling_thread() -> None:
    assert await add(1, 2) == 3
    assert await add(1) == 11
    assert _seen["thread"] is not threading.current_thread()


async def test_arguments_and_result_are_copies() -> None:
    sent = Order(1, ["a"])

    returned = await keep(sent)

    assert sent.items == ["a"]
    assert returned == Order(1, ["a", "added in the worker"])


async def test_an_argument_of_another_type_is_rejected() -> None:
    with pytest.raises(TypeError, match="a: expected int, got str"):
        await add("1", 2)  # type: ignore[arg-type]


async def test_a_builtin_exception_reaches_the_caller_as_itself() -> None:
    with pytest.raises(ValueError, match="bad input"):
        await fail_builtin()


async def test_any_other_exception_reaches_the_caller_as_remote_error() -> None:
    with pytest.raises(RemoteError) as caught:
        await fail_custom(7)

    assert (caught.value.type_name, caught.value.message) == ("NotFound", "no order 7")


async def test_progress_arrives_while_the_call_is_running(clock: ManualClock) -> None:
    progress = Observable(0.0)
    task = asyncio.ensure_future(report(progress))

    await asyncio.to_thread(lambda: None)
    for _ in range(100):
        clock.tick()
        if progress.value == 0.5:
            break
        await asyncio.sleep(0.01)

    assert progress.value == 0.5
    assert not task.done()
    _gate.set()
    assert await task == 3
    assert progress.value == 1.0


async def test_cancelling_the_task_sets_the_token() -> None:
    task = asyncio.ensure_future(until_cancelled())
    await asyncio.sleep(0)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    _gate.set()
    for _ in range(500):
        if "cancelled" in _seen:
            break
        await asyncio.sleep(0.01)

    assert _seen["cancelled"] is True


# -- definition ---------------------------------------------------------------


def test_the_function_is_registered_under_its_name_as_a_worker_function() -> None:
    function = lookup(f"{__name__}.add")

    assert isinstance(function, WorkerFunction)
    assert function.mark == "worker"


def test_a_function_in_a_server_only_module_is_refused() -> None:
    from tests.remote import test_server_function as server_module

    def stays_on_the_server() -> None:
        pass

    stays_on_the_server.__module__ = server_module.__name__
    stays_on_the_server.__qualname__ = stays_on_the_server.__name__

    with pytest.raises(TypeError, match=r"@worker .*stays_on_the_server: module .* is server-only"):
        worker(stays_on_the_server)


def test_a_method_is_refused_with_the_worker_mark() -> None:
    class Screen:
        def work(self) -> None:
            pass

    with pytest.raises(TypeError, match="@worker .*only a function defined with def at module level"):
        worker(Screen.work)
