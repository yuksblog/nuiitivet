"""Animation primitives.

This package contains lightweight, frame-driven animation utilities.
"""

from .easing import ease_cubic_out
from .animation import Animation
from .manager import AnimationHandle, AnimationManager
from .animatable import Animatable, DrivenAnimatable
from .motion import Motion, LinearMotion, BezierMotion, SpringMotion
from .tween import Rect, RectTween, IntTween, LerpTween

__all__ = [
    "Animatable",
    "Animation",
    "AnimationHandle",
    "AnimationManager",
    "DrivenAnimatable",
    "Motion",
    "LinearMotion",
    "BezierMotion",
    "SpringMotion",
    "ease_cubic_out",
    "Rect",
    "RectTween",
    "IntTween",
    "LerpTween",
]
