"""Tests for OverlayHandle semantics."""

from __future__ import annotations

import asyncio

import pytest

from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.result import OverlayResult
from nuiitivet.overlay.result import OverlayDismissReason
from nuiitivet.theme.manager import manager
from nuiitivet.material.theme.material_theme import MaterialTheme


@pytest.fixture(autouse=True)
def material_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))


def test_overlay_handle_done_and_result_when_closed_before_await() -> None:
    overlay = Overlay()

    handle = overlay.show(AlertDialog(title="Title"), dismiss_on_outside_tap=False)
    handle.close(True)

    assert handle.done() is True
    result = handle.result()
    assert result is not None
    assert result.value is True
    assert result.reason is OverlayDismissReason.CLOSED

    with pytest.raises(RuntimeError, match="never awaited"):
        handle.result()


def test_overlay_handle_result_available_after_await_and_close() -> None:
    overlay = Overlay()

    async def run() -> OverlayResult[str]:
        handle = overlay.show(AlertDialog(title="Title"), dismiss_on_outside_tap=False)

        async def _wait() -> OverlayResult[str]:
            return await handle

        waiter = asyncio.create_task(_wait())
        await asyncio.sleep(0)
        handle.close("ok")
        awaited = await waiter
        assert awaited.value == "ok"
        assert awaited.reason is OverlayDismissReason.CLOSED
        assert handle.done() is True
        result = handle.result()
        assert result is not None
        return result

    result = asyncio.run(run())
    assert result is not None
    assert result.value == "ok"
    assert result.reason is OverlayDismissReason.CLOSED
