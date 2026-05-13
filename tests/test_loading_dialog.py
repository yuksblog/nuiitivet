from __future__ import annotations

from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.overlay import Overlay, LoadingDialogIntent
from nuiitivet.overlay.dialogs import PlainLoadingDialog


def test_overlay_loading_returns_handle() -> None:
    overlay = MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i.message)})
    Overlay.set_root(overlay)

    handle = overlay.loading()
    assert overlay.has_entries() is True
    handle.close(None)
    assert overlay.has_entries() is False


def test_overlay_while_loading_context_manager_opens_and_closes() -> None:
    overlay = MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i.message)})
    Overlay.set_root(overlay)

    assert overlay.has_entries() is False
    with overlay.while_loading():
        assert overlay.has_entries() is True
    assert overlay.has_entries() is False
