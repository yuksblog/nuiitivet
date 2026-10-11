"""``@worker(parallel=N)`` without ``process`` on the desktop: the calls run on pooled threads, N at a time.

The functions block on an event the test sets, so the test decides when
each call goes on and never sleeps.
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from typing import Any, Callable, Iterator

import pytest

from nuiitivet.observable.switched import CancelToken
from nuiitivet.remote import worker
from nuiitivet.remote.worker import retire_pool, thread_pool

_TIMEOUT = 10.0
_seen: dict[str, Any] = {}
_lock = threading.Lock()
_release = threading.Event()


@pytest.fixture(autouse=True)
def _fresh() -> Iterator[None]:
    global _release
    _seen.clear()
    _release = threading.Event()
    yield
    _release.set()
    retire_pool()


async def until(condition: Callable[[], bool]) -> None:
    deadline = asyncio.get_running_loop().time() + _TIMEOUT
    while not condition():
        assert asyncio.get_running_loop().time() < deadline, "the condition never held"
        await asyncio.sleep(0.01)


def _arrived() -> None:
    with _lock:
        _seen["arrived"] = _seen.get("arrived", 0) + 1


def arrived() -> int:
    """How many calls have reached their wait."""
    with _lock:
        return int(_seen.get("arrived", 0))


@worker(parallel=2)
def hold(n: int) -> int:
    _arrived()
    assert _release.wait(_TIMEOUT)
    return os.getpid() * 10 + n


@worker(parallel=1)
def until_cancelled(cancel: CancelToken = CancelToken()) -> None:
    _arrived()
    while not cancel.cancelled:
        time.sleep(0.01)
    _seen["cancelled"] = True


# -- the ceiling --------------------------------------------------------------


async def test_calls_run_on_threads_in_this_process_up_to_the_ceiling() -> None:
    tasks = [asyncio.ensure_future(hold(n)) for n in range(3)]

    await until(lambda: arrived() == 2)
    await asyncio.sleep(0.1)
    assert arrived() == 2
    assert thread_pool().size == 2
    assert not any(task.done() for task in tasks)

    _release.set()
    results = await asyncio.gather(*tasks)

    assert results == [os.getpid() * 10 + n for n in range(3)]
    assert thread_pool().size == 2


# -- cancel -------------------------------------------------------------------


async def test_cancelling_a_pooled_thread_call_sets_its_token_and_frees_its_place() -> None:
    task = asyncio.ensure_future(until_cancelled())
    await until(lambda: arrived() == 1)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await until(lambda: bool(_seen.get("cancelled")))

    _release.set()
    assert await hold(7) == os.getpid() * 10 + 7
