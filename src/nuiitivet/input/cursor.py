"""The mouse cursor shapes a widget can ask the window to show."""

from __future__ import annotations

from enum import Enum


class MouseCursor(str, Enum):
    """A mouse cursor shape.

    Every member is a cursor the OS draws itself on macOS, Windows and X11,
    and one the browser draws for the canvas. A widget answers one from
    :attr:`~nuiitivet.widgeting.widget.Widget.mouse_cursor`, or has one
    attached with the ``cursor()`` modifier.

    Attributes:
        DEFAULT: The arrow.
        POINTER: The pointing hand, over something that can be clicked.
        TEXT: The I-beam, over text that can be edited or selected.
        NOT_ALLOWED: The barred circle, over a target that refuses the action.
        CROSSHAIR: The thin cross, over a canvas that places or picks a point.
        RESIZE_LEFT_RIGHT: The horizontal double arrow, over a vertical divider.
        RESIZE_UP_DOWN: The vertical double arrow, over a horizontal divider.
    """

    DEFAULT = "default"
    POINTER = "pointer"
    TEXT = "text"
    NOT_ALLOWED = "not_allowed"
    CROSSHAIR = "crosshair"
    RESIZE_LEFT_RIGHT = "resize_left_right"
    RESIZE_UP_DOWN = "resize_up_down"
