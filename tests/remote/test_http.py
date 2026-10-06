"""The server's side of a call, driven by a plain HTTP client."""

from __future__ import annotations

import http.client
import json
import threading
from typing import Any, Iterator

import pytest

from nuiitivet.observable.switched import CancelToken
from nuiitivet.remote import WriteOnlyObservable, server, server_only
from nuiitivet.web.server import make_server
from tests.remote.models import Order

server_only()

_TIMEOUT = 5.0
_gate = threading.Event()
_seen: dict[str, Any] = {}


@pytest.fixture(autouse=True)
def _fresh() -> None:
    _gate.clear()
    _seen.clear()


@server
def add(a: int, b: int) -> int:
    return a + b


@server
def keep(order: Order) -> Order:
    order.items.append("server")
    return order


@server
def report(progress: WriteOnlyObservable[float]) -> str:
    progress.value = 0.5
    assert _gate.wait(_TIMEOUT)
    progress.value = 1.0
    return "done"


@server
def fail_builtin() -> None:
    raise ValueError("bad input")


@server
def fail_custom() -> None:
    raise LookupError("x") from None


class NotHere(Exception):
    pass


@server
def fail_own() -> None:
    raise NotHere("gone")


@server
def until_cancelled(cancel: CancelToken = CancelToken()) -> None:
    _seen["started"] = True
    for _ in range(int(_TIMEOUT / 0.01)):
        if cancel.cancelled:
            _seen["cancelled"] = True
            return
        threading.Event().wait(0.01)


@pytest.fixture
def address() -> Iterator[tuple[str, int]]:
    httpd = make_server({}, 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield str(httpd.server_address[0]), httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def _post(address: tuple[str, int], name: str, values: dict[str, Any]) -> http.client.HTTPResponse:
    connection = http.client.HTTPConnection(*address, timeout=_TIMEOUT)
    connection.request("POST", f"/nv/call/{name}", json.dumps(values), {"Content-Type": "application/json"})
    return connection.getresponse()


def _lines(response: http.client.HTTPResponse) -> list[Any]:
    return [json.loads(line) for line in response.read().splitlines()]


def test_a_call_answers_with_the_result(address: tuple[str, int]) -> None:
    response = _post(address, __name__ + ".add", {"a": 1, "b": 2})

    assert response.status == 200
    assert response.getheader("Content-Type") == "application/x-ndjson"
    assert _lines(response) == [{"r": 3}]


def test_arguments_and_results_travel_in_their_wire_form(address: tuple[str, int]) -> None:
    response = _post(address, __name__ + ".keep", {"order": {"id": 1, "items": ["a"]}})

    assert _lines(response) == [{"r": {"id": 1, "items": ["a", "server"]}}]


def test_a_write_arrives_before_the_result_and_while_the_function_runs(address: tuple[str, int]) -> None:
    response = _post(address, __name__ + ".report", {})

    assert json.loads(response.readline()) == {"w": "progress", "v": 0.5}
    _gate.set()
    assert [json.loads(line) for line in response.read().splitlines()] == [{"w": "progress", "v": 1.0}, {"r": "done"}]


@pytest.mark.parametrize(
    ("name", "error"),
    [
        ("fail_builtin", {"type": "ValueError", "message": "bad input", "builtin": True}),
        ("fail_custom", {"type": "LookupError", "message": "x", "builtin": True}),
        ("fail_own", {"type": "NotHere", "message": "gone", "builtin": False}),
    ],
)
def test_an_exception_answers_as_its_wire_form(address: tuple[str, int], name: str, error: dict[str, Any]) -> None:
    assert _lines(_post(address, f"{__name__}.{name}", {})) == [{"e": error}]


def test_an_argument_of_another_type_is_an_error_line(address: tuple[str, int]) -> None:
    [message] = _lines(_post(address, __name__ + ".add", {"a": "1", "b": 2}))

    assert message["e"]["type"] == "TypeError"
    assert "a: expected int, got str" in message["e"]["message"]


def test_an_unknown_function_is_not_found(address: tuple[str, int]) -> None:
    assert _post(address, "nowhere.nothing", {}).status == 404


def test_a_get_of_the_call_route_is_not_found(address: tuple[str, int]) -> None:
    connection = http.client.HTTPConnection(*address, timeout=_TIMEOUT)
    connection.request("GET", "/nv/call/" + __name__ + ".add")

    assert connection.getresponse().status == 404


def test_hanging_up_sets_the_token(address: tuple[str, int]) -> None:
    connection = http.client.HTTPConnection(*address, timeout=_TIMEOUT)
    connection.request("POST", f"/nv/call/{__name__}.until_cancelled", "{}", {"Content-Type": "application/json"})
    for _ in range(500):
        if _seen.get("started"):
            break
        threading.Event().wait(0.01)

    connection.close()
    for _ in range(500):
        if _seen.get("cancelled"):
            break
        threading.Event().wait(0.01)

    assert _seen.get("cancelled") is True
