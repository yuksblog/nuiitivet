"""Shared helpers for pointer-event driven tests."""

from typing import Optional

from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.widgeting.widget import Widget


def _ensure_layout_rect_from_last_rect(widget: Widget) -> None:
    try:
        rect = widget.last_rect
        if rect is None:
            if widget.layout_rect is None:
                pw, ph = widget.preferred_size()
                widget.set_layout_rect(0, 0, int(pw), int(ph))
            return

        x, y, w, h = rect
        parent = getattr(widget, "_parent", None)
        if parent is not None:
            parent_global = getattr(parent, "global_layout_rect", None)
            if parent_global is not None:
                px, py, _pw, _ph = parent_global
                widget.set_layout_rect(int(x - px), int(y - py), int(w), int(h))
                return
        widget.set_layout_rect(int(x), int(y), int(w), int(h))
    except Exception:
        return


def send_pointer_event_for_test(
    widget: Widget,
    event_type: PointerEventType,
    x: float = 0.0,
    y: float = 0.0,
    pointer_id: int = 1,
    *,
    dx: float = 0.0,
    dy: float = 0.0,
    button: Optional[int] = None,
    scroll_x: float = 0.0,
    scroll_y: float = 0.0,
    modifiers: int = 0,
) -> bool:
    """Test helper: dispatch a synthetic pointer event directly to the given widget.

    Many unit tests call this helper with the widget-under-test and expect the
    event to be delivered to that widget (without hit_test routing).

    Tests often set `_last_rect` without running a full layout pass. Since the
    framework now uses layout-derived bounds for interaction, this helper
    initializes `layout_rect` from `last_rect` (or preferred_size) as a test
    convenience.
    """
    if event_type is PointerEventType.SCROLL:
        event = PointerEvent.scroll_event(pointer_id, x, y, scroll_x, scroll_y, modifiers=modifiers)
    else:
        event = PointerEvent.mouse_event(
            pointer_id,
            event_type,
            x,
            y,
            dx=dx,
            dy=dy,
            button=button,
            modifiers=modifiers,
        )

    _ensure_layout_rect_from_last_rect(widget)

    try:
        return bool(widget.dispatch_pointer_event(event))
    except Exception:
        return False


def send_pointer_event_for_test_via_app_routing(
    root: Widget,
    event_type: PointerEventType,
    x: float = 0.0,
    y: float = 0.0,
    pointer_id: int = 1,
    *,
    dx: float = 0.0,
    dy: float = 0.0,
    button: Optional[int] = None,
    scroll_x: float = 0.0,
    scroll_y: float = 0.0,
    modifiers: int = 0,
) -> bool:
    """Test helper: dispatch a synthetic pointer event via App-style routing.

    This approximates the App's pointer dispatch semantics:
    - Pick the deepest target via `hit_test(x, y)`.
    - Bubble the event up the `_parent` chain until handled.
    """
    if event_type is PointerEventType.SCROLL:
        event = PointerEvent.scroll_event(pointer_id, x, y, scroll_x, scroll_y, modifiers=modifiers)
    else:
        event = PointerEvent.mouse_event(
            pointer_id,
            event_type,
            x,
            y,
            dx=dx,
            dy=dy,
            button=button,
            modifiers=modifiers,
        )

    _ensure_layout_rect_from_last_rect(root)
    try:
        for child in getattr(root, "children", ()):
            _ensure_layout_rect_from_last_rect(child)
    except Exception:
        pass

    try:
        target = root.hit_test(int(x), int(y))
    except Exception:
        return False

    if target is None:
        return False

    current: Optional[Widget] = target
    visited: set[Widget] = set()
    while current is not None and current not in visited:
        visited.add(current)
        try:
            if current.dispatch_pointer_event(event):
                return True
        except Exception:
            pass
        current = getattr(current, "_parent", None)

    return False
