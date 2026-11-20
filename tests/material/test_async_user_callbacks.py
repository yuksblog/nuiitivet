"""The user callbacks of the Material widgets accept an async handler."""

import asyncio
from datetime import date
from typing import Callable, Coroutine

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.chip import FilterChip
from nuiitivet.material.date_picker import DatePicker
from nuiitivet.material.menu import Menu, MenuItem, SubMenuItem
from nuiitivet.material.navigation_rail import NavigationRail, RailItem
from nuiitivet.material.search import DockedSearchBar, SearchBar
from nuiitivet.material.selection_controls import Checkbox, RadioButton, RadioGroup, Switch
from nuiitivet.material.sheet import StandardSideSheet
from nuiitivet.material.slider import HorizontalRangeSlider, HorizontalSlider
from nuiitivet.material.text import Text
from nuiitivet.material.text_fields import TextField
from nuiitivet.observable import State
from nuiitivet.testing import AppHarness
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box


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


@pytest.mark.asyncio
async def test_async_value_change_callbacks_of_search_slider_and_date_picker_run() -> None:
    calls: list[tuple[str, object]] = []
    picker = DatePicker(State(date(2026, 11, 1)), on_change=_recorder(calls, "date picker"))

    def build() -> Widget:
        return Column(
            [
                SearchBar(State(""), on_change=_recorder(calls, "search bar"), key="search"),
                HorizontalSlider(on_change=_recorder(calls, "slider"), width=200, key="slider"),
                HorizontalRangeSlider(on_change=_recorder(calls, "range slider"), width=200, key="range"),
                picker,
            ]
        )

    with AppHarness(build, size=(480, 900)) as app:
        app.type("q", key="search")
        await app.idle()
        for key in ("slider", "range"):
            app.click(key=key)
            await app.idle()
        picker._on_day_tap(date(2026, 11, 15))  # as the date picker tests do
        await app.idle()

    assert [name for name, _value in calls] == ["search bar", "slider", "range slider", "date picker"]
    assert calls[0] == ("search bar", "q")
    assert calls[3] == ("date picker", date(2026, 11, 15))


@pytest.mark.asyncio
async def test_async_callbacks_of_filter_chip_navigation_rail_and_docked_search_bar_run() -> None:
    calls: list[tuple[str, object]] = []

    async def on_click() -> None:
        calls.append(("filter chip click", None))

    async def on_focus_change(focused: bool, _source: object) -> None:
        calls.append(("docked search bar", focused))

    def build() -> Widget:
        return Row(
            [
                NavigationRail(
                    children=[RailItem(icon="home", label="Home"), RailItem(icon="book", label="Library")],
                    on_select=_recorder(calls, "navigation rail"),
                ),
                Column(
                    [
                        FilterChip(
                            "Filter",
                            on_selected_change=_recorder(calls, "filter chip"),
                            on_click=on_click,
                            key="chip",
                        ),
                        DockedSearchBar(
                            State(""), content=Text("results"), on_focus_change=on_focus_change, key="docked"
                        ),
                    ]
                ),
            ]
        )

    with AppHarness(build, size=(800, 600)) as app:
        # The collapsed rail also holds the expanded label, clipped to nothing; the
        # visible one sits under the icon, the leftmost of the two.
        x, y, w, h = min((n.rect for n in app.get_all(label="Library") if n.rect is not None), key=lambda r: r[0])
        app.click(x=x + w / 2, y=y + h / 2)
        await app.idle()
        for key in ("chip", "docked"):
            app.click(key=key)
            await app.idle()

    assert calls[:4] == [
        ("navigation rail", 1),
        ("filter chip", True),
        ("filter chip click", None),
        ("docked search bar", True),
    ]


def _event_recorder(calls: list[tuple[str, object]], name: str) -> Callable[[], Coroutine[None, None, None]]:
    async def handler() -> None:
        calls.append((name, None))

    return handler


@pytest.mark.asyncio
async def test_async_submit_callbacks_run() -> None:
    calls: list[tuple[str, object]] = []

    def build() -> Widget:
        return Column(
            [
                TextField(State(""), on_submit=_recorder(calls, "text field"), key="field"),
                SearchBar(State(""), on_submit=_recorder(calls, "search bar"), key="search"),
                DockedSearchBar(State(""), content=Text("results"), on_submit=_recorder(calls, "docked"), key="docked"),
            ]
        )

    with AppHarness(build, size=(480, 600)) as app:
        for key in ("field", "search", "docked"):
            app.type("q", key=key)
            app.key("enter")
            await app.idle()

    assert calls == [("text field", "q"), ("search bar", "q"), ("docked", "q")]


@pytest.mark.asyncio
async def test_async_confirm_cancel_dismiss_and_close_callbacks_run() -> None:
    calls: list[tuple[str, object]] = []
    confirming = DatePicker(State(date(2026, 11, 15)), on_confirm=_recorder(calls, "date picker confirm"))
    cancelling = DatePicker(State(None), on_cancel=_event_recorder(calls, "date picker cancel"))
    menu = Menu(items=[MenuItem("A")], on_dismiss=_event_recorder(calls, "menu dismiss"))
    submenu = SubMenuItem("Export", items=[MenuItem("PNG")])
    submenu._bind_parent_dismiss(_event_recorder(calls, "submenu dismiss"))
    sheet = StandardSideSheet(Box(), on_close_click=_event_recorder(calls, "sheet close"))

    # The entry points the date picker, menu and sheet tests drive.
    confirming._on_ok()
    cancelling._on_cancel()
    assert menu.on_key_event("escape") is True
    submenu._chained_dismiss()
    sheet._handle_close_click()
    for _ in range(5):
        await asyncio.sleep(0)

    assert calls == [
        ("date picker confirm", date(2026, 11, 15)),
        ("date picker cancel", None),
        ("menu dismiss", None),
        ("submenu dismiss", None),
        ("sheet close", None),
    ]
