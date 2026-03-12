"""tooltip() modifier for transient anchored tooltips."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, Tuple

from nuiitivet.input.pointer import PointerEvent, PointerType
from nuiitivet.layout.alignment import AlignmentLike
from nuiitivet.modifiers.popup import PopupBox
from nuiitivet.observable import runtime
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.interaction import (
    FocusNode,
    InteractionHostMixin,
    ensure_interaction_region,
)

if TYPE_CHECKING:
    from nuiitivet.navigation.transition_spec import TransitionSpec


class TooltipBox(PopupBox):
    """PopupBox variant that manages tooltip open/close from interaction events."""

    def __init__(
        self,
        child: Widget,
        content: Widget,
        *,
        delay: float = 0.5,
        dismiss_delay: float = 1.5,
        alignment: AlignmentLike = "top-center",
        anchor: AlignmentLike = "bottom-center",
        offset: Tuple[float, float] = (0.0, -4.0),
        transition_spec: Optional["TransitionSpec"] = None,
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        """Initialize tooltip wrapper around anchor widget.

        Args:
            child: Anchor widget that owns tooltip interactions.
            content: Tooltip content widget.
            delay: Delay in seconds before opening.
            dismiss_delay: Delay in seconds before closing.
            alignment: Reference point on the anchor widget.
            anchor: Reference point on tooltip content.
            offset: Additional ``(dx, dy)`` offset in pixels.
            transition_spec: Optional overlay transition.
            width: Width sizing for this wrapper.
            height: Height sizing for this wrapper.
        """
        super().__init__(
            child,
            content,
            is_open=None,
            alignment=alignment,
            anchor=anchor,
            offset=offset,
            transition_spec=transition_spec,
            light_dismiss=False,
            width=width,
            height=height,
        )
        self.delay = max(0.0, float(delay))
        self.dismiss_delay = max(0.0, float(dismiss_delay))
        self._open_callback: Optional[Callable[[float], None]] = None
        self._close_callback: Optional[Callable[[float], None]] = None
        self._is_hovered = False
        self._is_focused = False
        self._active_touch_pointer_id: Optional[int] = None
        self._focus_node: Optional[FocusNode] = None
        self._prev_focus_callback: Optional[Callable[[bool], None]] = None
        self._focus_callback_wrapper: Optional[Callable[[bool], None]] = None
        self._install_interactions()

    def on_unmount(self) -> None:
        self._cancel_open()
        self._cancel_close()
        self._restore_focus_callback()
        super().on_unmount()

    def _install_interactions(self) -> None:
        if not isinstance(self._child, InteractionHostMixin):
            # TooltipModifier.apply() guarantees an InteractionHostMixin anchor.
            # This guard prevents wiring callbacks to a detached wrapper.
            return
        region = self._child
        region.enable_hover(on_change=self._on_hover_change)
        region.enable_click(on_press=self._on_press, on_release=self._on_release)

        focus_node = region.get_node(FocusNode)
        if focus_node is None:
            region.add_node(FocusNode(on_focus_change=self._on_focus_change))
            return

        if not isinstance(focus_node, FocusNode):
            return
        if self._focus_node is focus_node and self._focus_callback_wrapper is not None:
            if focus_node._on_focus_change is self._focus_callback_wrapper:
                return
        prev_callback = focus_node._on_focus_change

        def _chained(on: bool) -> None:
            if prev_callback is not None:
                prev_callback(on)
            self._on_focus_change(on)

        self._focus_node = focus_node
        self._prev_focus_callback = prev_callback
        self._focus_callback_wrapper = _chained
        focus_node._on_focus_change = _chained

    def _restore_focus_callback(self) -> None:
        focus_node = self._focus_node
        wrapper = self._focus_callback_wrapper
        if focus_node is not None and wrapper is not None:
            if focus_node._on_focus_change is wrapper:
                focus_node._on_focus_change = self._prev_focus_callback
        self._focus_node = None
        self._prev_focus_callback = None
        self._focus_callback_wrapper = None

    def _on_hover_change(self, hovered: bool) -> None:
        self._is_hovered = bool(hovered)
        if self._is_hovered:
            self._schedule_open(self.delay)
            return
        self._schedule_close(self.dismiss_delay)

    def _on_focus_change(self, focused: bool) -> None:
        self._is_focused = bool(focused)
        if self._is_focused:
            self._schedule_open(self.delay)
            return
        self._schedule_close(self.dismiss_delay)

    def _on_press(self, event: PointerEvent) -> None:
        if event.pointer_type != PointerType.TOUCH:
            return
        self._active_touch_pointer_id = event.id
        self._schedule_open(self.delay)

    def _on_release(self, event: PointerEvent) -> None:
        if self._active_touch_pointer_id != event.id:
            return
        self._active_touch_pointer_id = None
        self._schedule_close(self.dismiss_delay)

    def _schedule_open(self, delay: float) -> None:
        self._cancel_close()
        self._cancel_open()
        if delay <= 0.0:
            self._set_open(True)
            return

        def _open(_dt: float) -> None:
            self._open_callback = None
            self._set_open(True)

        self._open_callback = _open
        runtime.clock.schedule_once(_open, delay)

    def _schedule_close(self, delay: float) -> None:
        if self._is_hovered or self._is_focused:
            return
        self._cancel_open()
        self._cancel_close()
        if delay <= 0.0:
            self._set_open(False)
            return

        def _close(_dt: float) -> None:
            self._close_callback = None
            self._set_open(False)

        self._close_callback = _close
        runtime.clock.schedule_once(_close, delay)

    def _cancel_open(self) -> None:
        callback = self._open_callback
        if callback is None:
            return
        self._open_callback = None
        runtime.clock.unschedule(callback)

    def _cancel_close(self) -> None:
        callback = self._close_callback
        if callback is None:
            return
        self._close_callback = None
        runtime.clock.unschedule(callback)

    def _set_open(self, open_state: bool) -> None:
        if self._is_open.value == open_state:
            return
        self._is_open.value = open_state


@dataclass(slots=True)
class TooltipModifier(ModifierElement):
    """Modifier that attaches transient tooltip behavior to an anchor widget."""

    content: Widget
    delay: float = 0.5
    dismiss_delay: float = 1.5
    alignment: AlignmentLike = "top-center"
    anchor: AlignmentLike = "bottom-center"
    offset: Tuple[float, float] = (0.0, -4.0)
    transition_spec: Optional["TransitionSpec"] = None

    def apply(self, widget: Widget) -> Widget:
        """Wrap widget in TooltipBox and wire transient interaction behavior."""
        if isinstance(widget, InteractionHostMixin):
            anchor = widget
        else:
            anchor = ensure_interaction_region(widget)
        return TooltipBox(
            anchor,
            self.content,
            delay=self.delay,
            dismiss_delay=self.dismiss_delay,
            alignment=self.alignment,
            anchor=self.anchor,
            offset=self.offset,
            transition_spec=self.transition_spec,
            width=anchor.width_sizing,
            height=anchor.height_sizing,
        )


def tooltip(
    content: Widget,
    *,
    delay: float = 0.5,
    dismiss_delay: float = 1.5,
    alignment: AlignmentLike = "top-center",
    anchor: AlignmentLike = "bottom-center",
    offset: tuple[float, float] = (0.0, -4.0),
    transition_spec: Optional["TransitionSpec"] = None,
) -> TooltipModifier:
    """Attach a transient tooltip behavior to any widget.

    Behavior:
    - Opens automatically (desktop: hover/focus, touch: long-press).
    - Closes automatically on leave/blur with dismiss delay.
    - No external open state API.

    Args:
        content: Tooltip content widget.
        delay: Delay in seconds before opening.
        dismiss_delay: Delay in seconds before closing.
        alignment: Reference point on the anchor widget.
        anchor: Reference point on tooltip content.
        offset: Additional ``(dx, dy)`` offset in pixels.
        transition_spec: Optional overlay transition.

    Returns:
        A ``TooltipModifier`` suitable for :meth:`Widget.modifier`.
    """
    return TooltipModifier(
        content=content,
        delay=delay,
        dismiss_delay=dismiss_delay,
        alignment=alignment,
        anchor=anchor,
        offset=offset,
        transition_spec=transition_spec,
    )


__all__ = ["TooltipBox", "TooltipModifier", "tooltip"]
