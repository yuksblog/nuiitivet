"""Widget kernel package.

This package contains the backend-agnostic widget foundation (build/layout/paint/lifecycle/input).
"""

from .widget import FocusEvent, PointerEvent, Widget, layout_depends_on, paint_depends_on

__all__ = [
    "Widget",
    "FocusEvent",
    "PointerEvent",
    "layout_depends_on",
    "paint_depends_on",
]
