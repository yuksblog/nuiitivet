"""The functions the worker-process tests call. A child process imports this module by name."""

from __future__ import annotations

import os
import time

from nuiitivet.observable.switched import CancelToken
from nuiitivet.remote import WriteOnlyObservable, worker
from tests.remote.models import Order

_TIMEOUT = 15.0


def _wait_for(path: str) -> None:
    """Block until the file at *path* exists: a gate the test opens from the other process."""
    deadline = time.monotonic() + _TIMEOUT
    while not os.path.exists(path):
        assert time.monotonic() < deadline, f"nobody opened {path}"
        time.sleep(0.01)


class NotFound(Exception):
    pass


@worker
def pid_on_thread() -> int:
    return os.getpid()


@worker(process=True)
def pid_alone() -> int:
    return os.getpid()


@worker(parallel=2, process=True)
def pid() -> int:
    return os.getpid()


@worker(parallel=2, process=True)
def keep(order: Order) -> Order:
    order.items.append("added in the worker")
    return order


@worker(parallel=2, process=True)
def fail_builtin() -> None:
    raise ValueError("bad input")


@worker(parallel=2, process=True)
def fail_custom(order_id: int) -> None:
    raise NotFound(f"no order {order_id}")


@worker(parallel=2, process=True)
def report(gate: str, progress: WriteOnlyObservable[float]) -> int:
    progress.value = 0.5
    _wait_for(gate)
    progress.value = 1.0
    return os.getpid()


@worker(parallel=2, process=True)
def forever(started: WriteOnlyObservable[int], cancel: CancelToken = CancelToken()) -> None:
    started.value = os.getpid()
    while not cancel.cancelled:  # never set in a process: the call ends when the process does
        time.sleep(0.05)


@worker(parallel=2, process=True)
def crash() -> None:
    os._exit(3)
