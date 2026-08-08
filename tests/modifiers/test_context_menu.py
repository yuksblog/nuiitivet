"""Tests for the ``context_menu()`` modifier (issue #424).

A context menu differs from ``modeless()`` / ``light_dismiss()`` in that it owns
both the open state and the transient click coordinate. These tests pin that
contract: it opens only on the secondary button, at the pointer's *screen*
position, and it follows a second click to a new point.
"""

from __future__ import annotations

from typing import Optional, Tuple

import nuiitivet as nv
from nuiitivet.input.codes import BUTTON_LEFT, BUTTON_RIGHT
from nuiitivet.input.pointer import PointerEvent, PointerEventType as T
from nuiitivet.modifiers.context_menu import ContextMenuBox, ContextMenuModifier, context_menu
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import InteractionHostMixin, PointerListenerNode


class _FixedWidget(Widget):
    """Widget with a fixed preferred size for testing."""

    def __init__(self, pref_w: int = 0, pref_h: int = 0) -> None:
        super().__init__()
        self._pref_w = int(pref_w)
        self._pref_h = int(pref_h)

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        return (self._pref_w, self._pref_h)


def _wrap(menu: Widget) -> ContextMenuBox:
    child = Box(width=Sizing.fixed(100), height=Sizing.fixed(50))
    box = context_menu(menu).apply(child)
    assert isinstance(box, ContextMenuBox)
    return box


def _press(box: ContextMenuBox, x: float, y: float, button: int) -> None:
    """Press inside the host. The rect spans the viewport so any point lands on it."""
    host = box._child
    assert isinstance(host, InteractionHostMixin)
    host.set_last_rect(0, 0, 800, 600)
    host.on_pointer_event(PointerEvent.mouse_event(1, T.PRESS, x, y, button=button))


# ---------------------------------------------------------------------------
# Factory / wiring
# ---------------------------------------------------------------------------


def test_exported_from_modifiers_and_root() -> None:
    from nuiitivet.modifiers import context_menu as from_modifiers

    assert nv.context_menu is from_modifiers


def test_factory_returns_modifier_with_defaults() -> None:
    modifier = context_menu(_FixedWidget(10, 10))
    assert isinstance(modifier, ContextMenuModifier)
    assert modifier.content_anchor == "top-left"
    assert modifier.offset == (0.0, 0.0)


def test_apply_wraps_the_widget_in_an_interaction_host() -> None:
    box = _wrap(_FixedWidget(120, 90))
    assert isinstance(box._child, InteractionHostMixin)
    assert isinstance(box._child.get_node(PointerListenerNode), PointerListenerNode)


def test_menu_closes_on_outside_tap() -> None:
    """A context menu is always light-dismiss; clicking away closes it."""
    box = _wrap(_FixedWidget(120, 90))
    assert box._light_dismiss is True


# ---------------------------------------------------------------------------
# Opening at the pointer
# ---------------------------------------------------------------------------


def test_no_anchor_rect_before_any_click() -> None:
    box = _wrap(_FixedWidget(120, 90))
    assert box._rect_provider() is None
    assert box.is_open.value is False


def test_secondary_press_opens_at_a_zero_size_rect_on_the_point() -> None:
    box = _wrap(_FixedWidget(120, 90))
    _press(box, 240, 310, BUTTON_RIGHT)

    assert box.is_open.value is True
    assert box._rect_provider() == (240, 310, 0, 0)


def test_primary_press_does_not_open_the_menu() -> None:
    box = _wrap(_FixedWidget(120, 90))
    _press(box, 240, 310, BUTTON_LEFT)

    assert box.is_open.value is False
    assert box._rect_provider() is None


def test_uses_screen_coordinates_not_widget_local_ones() -> None:
    """The host rect is at (0, 0) here, so a divergence would be invisible.

    Offsetting the host makes screen and local coordinates differ: the menu must
    follow the screen pair, since the overlay root is not the host.
    """
    box = _wrap(_FixedWidget(120, 90))
    host = box._child
    assert isinstance(host, InteractionHostMixin)
    host.set_last_rect(50, 80, 100, 50)
    host.on_pointer_event(PointerEvent.mouse_event(1, T.PRESS, 90, 120, button=BUTTON_RIGHT))

    # local would be (40, 40); screen is (90, 120).
    assert box._rect_provider() == (90, 120, 0, 0)


def test_reopening_uses_the_newer_click_point() -> None:
    """The anchor is re-read from the latest press, not frozen at the first one.

    In the running app the light-dismiss layer means a close comes between the
    two presses; the box must not cache the stale point across that.
    """
    box = _wrap(_FixedWidget(120, 90))
    _press(box, 100, 100, BUTTON_RIGHT)
    assert box._rect_provider() == (100, 100, 0, 0)

    box.is_open.value = False
    _press(box, 400, 350, BUTTON_RIGHT)

    assert box.is_open.value is True
    assert box._rect_provider() == (400, 350, 0, 0)


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------


def test_menu_hangs_down_right_of_the_click_by_default() -> None:
    menu = _FixedWidget(120, 90)
    box = _wrap(menu)
    _press(box, 200, 150, BUTTON_RIGHT)

    from nuiitivet.overlay.overlay_position import OverlayPosition

    placed = OverlayPosition.anchored(
        box._rect_provider,
        target_anchor=box._target_anchor,
        content_anchor=box._content_anchor,
        offset=box._offset,
    ).make_position_content(menu)
    placed.layout(800, 600)

    assert menu.layout_rect == (200, 150, 120, 90)


def test_menu_near_the_edge_is_clamped_into_view() -> None:
    menu = _FixedWidget(120, 90)
    box = _wrap(menu)
    _press(box, 790, 590, BUTTON_RIGHT)

    from nuiitivet.overlay.overlay_position import OverlayPosition

    placed = OverlayPosition.anchored(
        box._rect_provider,
        target_anchor=box._target_anchor,
        content_anchor=box._content_anchor,
        offset=box._offset,
    ).make_position_content(menu)
    placed.layout(800, 600)

    assert menu.layout_rect == (680, 510, 120, 90)
