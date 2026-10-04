"""Translate browser input into the framework's backend-neutral codes."""

from __future__ import annotations

from typing import Optional

from nuiitivet.input.codes import BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT

# MouseEvent.button, in the browser's numbering.
_BUTTONS = {0: BUTTON_LEFT, 1: BUTTON_MIDDLE, 2: BUTTON_RIGHT}
# MouseEvent.buttons: the browser puts the right button before the middle one.
_HELD = ((1, BUTTON_LEFT), (2, BUTTON_RIGHT), (4, BUTTON_MIDDLE))

# The pixels one wheel step scrolls at the default ``scroll_multiplier``. Dividing
# by it makes a wheel delta given in pixels scroll that many pixels.
_PIXELS_PER_STEP = 20.0
_STEPS_PER_PAGE = 40.0

_DOM_DELTA_PIXEL = 0
_DOM_DELTA_LINE = 1


def button_code(button: int) -> Optional[int]:
    """The ``BUTTON_*`` code of a ``MouseEvent.button``, or ``None`` for a button the framework has no code for."""
    return _BUTTONS.get(int(button))


def buttons_mask(buttons: int) -> int:
    """The ``BUTTON_*`` mask of a ``MouseEvent.buttons``."""
    held = int(buttons)
    return sum(code for bit, code in _HELD if held & bit)


def wheel_steps(delta: float, delta_mode: int) -> float:
    """A ``WheelEvent`` delta in wheel steps. The sign is kept: positive moves the content forward."""
    if delta_mode == _DOM_DELTA_PIXEL:
        return float(delta) / _PIXELS_PER_STEP
    if delta_mode == _DOM_DELTA_LINE:
        return float(delta)
    return float(delta) * _STEPS_PER_PAGE


def key_name(key: str, code: str) -> str:
    """The framework's name for a key, from ``KeyboardEvent.key`` and ``KeyboardEvent.code``.

    A digit is named by its physical key, so ``Shift+1`` is ``1`` with the
    shift modifier and not the character the layout produces.
    """
    if code.startswith("Digit") and len(code) == 6:
        return code[5]
    if key == " ":
        return "space"
    name = key.lower()
    if name.startswith("arrow"):
        return name[5:]
    return name


__all__ = ["button_code", "buttons_mask", "key_name", "wheel_steps"]
