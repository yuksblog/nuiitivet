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
    from nuiitivet.theme.manager import manager

    resolved = TooltipStyle.from_theme(manager.current)
    assert isinstance(resolved, TooltipStyle)


def test_rich_tooltip_style_defaults_and_copy_with() -> None:
    style = RichTooltipStyle.standard()
    assert style.corner_radius == 12
    assert style.action_color is not None

    updated = style.copy_with(corner_radius=16)
    assert updated.corner_radius == 16
    assert style.corner_radius == 12


def test_rich_tooltip_style_from_theme_returns_style_instance() -> None:
    from nuiitivet.theme.manager import manager

    resolved = RichTooltipStyle.from_theme(manager.current)
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
