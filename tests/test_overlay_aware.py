"""Tests for OverlayAware mixin auto-injection."""

from __future__ import annotations

import pytest

from nuiitivet.layout.container import Container
from nuiitivet.overlay import DialogRoute, Overlay, OverlayAware, OverlayHandle
from nuiitivet.widgeting.widget import ComposableWidget, Widget


class _AwareDialog(ComposableWidget, OverlayAware[str]):
    def build(self) -> Widget:
        return Container(width=10, height=10)


def test_overlay_aware_injected_on_show_modal() -> None:
    overlay = Overlay()
    dialog = _AwareDialog()

    handle = overlay.show_modal(dialog, dismiss_on_outside_tap=False)

    assert dialog.overlay_handle is handle


def test_overlay_aware_injected_on_show_modeless() -> None:
    overlay = Overlay()
    dialog = _AwareDialog()

    handle = overlay.show_modeless(dialog)

    assert dialog.overlay_handle is handle


def test_overlay_aware_injected_on_show_light_dismiss() -> None:
    overlay = Overlay()
    dialog = _AwareDialog()

    handle = overlay.show_light_dismiss(dialog)

    assert dialog.overlay_handle is handle


def test_overlay_aware_injected_when_passed_via_route() -> None:
    overlay = Overlay()
    dialog = _AwareDialog()
    route = DialogRoute(builder=lambda: dialog)

    handle = overlay.show_modal(route, dismiss_on_outside_tap=False)

    assert dialog.overlay_handle is handle


def test_overlay_aware_close_via_handle() -> None:
    overlay = Overlay()
    dialog = _AwareDialog()

    overlay.show_modal(dialog, dismiss_on_outside_tap=False)
    dialog.overlay_handle.close("done")

    assert dialog.overlay_handle.done() is True
    result = dialog.overlay_handle.result()
    assert result is not None
    assert result.value == "done"


def test_overlay_handle_raises_before_display() -> None:
    dialog = _AwareDialog()

    with pytest.raises(RuntimeError, match="not available yet"):
        _ = dialog.overlay_handle


def test_overlay_aware_concurrent_display_raises() -> None:
    overlay = Overlay()
    dialog = _AwareDialog()

    overlay.show_modal(dialog, dismiss_on_outside_tap=False)

    with pytest.raises(RuntimeError, match="already attached"):
        overlay.show_modal(dialog, dismiss_on_outside_tap=False)


def test_overlay_aware_redisplay_after_close_allowed() -> None:
    overlay = Overlay()
    dialog = _AwareDialog()

    first = overlay.show_modal(dialog, dismiss_on_outside_tap=False)
    first.close(None)

    second = overlay.show_modal(dialog, dismiss_on_outside_tap=False)

    assert dialog.overlay_handle is second


def test_non_overlay_aware_widget_unaffected() -> None:
    overlay = Overlay()
    widget = Container(width=10, height=10)

    # Should not raise and should return a usable handle.
    handle = overlay.show_modal(widget, dismiss_on_outside_tap=False)

    assert isinstance(handle, OverlayHandle)
