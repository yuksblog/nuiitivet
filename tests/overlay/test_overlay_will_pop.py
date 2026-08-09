"""Tests for unified overlay dismissal through ``will_pop`` (issue #186).

Covers the three dismiss paths converging on a single pipeline:
    - ESC / system back  -> Overlay.async_request_close_topmost
    - scrim (outside) tap -> _request_dismiss_entry
    - Close button (SideSheet/BottomSheet) -> OverlayHandle.request_close
"""

from __future__ import annotations

import asyncio

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.sheet import BottomSheet, SideSheet
from nuiitivet.modifiers import will_pop
from nuiitivet.runtime.app import App


@pytest.mark.asyncio
async def test_overlay_async_close_topmost_respects_will_pop_cancel() -> None:
    """async_request_close_topmost returns True (handled) but does not remove the entry
    when will_pop returns False."""
    app = App(content=Container())
    overlay = app.overlay
    overlay.show(Container(width=100, height=100).modifier(will_pop(on_will_pop=lambda: False)), backdrop=True)

    handled = await overlay.async_request_close_topmost()
    assert handled is True
    assert overlay.has_entries() is True


@pytest.mark.asyncio
async def test_overlay_async_close_topmost_proceeds_when_will_pop_allows() -> None:
    app = App(content=Container())
    overlay = app.overlay
    overlay.show(Container(width=100, height=100).modifier(will_pop(on_will_pop=lambda: True)), backdrop=True)

    handled = await overlay.async_request_close_topmost()
    assert handled is True
    assert overlay.has_entries() is False


@pytest.mark.asyncio
async def test_overlay_async_close_topmost_respects_async_will_pop_cancel() -> None:
    async def deny() -> bool:
        await asyncio.sleep(0)
        return False

    app = App(content=Container())
    overlay = app.overlay
    overlay.show(Container(width=100, height=100).modifier(will_pop(on_will_pop=deny)), backdrop=True)

    handled = await overlay.async_request_close_topmost()
    assert handled is True
    assert overlay.has_entries() is True


@pytest.mark.asyncio
async def test_app_escape_overlay_will_pop_cancels_close() -> None:
    """ESC routed through App.handle_back_event respects will_pop on the top overlay entry."""
    app = App(content=Container())
    overlay = app.overlay
    overlay.show(Container(width=100, height=100).modifier(will_pop(on_will_pop=lambda: False)), backdrop=True)

    handled = app._dispatch_key_press("escape")
    assert handled is True
    # Drain the scheduled async back-event task.
    for _ in range(5):
        await asyncio.sleep(0)
    assert overlay.has_entries() is True


@pytest.mark.asyncio
async def test_side_sheet_close_button_respects_will_pop() -> None:
    """Close button on SideSheet routes through request_close, which honors will_pop."""
    content = Container()
    App(content=content, overlay_factory=lambda: MaterialOverlay(intents={}))
    overlay = MaterialOverlay.of(content)
    sheet = SideSheet(Container(width=10, height=10), headline="X")
    overlay.side_sheet(sheet.modifier(will_pop(on_will_pop=lambda: False)))

    sheet._on_close_click()
    # Sync will_pop: cancellation is immediate.
    assert overlay.has_entries() is True


@pytest.mark.asyncio
async def test_side_sheet_close_button_proceeds_without_will_pop() -> None:
    content = Container()
    App(content=content, overlay_factory=lambda: MaterialOverlay(intents={}))
    overlay = MaterialOverlay.of(content)
    sheet = SideSheet(Container(width=10, height=10), headline="X")
    overlay.side_sheet(sheet)

    sheet._on_close_click()
    # Default handle_back_event on ComposableWidget is async; let the
    # scheduled dismiss task run.
    for _ in range(5):
        await asyncio.sleep(0)
    assert overlay.has_entries() is False


@pytest.mark.asyncio
async def test_bottom_sheet_close_button_respects_will_pop() -> None:
    content = Container()
    App(content=content, overlay_factory=lambda: MaterialOverlay(intents={}))
    overlay = MaterialOverlay.of(content)
    sheet = BottomSheet(Container(width=10, height=10), headline="Y")
    overlay.bottom_sheet(sheet.modifier(will_pop(on_will_pop=lambda: False)))

    sheet._on_close_click()
    assert overlay.has_entries() is True


@pytest.mark.asyncio
async def test_material_overlay_side_sheet_accepts_wrapped_widget() -> None:
    """MaterialOverlay.side_sheet walks the tree to find SideSheet inside a wrapper."""
    content = Container()
    App(content=content, overlay_factory=lambda: MaterialOverlay(intents={}))
    overlay = MaterialOverlay.of(content)
    sheet = SideSheet(Container(width=10, height=10), headline="X")
    handle = overlay.side_sheet(sheet.modifier(will_pop(on_will_pop=lambda: True)), side="left")
    assert handle is not None
    assert overlay.has_entries() is True
