"""A server function awaited by a handler of a mounted app."""

from __future__ import annotations

import threading

from nuiitivet.layout.column import Column
from nuiitivet.material.buttons import Button
from nuiitivet.material.text import Text
from nuiitivet.observable import Observable
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
