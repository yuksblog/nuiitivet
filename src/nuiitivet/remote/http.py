"""The server's side of a call: one POST in, a stream of progress and the result out."""

from __future__ import annotations

import json
import select
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any

from nuiitivet.observable.switched import CancelToken

from .codec import Json
from .function import CALL_ROUTE, encode_error, lookup

# How often a running call looks for the caller hanging up, in seconds.
_POLL = 0.05


class _Outbox:
    """The newest write of each Observable, waiting to be sent."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: dict[str, Json] = {}
        self._changed = threading.Event()

    def sender(self, name: str) -> Any:
        def send(data: Json) -> None:
            with self._lock:
                self._pending[name] = data
            self._changed.set()

        return send

    def take(self, timeout: float) -> dict[str, Json]:
        self._changed.wait(timeout)
        with self._lock:
            pending, self._pending = self._pending, {}
            self._changed.clear()
            return pending


def _hung_up(connection: socket.socket) -> bool:
    """Whether the caller closed the connection. The request was read in full before."""
    readable, _, _ = select.select([connection], [], [], 0)
    if not readable:
        return False
    try:
        return connection.recv(1, socket.MSG_PEEK) == b""
    except OSError:
        return True


def handle_call(handler: BaseHTTPRequestHandler) -> bool:
    """Answer a POST to the call route, if ``handler.path`` is one.

    The response is newline-delimited JSON: a line ``{"w": name, "v": data}``
    for each write to a ``WriteOnlyObservable`` parameter, then one line
    ``{"r": data}`` with the result or ``{"e": {...}}`` with the exception.
    A caller that hangs up sets the function's ``CancelToken``.

    Args:
        handler: The request handler, with the request line and headers read.

    Returns:
        Whether the path was a call. ``False`` leaves the request untouched.
    """
    route = handler.path.split("?", 1)[0].lstrip("/")
    if not route.startswith(CALL_ROUTE):
        return False
    function = lookup(route[len(CALL_ROUTE):])
    if function is None:
        handler.send_error(HTTPStatus.NOT_FOUND, "no such server function")
        return True
    length = int(handler.headers.get("Content-Length") or 0)
    values = json.loads(handler.rfile.read(length) or b"{}")

    outbox = _Outbox()
    token = CancelToken()
    done: dict[str, Json] = {}

    def run() -> None:
        try:
            done["r"] = function.run(values, {name: outbox.sender(name) for name in function._writers}, token)
        except Exception as error:
            done["e"] = encode_error(error)

    worker = threading.Thread(target=run, name=f"server:{function.name}", daemon=True)
    worker.start()

    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "application/x-ndjson")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    # The connection stays open until the result; a caller that cancelled is
    # the only one that closes it first.
    handler.close_connection = True
    while worker.is_alive():
        if _hung_up(handler.connection):
            token._supersede()
            worker.join()
            return True
        for name, data in outbox.take(_POLL).items():
            _send(handler, {"w": name, "v": data})
    worker.join()
    for name, data in outbox.take(0).items():
        _send(handler, {"w": name, "v": data})
    _send(handler, done)
    return True


def _send(handler: BaseHTTPRequestHandler, message: Json) -> None:
    try:
        handler.wfile.write(json.dumps(message).encode() + b"\n")
        handler.wfile.flush()
    except OSError:
        pass


__all__ = ["handle_call"]
