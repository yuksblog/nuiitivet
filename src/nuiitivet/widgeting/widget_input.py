"""Input routing helpers for widgets."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import batch
from nuiitivet.input.events import FocusEvent, InputHandler, InputKind, KeyInputEvent
from nuiitivet.input.pointer import PointerEvent, PointerEventType


_logger = logging.getLogger(__name__)


class InputHubMixin:
    """Allows widgets to register layered input hooks per channel."""

    INPUT_PRIORITY: Tuple[InputKind, ...] = ("pointer", "scroll", "key", "focus")

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[override]
        super().__init__(*args, **kwargs)
        self._input_hooks: Dict[InputKind, List[InputHandler]] = {kind: [] for kind in self.INPUT_PRIORITY}

    # --- Hook registration -------------------------------------------------
    def register_input_hook(self, kind: InputKind, handler: InputHandler, *, prepend: bool = False) -> InputHandler:
        hooks = self._input_hooks.setdefault(kind, [])
        if prepend:
            hooks.insert(0, handler)
        else:
            hooks.append(handler)
        return handler

    # --- Pointer delivery --------------------------------------------------
    def dispatch_pointer_event(self, event: PointerEvent) -> bool:
        with batch():
            handled = False
            if event.type == PointerEventType.SCROLL:
                handled = self._dispatch_input("scroll", event)
                if not handled:
                    handled = bool(self.on_scroll_event(event))
            if handled:
                return True
            return self._dispatch_input("pointer", event) or bool(self.on_pointer_event(event))

    def on_pointer_event(self, event: PointerEvent) -> bool:  # pragma: no cover - default no-op
        return False

    def on_scroll_event(self, event: PointerEvent) -> bool:  # pragma: no cover - default no-op
        return False

    def capture_pointer(self, event: PointerEvent, *, passive: bool = False) -> bool:
        manager = self._pointer_manager()
        if manager is None:
            return False
        try:
            manager.capture(self, event, passive=passive)
            return True
        except Exception:
            exception_once(
                _logger,
                "widget_input_capture_pointer_exc",
                "Failed to capture pointer (passive=%s)",
                passive,
            )
            return False

    def release_pointer(self, pointer_id: int) -> bool:
        manager = self._pointer_manager()
        if manager is None:
            return False
        try:
            return bool(manager.release(pointer_id, self))
        except Exception:
            exception_once(
                _logger,
                "widget_input_release_pointer_exc",
                "Failed to release pointer: pointer_id=%s",
                pointer_id,
            )
            return False

    def cancel_pointer(self, pointer_id: int) -> None:
        manager = self._pointer_manager()
        if manager is None:
            return
        try:
            manager.cancel(pointer_id)
        except Exception:
            exception_once(
                _logger,
                "widget_input_cancel_pointer_exc",
                "Failed to cancel pointer: pointer_id=%s",
                pointer_id,
            )

    # --- Key delivery ------------------------------------------------------
    def handle_key_event(self, key: str, modifiers: int = 0) -> bool:
        with batch():
            event = KeyInputEvent(key=key, modifiers=modifiers)
            if self._dispatch_input("key", event):
                return True
            return bool(self.on_key_event(key, modifiers))

    def on_key_event(self, key: str, modifiers: int = 0) -> bool:  # pragma: no cover - default no-op
        return False

    # --- Focus delivery ----------------------------------------------------
    def handle_focus_event(self, event: FocusEvent) -> bool:
        with batch():
            if self._dispatch_input("focus", event):
                return True
            return bool(self.on_focus_event(event))

    def on_focus_event(self, event: FocusEvent) -> bool:  # pragma: no cover - default no-op
        return False

    # --- Helpers -----------------------------------------------------------
    def _dispatch_input(self, kind: InputKind, payload: Any) -> bool:
        handlers = self._input_hooks.get(kind, [])
        for handler in handlers:
            try:
                if handler(payload):
                    return True
            except Exception:
                exception_once(
                    _logger,
                    f"widget_input_dispatch_input_exc:{kind}",
                    "Exception in input hook: kind=%s handler=%r payload_type=%s",
                    kind,
                    handler,
                    type(payload).__name__,
                )
                continue
        return False

    def _pointer_manager(self):  # pragma: no cover - helper
        app = getattr(self, "_app", None)
        if app is None:
            return None
        return getattr(app, "_pointer_capture_manager", None)
