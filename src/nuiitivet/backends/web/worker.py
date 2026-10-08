"""The worker's side of a call: the page's message in, progress and the result out.

The page's ``worker.mjs`` imports this module in the worker's Pyodide.
"""

from __future__ import annotations

import importlib
import json
from typing import Any, Callable, Iterable

import js

from nuiitivet.observable.switched import CancelToken
from nuiitivet.remote.codec import Json
from nuiitivet.remote.function import encode_error, lookup


def prepare(modules: Iterable[str]) -> None:
    """Import the app's modules that hold a ``@worker`` function, so they answer calls.

    Args:
        modules: Their dotted names.
    """
    for name in list(modules):
        importlib.import_module(str(name))


def handle(call_id: int, name: str, values: str) -> None:
    """Run one call and post what it produces to the page.

    Each message is JSON text: ``{"id", "w": name, "v": data}`` for a write to
    a ``WriteOnlyObservable`` parameter, then ``{"id", "r": data}`` with the
    result or ``{"id", "e": {...}}`` with the exception.

    Args:
        call_id: The page's number for the call; every message carries it.
        name: The function's module and name, dotted.
        values: The data arguments by name, encoded, as JSON text.
    """

    def send(message: dict[str, Any]) -> None:
        js.postMessage(json.dumps({"id": call_id, **message}))

    def writer(parameter: str) -> Callable[[Json], None]:
        return lambda data: send({"w": parameter, "v": data})

    function = lookup(name)
    if function is None:
        send({"e": encode_error(LookupError(f"no worker function {name}"))})
        return
    writers = {parameter: writer(parameter) for parameter in function._writers}
    try:
        send({"r": function.run(json.loads(values), writers, CancelToken())})
    except Exception as error:
        send({"e": encode_error(error)})


__all__ = ["handle", "prepare"]
