"""Tests for Overlay intent resolution and loading context manager."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.overlay.intents import LoadingDialogIntent
from nuiitivet.overlay.dialogs import PlainLoadingDialog
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.theme.manager import manager
from nuiitivet.material.theme.material_theme import MaterialTheme


@pytest.fixture(autouse=True)
def material_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))


@dataclass(frozen=True, slots=True)
class _ConfirmIntent:
    message: str


def test_overlay_dialog_intent_resolves_to_widget() -> None:
    overlay = MaterialOverlay(
        intents={
            _ConfirmIntent: lambda i: AlertDialog(title=Text("Confirm"), content=Text(i.message)),
        }
    )

    overlay.dialog(_ConfirmIntent("hi"), dismiss_on_outside_tap=False)

    assert overlay.has_entries() is True


def test_overlay_dialog_intent_resolves_to_route() -> None:
    from nuiitivet.navigation.route import Route

    overlay = MaterialOverlay(
        intents={
            _ConfirmIntent: lambda i: Route(builder=lambda: AlertDialog(title=Text(i.message))),
        }
    )

    overlay.dialog(_ConfirmIntent("Confirm"), dismiss_on_outside_tap=False)
    assert overlay.has_entries() is True


def test_overlay_dialog_unknown_intent_raises() -> None:
    overlay = MaterialOverlay(intents={})

    with pytest.raises(RuntimeError, match=r"No overlay intent is registered: _ConfirmIntent"):
        overlay.dialog(_ConfirmIntent("x"), dismiss_on_outside_tap=False)


def test_overlay_loading_context_closes_on_exit() -> None:
    overlay = MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i)})

    with overlay.loading():
        assert overlay.has_entries() is True

    assert overlay.has_entries() is False


def test_overlay_loading_async_context_closes_on_exception() -> None:
    overlay = MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i)})

    async def run() -> None:
        with pytest.raises(RuntimeError, match="boom"):
            async with overlay.loading():
                assert overlay.has_entries() is True
                raise RuntimeError("boom")

        assert overlay.has_entries() is False

    asyncio.run(run())
