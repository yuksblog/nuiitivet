"""Pointer capture management.

Backend-agnostic pointer event types live in :mod:`nuiitivet.input.pointer`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional, TYPE_CHECKING, Tuple
import time
import weakref

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from ..widgeting.widget import Widget

from nuiitivet.input.pointer import PointerEvent
from nuiitivet.common.logging_once import exception_once


logger = logging.getLogger(__name__)


@dataclass
class PointerCapture:
    """Records which widget owns a pointer id."""

    pointer_id: int
    widget_ref: "weakref.ReferenceType[Widget]"
    started_at: float
    position: Tuple[float, float]
    last_event: Optional[PointerEvent] = None
    passive: bool = False

    def widget(self) -> Optional["Widget"]:
        return self.widget_ref()

    def update_from_event(self, event: PointerEvent) -> None:
        self.position = (event.x, event.y)
        self.last_event = event


class PointerCaptureManager:
    """Tracks pointer ownership so releases/cancels reach the right widget."""

    def __init__(self) -> None:
        self._captures: Dict[int, PointerCapture] = {}
        # optional callback used when a capture is forcefully cancelled
        # Signature: (pointer_id, widget_or_none, last_event_or_none)
        self._cancel_callback: Optional[Callable[[int, Optional["Widget"], Optional[PointerEvent]], None]] = None

    def set_cancel_callback(
        self,
        callback: Optional[Callable[[int, Optional["Widget"], Optional[PointerEvent]], None]],
    ) -> None:
        self._cancel_callback = callback

    def capture(self, widget: "Widget", event: PointerEvent, *, passive: bool = False) -> None:
        self._captures[event.id] = PointerCapture(
            pointer_id=event.id,
            widget_ref=weakref.ref(widget),
            started_at=time.time(),
            position=(event.x, event.y),
            last_event=event,
            passive=passive,
        )

    def release(self, pointer_id: int, widget: Optional["Widget"] = None) -> bool:
        record = self._captures.get(pointer_id)
        if record is None:
            return False
        owner = record.widget()
        if widget is not None and owner is not widget:
            return False
        self._captures.pop(pointer_id, None)
        return True

    def owner_of(self, pointer_id: int) -> Optional["Widget"]:
        record = self._captures.get(pointer_id)
        return record.widget() if record else None

    def update_event(self, event: PointerEvent) -> None:
        record = self._captures.get(event.id)
        if record is not None:
            record.update_from_event(event)

    def cancel(self, pointer_id: int) -> None:
        record = self._captures.pop(pointer_id, None)
        widget = record.widget() if record else None
        last_event = record.last_event if record else None
        if self._cancel_callback is not None:
            try:
                self._cancel_callback(pointer_id, widget, last_event)
            except Exception:
                exception_once(logger, "pointer_cancel_callback_exc", "Pointer cancel callback raised")

    def cancel_all_for(self, widget: "Widget") -> None:
        to_cancel = [pid for pid, rec in self._captures.items() if rec.widget() is widget]
        for pid in to_cancel:
            self.cancel(pid)

    def captured_pointer_ids(self) -> Tuple[int, ...]:
        return tuple(self._captures.keys())
