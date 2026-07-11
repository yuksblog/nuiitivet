from __future__ import annotations

from typing import Optional, Sequence

from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import (
    InteractionRegion,
    PointerEventCallback,
    PointerListenerNode,
    ensure_interaction_region,
)


class PointerInputModifier(ModifierElement):
    """Attach a raw pointer-stream listener to a widget.

    This is the low-level "Listener" layer (cf. Compose ``Modifier.pointerInput``,
    Flutter ``Listener``): it surfaces the individual pointer events — press,
    move, release, enter, leave, scroll — rather than the semantic click/hover
    that :func:`clickable` / :func:`hoverable` provide. Each callback receives a
    :class:`~nuiitivet.input.pointer.PointerEvent` whose ``local_x`` / ``local_y``
    are relative to the widget's top-left (``x`` / ``y`` remain screen
    coordinates).
    """

    def __init__(
        self,
        *,
        on_press: Optional[PointerEventCallback] = None,
        on_move: Optional[PointerEventCallback] = None,
        on_release: Optional[PointerEventCallback] = None,
        on_enter: Optional[PointerEventCallback] = None,
        on_leave: Optional[PointerEventCallback] = None,
        on_scroll: Optional[PointerEventCallback] = None,
        on_modifier_keys_change: Optional[PointerEventCallback] = None,
        buttons: Optional[Sequence[int]] = None,
        capture: bool = True,
    ) -> None:
        self.on_press = on_press
        self.on_move = on_move
        self.on_release = on_release
        self.on_enter = on_enter
        self.on_leave = on_leave
        self.on_scroll = on_scroll
        self.on_modifier_keys_change = on_modifier_keys_change
        self.buttons = buttons
        self.capture = capture

    def apply(self, widget: Widget) -> Widget:
        region: InteractionRegion = ensure_interaction_region(widget)

        node = region.get_node(PointerListenerNode)
        if isinstance(node, PointerListenerNode):
            # Recomposition re-applies the modifier; reconfigure the existing
            # node (setter semantics) rather than stacking a second one.
            node.configure(
                on_press=self.on_press,
                on_move=self.on_move,
                on_release=self.on_release,
                on_enter=self.on_enter,
                on_leave=self.on_leave,
                on_scroll=self.on_scroll,
                on_modifier_keys_change=self.on_modifier_keys_change,
                buttons=self.buttons,
                capture=self.capture,
            )
        else:
            region.add_node(
                PointerListenerNode(
                    on_press=self.on_press,
                    on_move=self.on_move,
                    on_release=self.on_release,
                    on_enter=self.on_enter,
                    on_leave=self.on_leave,
                    on_scroll=self.on_scroll,
                    on_modifier_keys_change=self.on_modifier_keys_change,
                    buttons=self.buttons,
                    capture=self.capture,
                )
            )
        return region


def pointer_input(
    *,
    on_press: Optional[PointerEventCallback] = None,
    on_move: Optional[PointerEventCallback] = None,
    on_release: Optional[PointerEventCallback] = None,
    on_enter: Optional[PointerEventCallback] = None,
    on_leave: Optional[PointerEventCallback] = None,
    on_scroll: Optional[PointerEventCallback] = None,
    on_modifier_keys_change: Optional[PointerEventCallback] = None,
    buttons: Optional[Sequence[int]] = None,
    capture: bool = True,
) -> PointerInputModifier:
    """Observe the raw pointer stream on any widget.

    Each callback may be sync or async and receives a
    :class:`~nuiitivet.input.pointer.PointerEvent`. The event's ``local_x`` /
    ``local_y`` are relative to the widget's top-left; ``x`` / ``y`` are screen
    coordinates. ``event.buttons`` is the bitmask of buttons currently held down
    (populated during a drag), letting an ``on_move`` handler tell whether a
    stroke is in progress.

    Args:
        on_press: Called on a pointer press inside the widget.
        on_move: Called as the pointer moves inside the widget, and — while
            captured — anywhere, so a stroke that runs off the edge keeps
            reporting.
        on_release: Called when the press that this node is tracking is released.
        on_enter: Called when the pointer enters the widget bounds.
        on_leave: Called when the pointer leaves the widget bounds.
        on_scroll: Called on a scroll (wheel) event over the widget.
        on_modifier_keys_change: Called when the held modifier-key mask changes
            while the pointer is inside or captured — even if the pointer is
            stationary. Reads ``event.modifier_keys`` for the new mask. This lets
            a widget (e.g. a canvas) swap its cursor the instant Alt is pressed
            without the pointer moving.
        buttons: The ``BUTTON_*`` codes that trigger ``on_press`` / ``on_release``.
            ``None`` (default) accepts every button.
        capture: When True (default), the pointer is captured on press so
            ``on_move`` / ``on_release`` keep arriving after it leaves the widget
            bounds. When False, moving outside delivers ``on_leave`` and stops
            ``on_move``.

    Returns:
        A :class:`PointerInputModifier` to attach via ``.modifier(...)``.
    """
    return PointerInputModifier(
        on_press=on_press,
        on_move=on_move,
        on_release=on_release,
        on_enter=on_enter,
        on_leave=on_leave,
        on_scroll=on_scroll,
        on_modifier_keys_change=on_modifier_keys_change,
        buttons=buttons,
        capture=capture,
    )
