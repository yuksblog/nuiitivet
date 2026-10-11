"""The worker's side of a call: the page's message in, progress and the result out.

``worker.mjs`` imports this module in each worker's Pyodide.
"""

from __future__ import annotations

import importlib
import json
from typing import Iterable

import js

from nuiitivet.remote.function import answer


def prepare(modules: Iterable[str]) -> None:
    """Import the app's modules that hold a ``@worker`` function, so they answer calls.

    Args:
        modules: Their dotted names.
    """
    for name in list(modules):
        importlib.import_module(str(name))


def handle(call_id: int, name: str, values: str) -> None:
    """Run one call and post what it produces to the page, message by message.

    Args:
        call_id: The page's number for the call; every message carries it.
        name: The function's module and name, dotted.
        values: The data arguments by name, encoded, as JSON text.
    """
    answer(call_id, name, json.loads(values), lambda message: js.postMessage(json.dumps(message)))


__all__ = ["handle", "prepare"]
