"""
Material Design 3 Interactive Widget.

This module provides the base class for interactive widgets in Material Design 3,
handling the State Layer visualization (hover, focus, press states).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia.color import make_opacity_paint
from nuiitivet.rendering.skia.geometry import clip_round_rect, make_rect
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.theme.types import ColorSpec
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.rendering.sizing import SizingLike

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

    def __init__(
        self,
        child: Optional["Widget"] = None,
        on_click: Optional[Callable[[], None]] = None,
        state_layer_color: ColorSpec = ColorRole.ON_SURFACE,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        disabled: bool | Any = False,
        **kwargs,
    ):
        super().__init__(
            child=child,
            on_click=on_click,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            **kwargs,
        )
        self.state_layer_color = state_layer_color

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

    def _get_active_state_layer_opacity(self) -> float:
        """Return the opacity for the current state layer based on interaction state."""
        state = self.state
        if state.dragging:
            return self._DRAG_OPACITY
        elif state.pressed:
            return self._PRESS_OPACITY
        elif state.focused:
            return self._FOCUS_OPACITY
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

