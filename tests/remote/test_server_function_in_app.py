"""A server function awaited by a handler of a mounted app, and one behind ``switch_map``."""

from __future__ import annotations

import threading

from nuiitivet.layout.column import Column
from nuiitivet.material.buttons import Button
from nuiitivet.material.text import Text
from nuiitivet.observable import Observable
from nuiitivet.observable.switched import CancelToken
from nuiitivet.remote import WriteOnlyObservable, server, server_only
from nuiitivet.widgeting.widget import ComposableWidget, Widget

server_only()

_TIMEOUT = 5.0
_halfway = threading.Event()
_finish = threading.Event()


@server
def import_rows(count: int, progress: WriteOnlyObservable[str]) -> int:
    progress.value = "half"
    _halfway.set()
    assert _finish.wait(_TIMEOUT)
    progress.value = "all"
    return count


_searched: list[str] = []
_cancelled: list[str] = []


@server
def search(query: str, cancel: CancelToken = CancelToken()) -> list[str]:
    _searched.append(query)
    if query == "slow":
        for _ in range(500):
            if cancel.cancelled:
                _cancelled.append(query)
                return []
            threading.Event().wait(0.01)
    return [f"{query}-1", f"{query}-2"]


class _Importer(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.progress = Observable("none")
        self.result = Observable("")

    def build(self) -> Widget:
        return Column(
            children=[
                Text(self.progress, key="progress"),
                Text(self.result, key="result"),
                Button("import", on_click=self._import, key="import"),
            ]
        )

    async def _import(self) -> None:
        self.result.value = f"imported {await import_rows(3, self.progress)}"


class _Search(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.query = Observable("")
        nothing: list[str] = []
        self.results = self.query.switch_map(search, initial=nothing)

    def build(self) -> Widget:
        return Column(children=[Text(self.results.map(", ".join), key="results")])


async def test_a_server_function_answers_a_switch_map(nuiitivet_app) -> None:
    _searched.clear()
    _cancelled.clear()
    screen = _Search()
    app = nuiitivet_app(screen, size=(400, 300))

    screen.query.value = "slow"
    await app.wait_for(lambda: "slow" in _searched)
    screen.query.value = "fast"
    await app.wait_for(text="fast-1, fast-2")
    await app.wait_for(lambda: _cancelled == ["slow"])


async def test_progress_shows_while_the_handler_waits_and_the_result_after(nuiitivet_app) -> None:
    _halfway.clear()
    _finish.clear()
    screen = _Importer()
    app = nuiitivet_app(screen, size=(400, 300))

    app.click(key="import")
    await app.wait_for(lambda: app.get(key="progress").text == "half")
    assert screen.result.value == ""

    _finish.set()
    await app.wait_for(text="imported 3")
    assert app.get(key="progress").text == "all"
