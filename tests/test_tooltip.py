"""Tests for tooltip widgets, styles, and modifier."""

from __future__ import annotations

from typing import Optional, Tuple

from nuiitivet.input.pointer import PointerEvent, PointerEventType, PointerType
from nuiitivet.material.tooltip import RichTooltip, Tooltip
from nuiitivet.material.styles.tooltip_style import RichTooltipStyle, TooltipStyle
from nuiitivet.modifiers.tooltip import TooltipBox, TooltipModifier, tooltip
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.interaction import FocusNode, InteractionRegion
from nuiitivet.widgets.box import Box


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


def test_tooltip_style_defaults_and_copy_with() -> None:
    style = TooltipStyle.standard()
    assert style.container_color is not None
    assert style.content_color is not None
    assert style.corner_radius == 4

    updated = style.copy_with(corner_radius=8)
    assert updated.corner_radius == 8
    assert style.corner_radius == 4


def test_tooltip_style_from_theme_returns_style_instance() -> None:
    from nuiitivet.theme.theme import Theme

    resolved = TooltipStyle.from_theme(Theme(mode="light", extensions=[]))
    assert isinstance(resolved, TooltipStyle)


def test_rich_tooltip_style_defaults_and_copy_with() -> None:
    style = RichTooltipStyle.standard()
    assert style.corner_radius == 12
    assert style.action_color is not None

    updated = style.copy_with(corner_radius=16)
    assert updated.corner_radius == 16
    assert style.corner_radius == 12


def test_rich_tooltip_style_from_theme_returns_style_instance() -> None:
    from nuiitivet.theme.theme import Theme

    resolved = RichTooltipStyle.from_theme(Theme(mode="light", extensions=[]))
    assert isinstance(resolved, RichTooltipStyle)


def test_tooltip_build_returns_box() -> None:
    widget = Tooltip("Copy")
    built = widget.build()
    assert isinstance(built, Box)


def test_rich_tooltip_build_returns_box() -> None:
    widget = RichTooltip(
        "Supporting text",
        subhead="Title",
        action_label="Action",
        action_label_2="Dismiss",
    )
    built = widget.build()
    assert isinstance(built, Box)


def test_tooltip_box_hover_opens_and_closes_immediately_when_delay_is_zero() -> None:
    box = TooltipBox(_FixedWidget(10, 10), _FixedWidget(20, 20), delay=0.0, dismiss_delay=0.0)

    box._on_hover_change(True)
    assert box._is_open.value is True

    box._on_hover_change(False)
    assert box._is_open.value is False


def test_tooltip_box_hover_schedules_open_and_close() -> None:
    box = TooltipBox(_FixedWidget(10, 10), _FixedWidget(20, 20), delay=0.2, dismiss_delay=0.3)

    box._on_hover_change(True)
    assert box._open_callback is not None

    box._on_hover_change(False)
    assert box._open_callback is None
    assert box._close_callback is not None


def test_tooltip_box_touch_press_release_tracks_pointer() -> None:
    box = TooltipBox(_FixedWidget(10, 10), _FixedWidget(20, 20), delay=0.1, dismiss_delay=0.1)

    press = PointerEvent(
        id=7,
        type=PointerEventType.PRESS,
        x=1.0,
        y=1.0,
        pointer_type=PointerType.TOUCH,
    )
    release = PointerEvent(
        id=7,
        type=PointerEventType.RELEASE,
        x=1.0,
        y=1.0,
        pointer_type=PointerType.TOUCH,
    )

    box._on_press(press)
    assert box._active_touch_pointer_id == 7
    assert box._open_callback is not None

    box._on_release(release)
    assert box._active_touch_pointer_id is None
    assert box._close_callback is not None


def test_tooltip_factory_returns_modifier() -> None:
    content = _FixedWidget(20, 20)
    result = tooltip(content)
    assert isinstance(result, TooltipModifier)
    assert result.alignment == "top-center"
    assert result.anchor == "bottom-center"
    assert result.offset == (0.0, -4.0)


def test_tooltip_modifier_apply_returns_tooltip_box() -> None:
    anchor = _FixedWidget(10, 10)
    content = _FixedWidget(20, 20)
    result = tooltip(content).apply(anchor)
    assert isinstance(result, TooltipBox)


def test_tooltip_modifier_wraps_anchor_with_interaction_region_for_hover() -> None:
    anchor = _FixedWidget(10, 10)
    content = _FixedWidget(20, 20)
    result = tooltip(content, delay=0.0, dismiss_delay=0.0).apply(anchor)

    assert isinstance(result, TooltipBox)
    assert isinstance(result._child, InteractionRegion)

    enter = PointerEvent(
        id=1,
        type=PointerEventType.ENTER,
        x=0.0,
        y=0.0,
        pointer_type=PointerType.MOUSE,
    )
    leave = PointerEvent(
        id=1,
        type=PointerEventType.LEAVE,
        x=0.0,
        y=0.0,
        pointer_type=PointerType.MOUSE,
    )

    result._child.on_pointer_event(enter)
    assert result._is_open.value is True

    result._child.on_pointer_event(leave)
    assert result._is_open.value is False


def test_tooltip_modifier_binds_directly_to_interactive_anchor() -> None:
    anchor = Clickable(child=_FixedWidget(10, 10))
    content = _FixedWidget(20, 20)
    result = tooltip(content, delay=0.0, dismiss_delay=0.0).apply(anchor)

    assert isinstance(result, TooltipBox)
    # For interactive widgets, tooltip should attach to the anchor itself.
    assert result._child is anchor

    enter = PointerEvent(
        id=1,
        type=PointerEventType.ENTER,
        x=0.0,
        y=0.0,
        pointer_type=PointerType.MOUSE,
    )
    leave = PointerEvent(
        id=1,
        type=PointerEventType.LEAVE,
        x=0.0,
        y=0.0,
        pointer_type=PointerType.MOUSE,
    )

    anchor.on_pointer_event(enter)
    assert result._is_open.value is True

    anchor.on_pointer_event(leave)
    assert result._is_open.value is False


def test_tooltip_modifier_restores_focus_callback_on_unmount() -> None:
    anchor = Clickable(child=_FixedWidget(10, 10))
    focus_node = anchor.get_node(FocusNode)
    assert isinstance(focus_node, FocusNode)
    before_callback = focus_node._on_focus_change

    result = tooltip(_FixedWidget(20, 20)).apply(anchor)
    assert isinstance(result, TooltipBox)
    assert focus_node._on_focus_change is not before_callback

    result.on_unmount()
    assert focus_node._on_focus_change is before_callback


def test_tooltip_exported_from_modifiers() -> None:
    import nuiitivet.modifiers as m

    assert hasattr(m, "tooltip")
    assert "tooltip" in m.__all__


def test_tooltip_widgets_exported_from_material() -> None:
    import nuiitivet.material as m

    assert hasattr(m, "Tooltip")
    assert hasattr(m, "RichTooltip")
    assert "Tooltip" in m.__all__
    assert "RichTooltip" in m.__all__


def test_tooltip_does_not_suppress_existing_press_handler() -> None:
    """Applying tooltip() must not override existing on_press/on_release handlers."""
    press_calls: list[PointerEvent] = []
    release_calls: list[PointerEvent] = []

    anchor = Clickable(
        child=_FixedWidget(10, 10),
        on_press=lambda e: press_calls.append(e),
        on_release=lambda e: release_calls.append(e),
    )
    tooltip(_FixedWidget(20, 20), delay=0.0, dismiss_delay=0.0).apply(anchor)

    press = PointerEvent(id=1, type=PointerEventType.PRESS, x=5.0, y=5.0, pointer_type=PointerType.MOUSE)
    release = PointerEvent(id=1, type=PointerEventType.RELEASE, x=5.0, y=5.0, pointer_type=PointerType.MOUSE)

    anchor.on_pointer_event(press)
    anchor.on_pointer_event(release)

    assert len(press_calls) == 1
    assert len(release_calls) == 1


def test_tooltip_hover_listener_not_accumulated_across_mount_unmount() -> None:
    """Repeated mount/unmount must not cause duplicate hover callback executions."""
    anchor = Clickable(child=_FixedWidget(10, 10))
    content = _FixedWidget(20, 20)

    result1 = tooltip(content, delay=0.0, dismiss_delay=0.0).apply(anchor)
    assert isinstance(result1, TooltipBox)
    result1.on_unmount()

    result2 = tooltip(content, delay=0.0, dismiss_delay=0.0).apply(anchor)
    assert isinstance(result2, TooltipBox)

    # Trigger hover; only result2's callback should fire (result1 was unsubscribed)
    enter = PointerEvent(id=1, type=PointerEventType.ENTER, x=0.0, y=0.0, pointer_type=PointerType.MOUSE)
    anchor.on_pointer_event(enter)

    assert result1._is_open.value is False
    assert result2._is_open.value is True


def test_tooltip_uninstall_stops_hover_after_unmount() -> None:
    """After on_unmount, hover events must not trigger tooltip open."""
    anchor = Clickable(child=_FixedWidget(10, 10))
    result = tooltip(_FixedWidget(20, 20), delay=0.0, dismiss_delay=0.0).apply(anchor)
    assert isinstance(result, TooltipBox)

    result.on_unmount()

    enter = PointerEvent(id=1, type=PointerEventType.ENTER, x=0.0, y=0.0, pointer_type=PointerType.MOUSE)
    anchor.on_pointer_event(enter)

    assert result._is_open.value is False


def test_schedule_close_cancels_pending_open_when_externally_closed_and_focused_stale() -> None:
    """Regression: ESC sets _is_open=False externally; mouse-leave must still cancel pending open.

    Bug #138: When _is_focused is stale True (from pointer-click, see #137),
    the old guard ``if _is_hovered or _is_focused: return`` would short-circuit
    _cancel_open(), leaving the pending callback alive. After the timer fires,
    _set_open(True) re-opens the tooltip even though ESC had dismissed it.

    Fix: guard is now ``if _is_open.value and (_is_hovered or _is_focused)``,
    so an already-closed tooltip always proceeds to _cancel_open().
    """
    box = TooltipBox(_FixedWidget(10, 10), _FixedWidget(20, 20), delay=0.5, dismiss_delay=0.0)

    # Hover starts a pending open (delay=0.5 so it stays scheduled).
    box._on_hover_change(True)
    assert box._open_callback is not None

    # Simulate pointer-click setting _is_focused=True (#137 bug).
    box._is_focused = True

    # ESC dismisses the overlay externally — bypasses _set_open().
    box._is_open.value = False

    # Mouse leaves the button.
    box._on_hover_change(False)

    # The pending open callback must be cancelled; tooltip must stay closed.
    assert box._open_callback is None
    assert box._is_open.value is False


def test_tooltip_esc_suppresses_reopen_while_hovered() -> None:
    """After ESC dismissal, pointer movement within the button must not reopen the tooltip.

    When the pointer crosses internal sub-widget boundaries the InteractionRegion
    emits a hover=False then hover=True pair within the same dispatch cycle.
    The tooltip must ignore the hover=True while _user_dismissed is set.

    This test sets state directly to avoid triggering _schedule_dismiss_reset,
    which uses a background timer that would introduce a threading race condition.
    The deferred-reset path is covered by test_tooltip_esc_suppression_clears_after_pointer_leaves.
    """
    box = TooltipBox(_FixedWidget(10, 10), _FixedWidget(20, 20), delay=0.5, dismiss_delay=0.5)

    # Simulate: tooltip is open while the pointer hovers over the anchor widget.
    box._is_hovered = True
    box._is_open.value = True

    # ESC closes externally — mirrors what the handle monitor does.
    box._on_closed_externally()
    box._is_open.value = False
    assert box._user_dismissed is True

    # ENTER fires again (sub-widget crossing; deferred reset has not yet fired).
    box._on_hover_change(True)

    # No open should be scheduled while _user_dismissed is still set.
    assert box._open_callback is None
    assert box._is_open.value is False
    assert box._user_dismissed is True


def test_tooltip_esc_suppression_clears_after_pointer_leaves() -> None:
    """_user_dismissed resets once the pointer genuinely leaves the button.

    The reset is deferred to the next frame so that a sub-widget crossing does
    not clear the flag.  When the pointer truly leaves, the deferred callback
    fires and clears _user_dismissed so the next re-entry reopens normally.

    The observable runtime clock is replaced with a no-op during the test to
    prevent _ThreadClock from racing the assertions via background threads.
    """
    import types
    from nuiitivet.observable import runtime as _observable_runtime

    box = TooltipBox(_FixedWidget(10, 10), _FixedWidget(20, 20), delay=0.0, dismiss_delay=0.5)

    # Simulate: ESC dismissed while hovered.
    box._is_hovered = True
    box._is_open.value = True
    box._on_closed_externally()
    box._is_open.value = False

    # Replace clock with a no-op so that schedule_once never fires in the
    # background, allowing the assertions below to be deterministic.
    _prev_clock = _observable_runtime.clock
    _observable_runtime.set_clock(
        types.SimpleNamespace(
            schedule_once=lambda fn, d: None,
            unschedule=lambda fn: None,
            schedule_interval=lambda fn, i: None,
        )
    )
    try:
        # Pointer leaves the button with no subsequent hover=True.
        box._on_hover_change(False)
        assert box._dismiss_reset_callback is not None

        # Simulate next-frame deferred callback firing.
        box._dismiss_reset_callback(0.0)
        assert box._user_dismissed is False

        # Re-entering the button now opens the tooltip normally.
        box._on_hover_change(True)
        assert box._is_open.value is True
    finally:
        _observable_runtime.set_clock(_prev_clock)
