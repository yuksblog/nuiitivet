"""Backend-agnostic input codes.

These codes are normalized by the active backend (e.g. pyglet).
"""

from __future__ import annotations

from typing import Optional

# Modifier bit masks (backend-agnostic)
MOD_SHIFT: int = 1 << 0
MOD_CTRL: int = 1 << 1
MOD_ALT: int = 1 << 2
MOD_META: int = 1 << 3

# Pointer button codes (backend-agnostic).
#
# These double as bit masks so a single button (``PointerEvent.button``) and a
# set of held buttons (``PointerEvent.buttons``) share one encoding. The values
# intentionally match pyglet's ``mouse.LEFT``/``MIDDLE``/``RIGHT`` ordering, but
# the mapping is performed explicitly by the backend so no pyglet value ever
# leaks through the public ``PointerEvent``.
BUTTON_LEFT: int = 1 << 0
BUTTON_MIDDLE: int = 1 << 1
BUTTON_RIGHT: int = 1 << 2


def is_primary_button(button: Optional[int]) -> bool:
    """Return True if ``button`` counts as a primary (activating) button.

    The left button is primary. ``None`` is also treated as primary so that
    synthesized events and non-mouse pointers (touch/pen), which carry no
    button, keep activating widgets.
    """
    return button is None or button == BUTTON_LEFT


# Text motion codes (backend-agnostic)
TEXT_MOTION_BACKSPACE: int = 1
TEXT_MOTION_DELETE: int = 2
TEXT_MOTION_LEFT: int = 3
TEXT_MOTION_RIGHT: int = 4
TEXT_MOTION_HOME: int = 5
TEXT_MOTION_END: int = 6
