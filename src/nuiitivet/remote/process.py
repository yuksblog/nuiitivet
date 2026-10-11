"""The desktop's workers for the ``@worker`` functions marked ``parallel``: child processes, and the child's side."""

from __future__ import annotations

import importlib
import json
import multiprocessing
import os
import threading
import traceback
from multiprocessing.connection import Connection
from typing import Callable

from .codec import Json
from .function import alias_module, answer
from .pool import Slot

# How long the parent waits for an ended child before killing it.
_JOIN_TIMEOUT = 5.0


class ProcessTransport:
    """Starts child processes, one per worker, with the ``spawn`` context on every OS.

    ``fork`` is not used on any OS: a forked child inherits the UI's threads
    and its windowing state, and ``spawn`` behaves the same everywhere.
    """

    def __init__(self, modules: Callable[[], list[str]]) -> None:
        """Initialize ProcessTransport.

        Args:
            modules: The dotted names of the modules a child imports before
                it reads calls, read when a child starts.
        """
        self._modules = modules

    @property
    def machine_limit(self) -> int:
        """The machine's CPU count."""
        return os.cpu_count() or 1

    def start(self, slot: Slot) -> _ProcessWorker:
        """Start one child that reports to *slot*.

        Args:
            slot: Where the child's ready, its messages and its exit arrive.
        """
        return _ProcessWorker(slot, self._modules())


class _ProcessWorker:
    """One child process, and the thread that reads what it sends."""

    __slots__ = ("_connection", "_process")

    def __init__(self, slot: Slot, modules: list[str]) -> None:
        context = multiprocessing.get_context("spawn")
        self._connection, child = context.Pipe()
        self._process = context.Process(target=serve, args=(child, modules), name="nuiitivet-worker", daemon=True)
        self._process.start()
        child.close()
        threading.Thread(target=self._read, args=(slot,), name="nuiitivet-worker-reader", daemon=True).start()

    def post(self, call_id: int, name: str, values: dict[str, Json]) -> None:
        try:
            self._connection.send_bytes(json.dumps({"id": call_id, "name": name, "values": values}).encode())
        except OSError:
            # The child is gone; its exit reaches the pool from the reader thread.
            pass

    def end(self) -> None:
        self._process.terminate()

    def _read(self, slot: Slot) -> None:
        connection, process = self._connection, self._process
        failure = None
        try:
            first = json.loads(connection.recv_bytes().decode())
            if "failed" in first:
                failure = first["failed"]
            else:
                slot.ready()
                while True:
                    slot.message(connection.recv_bytes().decode())
        except (EOFError, OSError):
            pass
        finally:
            connection.close()
        process.join(_JOIN_TIMEOUT)
        if process.is_alive():
            process.kill()
            process.join()
        slot.exit(failure or f"exit code {process.exitcode}")


def serve(connection: Connection, modules: list[str]) -> None:
    """The child's whole life: import *modules*, say so, then answer calls until the parent closes the pipe.

    The target of every worker process. The first message is ``{"ready":
    true}`` or ``{"failed": traceback}``; after it, each message is one of a
    call's, as :func:`~nuiitivet.remote.function.answer` writes them.

    Args:
        connection: The child's end of the pipe to the parent.
        modules: The dotted names of the modules that hold the functions.
    """

    def send(message: dict[str, Json]) -> None:
        connection.send_bytes(json.dumps(message).encode())

    try:
        for name in modules:
            importlib.import_module(name)
    except BaseException:
        send({"failed": traceback.format_exc()})
        return
    # The entry script ran here as __mp_main__; the parent names its functions by __main__.
    alias_module("__mp_main__", "__main__")
    send({"ready": True})
    while True:
        try:
            request = json.loads(connection.recv_bytes().decode())
        except EOFError:
            return
        answer(request["id"], request["name"], request["values"], send)


__all__ = ["ProcessTransport", "serve"]
