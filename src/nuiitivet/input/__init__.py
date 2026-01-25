"""Input domain models.

This package contains backend-agnostic, mostly pure input event types.
"""

from .events import FocusEvent, InputHandler, InputKind, KeyInputEvent
from .pointer import PointerEvent, PointerEventType, PointerType
from .codes import (
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_DELETE,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_LEFT,
    TEXT_MOTION_RIGHT,
)

__all__ = [
    "FocusEvent",
    "InputHandler",
    "InputKind",
    "KeyInputEvent",
    "MOD_ALT",
    "MOD_CTRL",
    "MOD_META",
    "MOD_SHIFT",
    "PointerEvent",
    "PointerEventType",
    "PointerType",
    "TEXT_MOTION_BACKSPACE",
    "TEXT_MOTION_DELETE",
    "TEXT_MOTION_END",
    "TEXT_MOTION_HOME",
    "TEXT_MOTION_LEFT",
    "TEXT_MOTION_RIGHT",
]
