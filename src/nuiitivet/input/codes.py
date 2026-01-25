"""Backend-agnostic input codes.

These codes are normalized by the active backend (e.g. pyglet).
"""

from __future__ import annotations

# Modifier bit masks (backend-agnostic)
MOD_SHIFT: int = 1 << 0
MOD_CTRL: int = 1 << 1
MOD_ALT: int = 1 << 2
MOD_META: int = 1 << 3

# Text motion codes (backend-agnostic)
TEXT_MOTION_BACKSPACE: int = 1
TEXT_MOTION_DELETE: int = 2
TEXT_MOTION_LEFT: int = 3
TEXT_MOTION_RIGHT: int = 4
TEXT_MOTION_HOME: int = 5
TEXT_MOTION_END: int = 6
