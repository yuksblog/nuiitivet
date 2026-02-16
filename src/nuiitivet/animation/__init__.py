"""Animation primitives.

This package contains lightweight, frame-driven animation utilities.
"""

from .animatable import Animatable
from .converter import VectorConverter, FloatConverter, RgbaTupleConverter
from .motion import Motion, LinearMotion, BezierMotion, SpringMotion
from .interpolate import Rect, lerp, lerp_int, lerp_rect

__all__ = [
    "Animatable",
    "VectorConverter",
    "FloatConverter",
    "RgbaTupleConverter",
    "Motion",
    "LinearMotion",
    "BezierMotion",
    "SpringMotion",
    "Rect",
    "lerp",
    "lerp_int",
    "lerp_rect",
]
