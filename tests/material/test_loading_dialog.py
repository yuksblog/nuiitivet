from __future__ import annotations

from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.overlay import LoadingDialogIntent
from nuiitivet.overlay.dialogs import PlainLoadingDialog


def _loading_overlay() -> MaterialOverlay:
    return MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i.message)})


def test_overlay_loading_returns_handle() -> None:
    overlay = _loading_overlay()

    handle = overlay.loading()
    assert overlay.has_entries() is True
    handle.close(None)
    assert overlay.has_entries() is False


def test_overlay_while_loading_context_manager_opens_and_closes() -> None:
    overlay = _loading_overlay()

    assert overlay.has_entries() is False
    with overlay.while_loading():
        assert overlay.has_entries() is True
    assert overlay.has_entries() is False
