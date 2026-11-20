"""The value-change callbacks of the selection controls accept an async handler."""

from typing import Callable, Coroutine

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.selection_controls import Checkbox, RadioButton, RadioGroup, Switch
from nuiitivet.observable import State
from nuiitivet.testing import AppHarness
from nuiitivet.widgeting.widget import Widget


def _recorder(calls: list[tuple[str, object]], name: str) -> Callable[[object], Coroutine[None, None, None]]:
    async def handler(value: object) -> None:
        calls.append((name, value))

    return handler


@pytest.mark.asyncio
async def test_async_value_change_callbacks_run() -> None:
    calls: list[tuple[str, object]] = []

    def build() -> Widget:
        return Column(
            [
                Checkbox(checked=State(False), on_toggle=_recorder(calls, "bound checkbox"), key="bound"),
                Checkbox(
                    checked=State(False),
                    indeterminate=State(True),
                    on_toggle=_recorder(calls, "split checkbox"),
                    key="split",
                ),
                Checkbox(on_toggle=_recorder(calls, "local checkbox"), key="local"),
                Switch(on_change=_recorder(calls, "switch"), key="switch"),
                RadioGroup(
                    Row([RadioButton("a"), RadioButton("b", key="radio-b")]),
                    value=State("a"),
                    on_change=_recorder(calls, "radio group"),
                ),
            ]
        )

    with AppHarness(build, size=(400, 400)) as app:
        for key in ("bound", "split", "local", "switch", "radio-b"):
            app.click(key=key)
            await app.idle()

    assert calls == [
        ("bound checkbox", True),
        ("split checkbox", True),
        ("local checkbox", True),
        ("switch", True),
        ("radio group", "b"),
    ]
