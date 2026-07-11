"""Input domain models.

This package contains backend-agnostic, mostly pure input event types.
"""

from .events import FocusEvent, InputHandler, InputKind, KeyInputEvent
from .pointer import PointerEvent, PointerEventType, PointerType
from .codes import (
    BUTTON_LEFT,
    BUTTON_MIDDLE,
    BUTTON_RIGHT,
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    is_primary_button,
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_DELETE,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_LEFT,
    TEXT_MOTION_RIGHT,
)

__all__ = [
    "BUTTON_LEFT",
    "BUTTON_MIDDLE",
    "BUTTON_RIGHT",
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
    "is_primary_button",
    "TEXT_MOTION_BACKSPACE",
    "TEXT_MOTION_DELETE",
    "TEXT_MOTION_END",
    "TEXT_MOTION_HOME",
    "TEXT_MOTION_LEFT",
    "TEXT_MOTION_RIGHT",
]
