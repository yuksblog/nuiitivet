"""
Material Design 3 Interactive Widget.

This module provides the base class for interactive widgets in Material Design 3,
handling the State Layer visualization (hover, focus, press states).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, Union, Any, TYPE_CHECKING

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia.geometry import make_rect, draw_round_rect
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.interaction import FocusNode
from nuiitivet.theme.types import ColorSpec
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.rendering.sizing import SizingLike

if TYPE_CHECKING:
    from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)


class InteractiveWidget(Clickable):
    """
    Base class for interactive Material Design 3 widgets.

    Implements the MD3 State Layer visual effects for:
    - Hover state
    - Focus state
    - Press state
    - Drag state

    The State Layer is an overlay drawn on top of the container (background)
    but behind the content (children).
    """

    # MD3 State Layer Opacity Standard
    _HOVER_OPACITY = 0.08
    _FOCUS_OPACITY = 0.12
    _PRESS_OPACITY = 0.12
    _DRAG_OPACITY = 0.16

    # MD3 Focus Indicator Standard
    _FOCUS_RING_THICKNESS = 3.0
    _FOCUS_RING_OFFSET = 2.0
    _FOCUS_RING_COLOR = ColorRole.SECONDARY

    def __init__(
        self,
        child: Optional["Widget"] = None,
        on_click: Optional[Callable[[], None]] = None,
        state_layer_color: ColorSpec = ColorRole.ON_SURFACE,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        disabled: bool | Any = False,
        focusable: bool = True,
        **kwargs,
    ):
        super().__init__(
            child=child,
            on_click=on_click,
            disabled=disabled,
            focusable=focusable,
            width=width,
            height=height,
            padding=padding,
            **kwargs,
        )
        self.state_layer_color = state_layer_color
        self._focus_from_pointer = False

        # Attach key event handler to the FocusNode (Standard Accessibility)
        node = self.get_node(FocusNode)
        if node and isinstance(node, FocusNode):
            node._on_key = self.on_key_event
            node._on_focus_change = self._handle_focus_change

    def on_key_event(self, key: str, modifiers: int = 0) -> bool:
        """Handle key events (Space/Enter to click)."""
        if self.disabled:
            return False

        if key in ("space", "enter"):
            # Trigger click via PointerInputNode to ensure callbacks are invoked
            self._pointer_node._emit_click()
            return True
        return False

    def _handle_focus_change(self, focused: bool) -> None:
        """Handle focus state changes."""
        if not focused:
            self._focus_from_pointer = False

    def request_focus_from_pointer(self) -> None:
        """Request focus originating from a pointer (e.g. click)."""
        self._focus_from_pointer = True
        super().request_focus_from_pointer()

    @property
    def should_show_focus_ring(self) -> bool:
        """Return True if the focus ring should be visible."""
        # MD3: Hide focus ring if focus came from pointer interaction
        return self.state.focused and not self._focus_from_pointer

    def paint_outsets(self) -> Tuple[int, int, int, int]:
        """Compute visual overflow (outsets) including focus ring."""
        # Get base outsets (e.g. from Box shadow)
        base = super().paint_outsets()

        # Calculate focus ring outsets if potentially visible
        # Note: We include this even if not currently focused to avoid
        # surface resizing/jank during interaction.
        ring_outset = 0
        if not self.disabled:
            # MD3 Focus Ring extends outside the bounds by (offset + thickness)
            import math

            val = self._FOCUS_RING_THICKNESS + max(0, self._FOCUS_RING_OFFSET)
            ring_outset = int(math.ceil(val))

        # Combine by taking max of each side
        return (
            max(base[0], ring_outset),
            max(base[1], ring_outset),
            max(base[2], ring_outset),
            max(base[3], ring_outset),
        )

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """Override paint to inject draw_state_layer."""
        self.set_last_rect(x, y, width, height)

        # 1. Background (from Box)
        self.draw_background(canvas, x, y, width, height)

        # 2. State Layer (New)
        if not self.disabled:
            self.draw_state_layer(canvas, x, y, width, height)

        # 3. Children (from Box)
        self.draw_children(canvas, x, y, width, height)

        # 4. Border (from Box)
        self.draw_border(canvas, x, y, width, height)

        # 5. Focus Indicator (New)
        if not self.disabled and self.should_show_focus_ring:
            self.draw_focus_indicator(canvas, x, y, width, height)

    def _get_active_state_layer_opacity(self) -> float:
        """Return the opacity for the current state layer based on interaction state."""
        state = self.state
        if state.dragging:
            return self._DRAG_OPACITY
        elif state.pressed:
            return self._PRESS_OPACITY
        elif state.hovered:
            return self._HOVER_OPACITY
        return 0.0

    def draw_state_layer(self, canvas, x: int, y: int, width: int, height: int):
        """Draws the MD3 State Layer based on current interaction state."""
        opacity = self._get_active_state_layer_opacity()

        if opacity <= 0:
            return

        # Prepare paint
        try:
            # Resolve the base color of the state layer
            color = resolve_color_to_rgba(self.state_layer_color, self)
            if color is None:
                return

            # Apply opacity to the color or use a layer
            # Since we just want a flat fill, we can modify the alpha of the paint
            r, g, b, a = color

            # Combine alpha
            final_alpha = a * opacity

            # Draw
            from nuiitivet.rendering.skia import make_paint

            paint = make_paint(color=(r, g, b, final_alpha), style="fill")

            rect = make_rect(x, y, width, height)
            radii = list(self.corner_radii_pixels(width, height))

            # We need to respect corner radius
            # Reuse Box's clip mechanism if possible, but here we can just draw rounded rect
            # matching the container shape.

            draw_round_rect(canvas, rect, radii, paint)

        except Exception:
            exception_once(logger, "interactive_widget_state_layer_exc", "Failed to draw state layer")

    def draw_focus_indicator(self, canvas, x: int, y: int, width: int, height: int):
        """Draws the MD3 Focus Indicator (Ring) when focused."""
        try:
            # Focus ring color is usually Secondary
            color = resolve_color_to_rgba(self._FOCUS_RING_COLOR, self)
            if color is None:
                return

            from nuiitivet.rendering.skia import make_paint

            # 3dp limit
            thickness = self._FOCUS_RING_THICKNESS
            offset = self._FOCUS_RING_OFFSET

            # Draw outside the container
            inflate = offset + (thickness / 2)

            paint = make_paint(color=color, style="stroke", stroke_width=thickness)

            # Inflate rect
            rect = make_rect(x - inflate, y - inflate, width + (inflate * 2), height + (inflate * 2))

            # Adjust corner radii for the outer ring
            original_radii = list(self.corner_radii_pixels(width, height))
            radii = [r + inflate for r in original_radii]

            draw_round_rect(canvas, rect, radii, paint)

        except Exception:
            exception_once(logger, "interactive_widget_focus_ring_exc", "Failed to draw focus indicator")
