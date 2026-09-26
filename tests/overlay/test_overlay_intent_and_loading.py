"""Tests for Overlay intent resolution and loading context manager."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.material.loading_indicator import LoadingIndicator
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.material.transition_spec import MaterialTransitions
from nuiitivet.overlay.intents import LoadingDialogIntent
from nuiitivet.overlay.dialogs import PlainLoadingDialog
from nuiitivet.transition.spec import EmptyTransitionSpec


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
    route = next(iter(overlay._entry_to_layer.values()))
    assert not isinstance(route.transition_spec, EmptyTransitionSpec)


def test_overlay_dialog_unknown_intent_raises() -> None:
    overlay = MaterialOverlay(intents={})

    with pytest.raises(RuntimeError, match=r"No overlay intent is registered: _ConfirmIntent"):
        overlay.dialog(_ConfirmIntent("x"), dismiss_on_outside_tap=False)


def test_material_overlay_dialog_shows_widget_with_dialog_transition() -> None:
    overlay = MaterialOverlay(intents={})
    widget = BasicDialog(title="Widget dialog")

    overlay.dialog(widget, dismiss_on_outside_tap=False)

    route = next(iter(overlay._entry_to_layer.values()))
    assert route._content_widget is widget
    assert not isinstance(route.transition_spec, EmptyTransitionSpec)


def test_material_overlay_default_loading_has_no_transition() -> None:
    overlay = MaterialOverlay()

    overlay.loading()

    route = next(iter(overlay._entry_to_layer.values()))
    assert isinstance(route._content_widget, LoadingIndicator)
    assert isinstance(route.transition_spec, EmptyTransitionSpec)


def test_overlay_show_transition_does_not_carry_to_next_show() -> None:
    overlay = MaterialOverlay(intents={})

    overlay.show(BasicDialog(title="First"), transition=MaterialTransitions.dialog())
    overlay.show(BasicDialog(title="Second"))

    first, second = overlay._entry_to_layer.values()
    assert not isinstance(first.transition_spec, EmptyTransitionSpec)
    assert isinstance(second.transition_spec, EmptyTransitionSpec)


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
