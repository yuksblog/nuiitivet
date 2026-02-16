"""Animation primitives.

This package contains lightweight, frame-driven animation utilities.
"""

from .easing import ease_cubic_out
from .animation import Animation
from .manager import AnimationHandle, AnimationManager
from .animatable import Animatable
from .converter import VectorConverter, FloatConverter, RgbaTupleConverter
from .motion import Motion, LinearMotion, BezierMotion, SpringMotion
from .interpolate import Rect, lerp, lerp_int, lerp_rect

__all__ = [
    "Animatable",
    "Animation",
    "AnimationHandle",
    "AnimationManager",
    "VectorConverter",
    "FloatConverter",
    "RgbaTupleConverter",
    "Motion",
    "LinearMotion",
    "BezierMotion",
    "SpringMotion",
    "ease_cubic_out",
    "Rect",
    "lerp",
    "lerp_int",
    "lerp_rect",
]
