"""Tests for OverlayHandle semantics."""

from __future__ import annotations

import asyncio

import pytest

from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.result import OverlayResult
from nuiitivet.overlay.result import OverlayDismissReason


def test_overlay_handle_done_and_result_when_closed_before_await() -> None:
    overlay = Overlay()

    handle = overlay.show(BasicDialog(title="Title"), backdrop=True)
    handle.close(True)

    assert handle.done() is True
    result = handle.result()
    assert result is not None
    assert result.value is True
    assert result.reason is OverlayDismissReason.CLOSED

    with pytest.raises(RuntimeError, match="never awaited"):
        handle.result()


async def test_overlay_handle_result_available_after_await_and_close(
    nuiitivet_mount,
) -> None:
    overlay = Overlay()
    host = nuiitivet_mount(overlay)
    host.layout(400, 300)
    handle = overlay.show(BasicDialog(title="Title"), backdrop=True)

    async def _wait() -> OverlayResult[str]:
        return await handle

    waiter = asyncio.create_task(_wait())
    await host.idle()  # let the waiter park on the handle before it resolves
    handle.close("ok")

    awaited = await waiter
    assert awaited.value == "ok"
    assert awaited.reason is OverlayDismissReason.CLOSED
    assert handle.done() is True

    result = handle.result()
    assert result is not None
    assert result.value == "ok"
    assert result.reason is OverlayDismissReason.CLOSED
