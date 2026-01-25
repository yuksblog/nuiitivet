"""Tests for Overlay.show()."""

import asyncio

from nuiitivet.layout.stack import Stack
from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.result import OverlayDismissReason
from nuiitivet.overlay.result import OverlayResult
from nuiitivet.navigation import Route
from nuiitivet.layout.container import Container
from nuiitivet.modifiers.clickable import clickable
from nuiitivet.material.buttons import FilledButton
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.theme.manager import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
import pytest

from tests.helpers.pointer import send_pointer_event_for_test_via_app_routing


@pytest.fixture(autouse=True)
def material_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))


def test_overlay_dialog_inserts_entry_with_barrier_and_dialog() -> None:
    overlay = Overlay()
    dialog = AlertDialog(title=Text("Title"), content=Text("Body"))

    overlay.show(dialog, dismiss_on_outside_tap=False)

    assert overlay.has_entries() is True
    entry = next(iter(overlay._entry_to_route.keys()))
    built = entry.build_widget()
    assert isinstance(built, Stack)

    children = built.children_snapshot()
    assert len(children) == 2
    positioned = children[1]
    positioned_children = positioned.children_snapshot()
    assert len(positioned_children) == 1
    assert positioned_children[0] is dialog


def test_overlay_show_dismiss_on_outside_tap_false_does_not_close_on_barrier_click() -> None:
    overlay = Overlay()
    dialog = AlertDialog(title=Text("Title"))

    overlay.show(dialog, dismiss_on_outside_tap=False)

    root = Stack(children=[overlay], alignment="center")
    root.mount(None)
    root.layout(800, 600)

    assert overlay.has_entries() is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, 5, 5) is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, 5, 5) is True
    assert overlay.has_entries() is True


def test_overlay_dialog_ok_button_clickable_via_app_routing() -> None:
    clicked: list[bool] = []

    def on_ok() -> None:
        clicked.append(True)

    overlay = Overlay()
    ok_button = FilledButton("OK", on_click=on_ok)
    dialog = AlertDialog(title=Text("Title"), content=Text("Body"), actions=[ok_button])

    overlay.show(dialog, dismiss_on_outside_tap=False)

    root = Stack(children=[overlay], alignment="center")
    # Mount so BuilderHostMixin builds dialog contents.
    root.mount(None)

    root.layout(800, 600)

    rect = ok_button.global_layout_rect
    assert rect is not None
    x, y, w, h = rect
    cx = x + w // 2
    cy = y + h // 2

    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, cx, cy) is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, cx, cy) is True
    assert clicked == [True]


def test_overlay_dialog_dialogroute_barrier_dismissible_true_closes_on_barrier_click() -> None:
    overlay = Overlay()
    overlay.show(AlertDialog(title=Text("Title")), dismiss_on_outside_tap=True)

    root = Stack(children=[overlay], alignment="center")
    root.mount(None)
    root.layout(800, 600)

    assert overlay.has_entries() is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, 5, 5) is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, 5, 5) is True
    assert overlay.has_entries() is False


def test_overlay_show_passthrough_allows_background_click() -> None:
    clicked: list[bool] = []

    def on_bg() -> None:
        clicked.append(True)

    bg = Container(width="100%", height="100%").modifier(clickable(on_click=on_bg))
    overlay = Overlay()
    overlay.show(AlertDialog(title=Text("Title")), passthrough=True)

    bg.width_sizing = Sizing.flex(100)
    bg.height_sizing = Sizing.flex(100)
    overlay.width_sizing = Sizing.flex(100)
    overlay.height_sizing = Sizing.flex(100)

    root = Stack(children=[bg, overlay], alignment="center")
    root.mount(None)
    root.layout(800, 600)
    root.set_layout_rect(0, 0, 800, 600)

    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, 5, 5) is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, 5, 5) is True
    assert clicked == [True]


def test_overlay_dialog_route_is_disposed_on_close_topmost() -> None:
    overlay = Overlay()

    route = Route(builder=lambda: AlertDialog(title=Text("Title")))
    overlay.show(route, dismiss_on_outside_tap=False)

    # Route widget is created eagerly by Overlay.dialog().
    assert route._widget is not None

    overlay.close_topmost()
    assert route._widget is None


def test_overlay_dialog_async_resolves_with_close_result() -> None:
    overlay = Overlay()

    async def run() -> OverlayResult[bool]:
        handle = overlay.show(AlertDialog(title=Text("Title")), dismiss_on_outside_tap=False)
        await asyncio.sleep(0)
        handle.close(True)
        return await handle

    result = asyncio.run(run())
    assert result.value is True
    assert result.reason is OverlayDismissReason.CLOSED


def test_overlay_dialog_async_resolves_none_on_close_without_result() -> None:
    overlay = Overlay()

    async def run() -> OverlayResult[None]:
        handle = overlay.show(AlertDialog(title=Text("Title")), dismiss_on_outside_tap=False)
        await asyncio.sleep(0)
        handle.close()
        return await handle

    result = asyncio.run(run())
    assert result.value is None
    assert result.reason is OverlayDismissReason.CLOSED
