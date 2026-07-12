"""Input domain models.

This package contains backend-agnostic, mostly pure input event types.
"""

from .events import FocusEvent, InputHandler, InputKind, KeyInputEvent
from .pointer import PointerEvent, PointerEventType, PointerType
from .codes import (
    BUTTON_LEFT,
    BUTTON_MIDDLE,
    BUTTON_RIGHT,
    MOD_ACCEL,
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    accel_mask,
    is_primary_button,
    resolve_modifiers,
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_DELETE,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_LEFT,
    TEXT_MOTION_RIGHT,
)
from .shortcut import Shortcut, ShortcutBinding, ShortcutLike, normalize_key_name, to_shortcut

__all__ = [
    "BUTTON_LEFT",
    "BUTTON_MIDDLE",
    "BUTTON_RIGHT",
    "FocusEvent",
    "InputHandler",
    "InputKind",
    "KeyInputEvent",
    "MOD_ACCEL",
    "MOD_ALT",
    "MOD_CTRL",
    "MOD_META",
    "MOD_SHIFT",
    "PointerEvent",
    "PointerEventType",
    "PointerType",
    "Shortcut",
    "ShortcutBinding",
    "ShortcutLike",
    "accel_mask",
    "is_primary_button",
    "normalize_key_name",
    "resolve_modifiers",
    "to_shortcut",
    "TEXT_MOTION_BACKSPACE",
    "TEXT_MOTION_DELETE",
    "TEXT_MOTION_END",
    "TEXT_MOTION_HOME",
    "TEXT_MOTION_LEFT",
    "TEXT_MOTION_RIGHT",
]
