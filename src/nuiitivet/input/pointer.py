"""Pointer event primitives.

These types are backend-agnostic and can be reused across different UI backends.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import time


class PointerType(str, Enum):
    """Logical pointer device categories."""

    MOUSE = "mouse"
    TOUCH = "touch"
    PEN = "pen"
    UNKNOWN = "unknown"


class PointerEventType(str, Enum):
    """Pointer event actions."""

    ENTER = "enter"
    LEAVE = "leave"
    PRESS = "press"
    MOVE = "move"
    HOVER = "hover"
    RELEASE = "release"
    CANCEL = "cancel"
    SCROLL = "scroll"


@dataclass(frozen=True)
class PointerEvent:
    """Immutable pointer event payload delivered to widgets.

    Button semantics:
        ``button`` is the single button that *caused* this event — set on
        ``PRESS`` and ``RELEASE`` (and carried through the synthesized
        ``CANCEL``) to a backend-neutral ``BUTTON_*`` code, and ``None``
        otherwise (``MOVE``/``HOVER``/``ENTER``/``LEAVE``/``SCROLL``, or a
        synthetic/non-mouse event that carries no button).

        ``buttons`` is a bit mask of the buttons currently *held down*, using
        the same ``BUTTON_*`` codes OR-ed together. It is populated on ``MOVE``
        (drag) events so a consumer can tell a right-drag from a left-drag; it
        is ``0`` when no button is held.
    """

    id: int
    type: PointerEventType
    x: float
    y: float
    pointer_type: PointerType = PointerType.UNKNOWN
    dx: float = 0.0
    dy: float = 0.0
    scroll_x: float = 0.0
    scroll_y: float = 0.0
    button: Optional[int] = None
    buttons: int = 0
    timestamp: float = 0.0
    is_primary: bool = True
    modifier_keys: int = 0

    @staticmethod
    def mouse_event(
        pointer_id: int,
        event_type: PointerEventType,
        x: float,
        y: float,
        *,
        dx: float = 0.0,
        dy: float = 0.0,
        button: Optional[int] = None,
        buttons: int = 0,
        timestamp: Optional[float] = None,
        modifier_keys: int = 0,
    ) -> "PointerEvent":
        return PointerEvent(
            id=pointer_id,
            type=event_type,
            x=x,
            y=y,
            pointer_type=PointerType.MOUSE,
            dx=dx,
            dy=dy,
            button=button,
            buttons=buttons,
            timestamp=time.time() if timestamp is None else float(timestamp),
            modifier_keys=modifier_keys,
        )

    @staticmethod
    def scroll_event(
        pointer_id: int,
        x: float,
        y: float,
        scroll_x: float,
        scroll_y: float,
        *,
        timestamp: Optional[float] = None,
        modifier_keys: int = 0,
    ) -> "PointerEvent":
        return PointerEvent(
            id=pointer_id,
            type=PointerEventType.SCROLL,
            x=x,
            y=y,
            pointer_type=PointerType.MOUSE,
            scroll_x=scroll_x,
            scroll_y=scroll_y,
            timestamp=time.time() if timestamp is None else float(timestamp),
            modifier_keys=modifier_keys,
        )
