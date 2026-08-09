"""Tests for the two-axis ``Overlay.show`` API."""

import asyncio

from nuiitivet.layout.stack import Stack
from nuiitivet.input.codes import BUTTON_MIDDLE, BUTTON_RIGHT
from nuiitivet.input.pointer import PointerEventType
from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.modifiers._hit_participation import HitParticipationBox
from nuiitivet.overlay.overlay_route import OverlayRoute
from nuiitivet.modifiers.passthrough_pointer import PassthroughPointerBox
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.result import OverlayDismissReason
from nuiitivet.overlay.result import OverlayResult
from nuiitivet.navigation import Route
from nuiitivet.layout.container import Container
from nuiitivet.modifiers.clickable import clickable
from nuiitivet.material.buttons import Button
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.interaction import InteractionRegion
from nuiitivet.material import ButtonStyle

from tests.helpers.pointer import send_pointer_event_for_test_via_app_routing


def _find_descendant_box(widget: Widget) -> HitParticipationBox | None:
    if isinstance(widget, HitParticipationBox):
        return widget
    for child in widget.children:
        if isinstance(child, Widget):
            found = _find_descendant_box(child)
            if found is not None:
                return found
    return None


def _is_descendant_of(widget: Widget, ancestor: Widget) -> bool:
    current: Widget | None = widget
    while current is not None:
        if current is ancestor:
            return True
        current = getattr(current, "_parent", None)
    return False


def _overlay_root(overlay: Overlay) -> Stack:
    """Lay out *overlay* alone at 800x600 and return the root."""
    root = Stack(children=[overlay], alignment="center")
    root.mount(None)
    root.layout(800, 600)
    return root


def _layered_root(overlay: Overlay, behind: Widget) -> Stack:
    """Lay out *overlay* stacked over *behind*, both filling 800x600."""
    behind.width_sizing = Sizing.weight(100)
    behind.height_sizing = Sizing.weight(100)
    overlay.width_sizing = Sizing.weight(100)
    overlay.height_sizing = Sizing.weight(100)

    root = Stack(children=[behind, overlay], alignment="center")
    root.mount(None)
    root.layout(800, 600)
    root.set_layout_rect(0, 0, 800, 600)
    return root


def test_overlay_show_stacks_backdrop_then_blocker_then_content() -> None:
    overlay = Overlay()
    dialog = BasicDialog(title="Title", message="Body")

    overlay.show(dialog, backdrop=True)

    assert overlay.has_entries() is True
    entry = next(iter(overlay._entry_to_route.keys()))
    built = entry.build_widget()

    # The core does the stacking: backdrop (click-through), then its blocking
    # layer, then the composer's positioned content on top.
    assert isinstance(built, Stack)
    layers = built.children_snapshot()
    assert len(layers) == 3
    assert isinstance(layers[0], PassthroughPointerBox)

    current = layers[-1]
    found_dialog = False
    for _ in range(4):
        nested = current.children_snapshot()
        if len(nested) != 1:
            break
        child = nested[0]
        if child is dialog:
            found_dialog = True
            break
        current = child

    assert found_dialog is True


def test_overlay_show_without_backdrop_has_no_painted_layer() -> None:
    """``backdrop=False`` still blocks: the blocker is invisible, not absent."""
    overlay = Overlay()
    overlay.show(BasicDialog(title="Title"))

    entry = next(iter(overlay._entry_to_route.keys()))
    built = entry.build_widget()

    assert isinstance(built, Stack)
    layers = built.children_snapshot()
    # Blocker + content only; nothing painted.
    assert len(layers) == 2
    assert not any(isinstance(layer, PassthroughPointerBox) for layer in layers)
    assert _find_descendant_box(layers[0]) is not None


def test_overlay_passthrough_entry_is_the_composed_content_alone() -> None:
    """No blocker, no backdrop: nothing is stacked around the content."""
    overlay = Overlay()
    overlay.show(BasicDialog(title="Title"), passthrough=True)

    entry = next(iter(overlay._entry_to_route.keys()))
    assert _find_descendant_box(entry.build_widget()) is None


def test_overlay_content_is_last_child_so_it_is_hit_tested_first() -> None:
    """Ordering regression: the content must be the *last* child.

    ``_hit_test_children`` walks ``reversed(children)``, so the content is
    tested first and the blocker catches only what the content declined.
    Reversed, the blocker would swallow clicks meant for the overlay content.
    """
    clicked: list[bool] = []

    overlay = Overlay()
    ok_button = Button("OK", on_click=lambda: clicked.append(True), style=ButtonStyle.filled())
    dialog = BasicDialog(title="Title", message="Body", actions=[ok_button])
    overlay.show(dialog, backdrop=True, dismiss_on_outside_tap=True)

    root = _overlay_root(overlay)

    entry = next(iter(overlay._entry_to_route.keys()))
    layers = entry.build_widget().children_snapshot()
    assert _find_descendant_box(layers[-2]) is not None, "the blocker must sit directly under the content"

    rect = ok_button.global_layout_rect
    assert rect is not None
    x, y, w, h = rect
    cx, cy = x + w // 2, y + h // 2

    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, cx, cy) is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, cx, cy) is True
    assert clicked == [True]
    # The content click must not have tripped outside-tap dismissal.
    assert overlay.has_entries() is True


def test_overlay_blocker_interaction_region_is_outside_the_hit_participation_box() -> None:
    """Ordering regression: ``block_pointer()`` must sit inside ``clickable()``.

    ``clickable`` does not wrap — it returns ``ensure_interaction_region(widget)``
    — and pointer bubbling walks parents only. So the region has to be an
    *ancestor* of the ``HitParticipationBox`` that is the actual hit target.
    Reversed, the region would be the box's child and would never see the event.
    """
    overlay = Overlay()
    overlay.show(BasicDialog(title="Title"), dismiss_on_outside_tap=True)

    entry = next(iter(overlay._entry_to_route.keys()))
    blocker = entry.build_widget().children_snapshot()[-2]

    # The region is the outermost widget of the blocking layer, and the box that
    # actually catches the hit lives underneath it.
    assert isinstance(blocker, InteractionRegion)
    assert _find_descendant_box(blocker) is not None, "the HitParticipationBox must be inside the region"


def test_overlay_show_dismiss_on_outside_tap_false_swallows_the_tap() -> None:
    """Without dismissal the layer still blocks: the tap neither closes nor passes."""
    clicked: list[bool] = []

    bg = Container(width="wt", height="wt").modifier(clickable(on_click=lambda: clicked.append(True)))
    overlay = Overlay()
    overlay.show(BasicDialog(title="Title"), backdrop=True)

    root = _layered_root(overlay, bg)

    assert overlay.has_entries() is True
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, 5, 5)
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, 5, 5)
    assert overlay.has_entries() is True
    assert clicked == []


def test_overlay_show_dismiss_on_outside_tap_closes_on_outside_tap() -> None:
    overlay = Overlay()
    overlay.show(BasicDialog(title="Title"), backdrop=True, dismiss_on_outside_tap=True)

    root = _overlay_root(overlay)

    assert overlay.has_entries() is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, 5, 5) is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, 5, 5) is True
    assert overlay.has_entries() is False


def test_overlay_outside_tap_dismisses_on_secondary_and_middle_button() -> None:
    """Issue #506: dismissal is not gated on the primary button."""
    for button in (BUTTON_RIGHT, BUTTON_MIDDLE):
        overlay = Overlay()
        overlay.show(BasicDialog(title="Title"), dismiss_on_outside_tap=True)
        root = _overlay_root(overlay)

        assert overlay.has_entries() is True
        send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, 5, 5, button=button)
        send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, 5, 5, button=button)
        assert overlay.has_entries() is False, f"button={button} did not dismiss"


def test_overlay_passthrough_allows_background_press() -> None:
    clicked: list[bool] = []

    bg = Container(width="wt", height="wt").modifier(clickable(on_click=lambda: clicked.append(True)))
    overlay = Overlay()
    overlay.show(BasicDialog(title="Title"), passthrough=True)

    root = _layered_root(overlay, bg)

    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, 5, 5) is True
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, 5, 5) is True
    assert clicked == [True]


def test_overlay_blocking_entry_blocks_background_press_hover_and_wheel() -> None:
    """A ``passthrough=False`` entry blocks every pointer kind, not just press.

    ``dispatch_mouse_press`` / ``dispatch_mouse_motion`` / ``dispatch_mouse_scroll``
    all resolve their target through ``hit_test``, so a layer that wins the
    hit test covers all three at once.
    """
    pressed: list[bool] = []
    hovered: list[bool] = []

    bg = Container(width="wt", height="wt").modifier(clickable(on_click=lambda: pressed.append(True)))
    assert isinstance(bg, InteractionRegion)
    bg.enable_hover(on_change=lambda value: hovered.append(value))

    overlay = Overlay()
    overlay.show(BasicDialog(title="Title"))

    root = _layered_root(overlay, bg)

    # The single hit target behind every pointer kind is the overlay's blocker,
    # never the background.
    target = root.hit_test(5, 5)
    assert target is not None
    assert not _is_descendant_of(target, bg)

    send_pointer_event_for_test_via_app_routing(root, PointerEventType.PRESS, 5, 5)
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.RELEASE, 5, 5)
    send_pointer_event_for_test_via_app_routing(root, PointerEventType.HOVER, 5, 5)
    assert send_pointer_event_for_test_via_app_routing(root, PointerEventType.SCROLL, 5, 5, scroll_y=1.0) is False

    assert pressed == []
    assert True not in hovered


def test_overlay_passthrough_with_explicit_dismiss_on_outside_tap_raises() -> None:
    overlay = Overlay()
    try:
        overlay.show(BasicDialog(title="Title"), passthrough=True, dismiss_on_outside_tap=True)
    except ValueError as exc:
        assert "#508" in str(exc)
    else:
        raise AssertionError("expected ValueError for the unimplementable fourth cell")


def test_overlay_dialog_ok_button_clickable_via_app_routing() -> None:
    clicked: list[bool] = []

    def on_ok() -> None:
        clicked.append(True)

    overlay = Overlay()
    ok_button = Button("OK", on_click=on_ok, style=ButtonStyle.filled())
    dialog = BasicDialog(title="Title", message="Body", actions=[ok_button])

    overlay.show(dialog, backdrop=True)

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


def test_overlay_dialog_route_is_disposed_on_close_topmost() -> None:
    overlay = Overlay()

    route = Route(builder=lambda: BasicDialog(title="Title"))
    overlay.show(route, backdrop=True)

    # Route widget is created eagerly by Overlay.show().
    assert route._widget is not None

    overlay.close_topmost()
    assert route._widget is None


def test_overlay_dialog_async_resolves_with_close_result() -> None:
    overlay = Overlay()

    async def run() -> OverlayResult[bool]:
        handle = overlay.show(BasicDialog(title="Title"), backdrop=True)
        await asyncio.sleep(0)
        handle.close(True)
        return await handle

    result = asyncio.run(run())
    assert result.value is True
    assert result.reason is OverlayDismissReason.CLOSED


def test_overlay_dialog_async_resolves_none_on_close_without_result() -> None:
    overlay = Overlay()

    async def run() -> OverlayResult[None]:
        handle = overlay.show(BasicDialog(title="Title"), backdrop=True)
        await asyncio.sleep(0)
        handle.close()
        return await handle

    result = asyncio.run(run())
    assert result.value is None
    assert result.reason is OverlayDismissReason.CLOSED


def test_overlay_show_widget_and_route_have_disposal_parity() -> None:
    class _UnmountCountWidget(Widget):
        def __init__(self) -> None:
            super().__init__()
            self.unmount_count = 0

        def on_unmount(self) -> None:
            self.unmount_count += 1
            super().on_unmount()

        def build(self) -> Widget:
            return self

    overlay_widget = Overlay()
    widget_input = _UnmountCountWidget()
    overlay_widget.show(widget_input, backdrop=True)
    overlay_widget.close_topmost()

    assert overlay_widget.has_entries() is False
    assert widget_input.unmount_count == 1

    overlay_route = Overlay()
    route_widget = _UnmountCountWidget()
    route_input = OverlayRoute(builder=lambda: route_widget)
    overlay_route.show(route_input, backdrop=True)
    overlay_route.close_topmost()

    assert overlay_route.has_entries() is False
    assert route_widget.unmount_count == 1
    assert route_input._widget is None  # type: ignore[attr-defined]
