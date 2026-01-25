"""Animation primitives.

This package contains lightweight, frame-driven animation utilities.
"""

from .easing import ease_cubic_out
from .animation import Animation
from .manager import AnimationHandle, AnimationManager

__all__ = [
    "Animation",
    "AnimationHandle",
    "AnimationManager",
    "ease_cubic_out",
]
