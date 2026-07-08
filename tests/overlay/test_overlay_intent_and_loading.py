"""Tests for Overlay intent resolution and loading context manager."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.overlay.intents import LoadingDialogIntent
from nuiitivet.overlay.dialogs import PlainLoadingDialog
from nuiitivet.overlay.overlay_route import OverlayRoute
from nuiitivet.navigation.transition_spec import EmptyTransitionSpec


@dataclass(frozen=True, slots=True)
class _ConfirmIntent:
    message: str


def test_overlay_dialog_intent_resolves_to_widget() -> None:
    overlay = MaterialOverlay(
        intents={
            _ConfirmIntent: lambda i: BasicDialog(title="Confirm", message=i.message),
        }
    )

    overlay.dialog(_ConfirmIntent("hi"), dismiss_on_outside_tap=False)

    assert overlay.has_entries() is True
    route = next(iter(overlay._entry_to_route.values()))
    assert not isinstance(route.transition_spec, EmptyTransitionSpec)


def test_overlay_dialog_intent_resolves_to_route() -> None:
    from nuiitivet.navigation.route import Route

    overlay = MaterialOverlay(
        intents={
            _ConfirmIntent: lambda i: Route(builder=lambda: BasicDialog(title=i.message)),
        }
    )

    overlay.dialog(_ConfirmIntent("Confirm"), dismiss_on_outside_tap=False)
    assert overlay.has_entries() is True


def test_overlay_dialog_unknown_intent_raises() -> None:
    overlay = MaterialOverlay(intents={})

    with pytest.raises(RuntimeError, match=r"No overlay intent is registered: _ConfirmIntent"):
        overlay.dialog(_ConfirmIntent("x"), dismiss_on_outside_tap=False)


def test_material_overlay_dialog_accepts_widget_without_manual_dialog_route() -> None:
    overlay = MaterialOverlay(intents={})
    widget = BasicDialog(title="Widget dialog")

    route = overlay._normalize_dialog_to_route(widget, dismiss_on_outside_tap=False)

    assert isinstance(route, OverlayRoute)
    assert route.barrier_dismissible is False

    overlay.dialog(widget, dismiss_on_outside_tap=False)
    assert overlay.has_entries() is True


def test_material_overlay_dialog_rejects_directly_passed_route() -> None:
    """dialog() no longer accepts a Route directly; a Route is treated as an
    unknown intent. Callers needing a custom Route should use show_modal()."""
    overlay = MaterialOverlay(intents={})
    route = OverlayRoute(builder=lambda: BasicDialog(title="Custom route"), barrier_dismissible=False)

    with pytest.raises(RuntimeError, match=r"No overlay intent is registered: OverlayRoute"):
        overlay.dialog(route, dismiss_on_outside_tap=False)


def test_overlay_loading_returns_handle() -> None:
    overlay = MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i)})

    handle = overlay.loading()
    assert overlay.has_entries() is True
    handle.close(None)
    assert overlay.has_entries() is False


def test_overlay_while_loading_context_closes_on_exit() -> None:
    overlay = MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i)})

    with overlay.while_loading():
        assert overlay.has_entries() is True

    assert overlay.has_entries() is False


def test_overlay_while_loading_async_context_closes_on_exception() -> None:
    overlay = MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i)})

    async def run() -> None:
        with pytest.raises(RuntimeError, match="boom"):
            async with overlay.while_loading():
                assert overlay.has_entries() is True
                raise RuntimeError("boom")

        assert overlay.has_entries() is False

    asyncio.run(run())
