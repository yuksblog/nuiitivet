"""The desktop's workers for the ``@worker`` functions marked ``parallel`` without ``process``: threads."""

from __future__ import annotations

import json
import queue
import sys
import threading
from typing import Optional

from nuiitivet.observable.switched import CancelToken

from .codec import Json
from .function import answer
from .pool import Slot


class ThreadTransport:
    """Starts threads, one per worker. A thread costs nothing to start, so the machine sets no limit."""

    machine_limit = sys.maxsize

    def start(self, slot: Slot) -> _ThreadWorker:
        """Start one thread that reports to *slot*.

        Args:
            slot: Where the thread's ready, its messages and its end arrive.
        """
        return _ThreadWorker(slot)


class _ThreadWorker:
    """One thread that runs calls in turn, in this process."""

    __slots__ = ("_calls", "_running", "_lock")

    def __init__(self, slot: Slot) -> None:
        self._calls: queue.SimpleQueue[Optional[tuple[int, str, dict[str, Json]]]] = queue.SimpleQueue()
        self._running: Optional[CancelToken] = None
        self._lock = threading.Lock()
        threading.Thread(target=self._run, args=(slot,), name="nuiitivet-worker", daemon=True).start()

    def post(self, call_id: int, name: str, values: dict[str, Json]) -> None:
        self._calls.put((call_id, name, values))

    def end(self) -> None:
        # A thread cannot be killed: the running call's token is set and the
        # thread finishes it, then ends. The pool reads nothing more from it.
        with self._lock:
            running = self._running
        if running is not None:
            running._supersede()
        self._calls.put(None)

    def _run(self, slot: Slot) -> None:
        slot.ready()
        while True:
            call = self._calls.get()
            if call is None:
                return
            call_id, name, values = call
            token = CancelToken()
            with self._lock:
                self._running = token
            answer(call_id, name, values, lambda message: slot.message(json.dumps(message)), token)
            with self._lock:
                self._running = None


__all__ = ["ThreadTransport"]
