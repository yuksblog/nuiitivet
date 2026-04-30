"""Event helper functions extracted from App to improve testability."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .pointer import PointerCaptureManager
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.common.logging_once import exception_once

logger = logging.getLogger(__name__)


def _pointer_manager(app: Any) -> Optional[PointerCaptureManager]:
    manager = getattr(app, "_pointer_capture_manager", None)
    if isinstance(manager, PointerCaptureManager):
        return manager
    return None


def _primary_pointer_id(app: Any) -> int:
    return getattr(app, "_primary_pointer_id", 1)


def _bubble_pointer_event(target: Any, event: PointerEvent) -> Optional[Any]:
    current = target
    visited = set()
    while current is not None and current not in visited:
        visited.add(current)
        handled = False
        dispatcher = getattr(current, "dispatch_pointer_event", None)
        if callable(dispatcher):
            try:
                handled = bool(dispatcher(event))
            except Exception:
                exception_once(
                    logger,
                    "app_events_dispatch_pointer_event_exc",
                    "dispatch_pointer_event raised (target=%s)",
                    type(current).__name__,
                )
                handled = False
        if handled:
            return current
        try:
            current = getattr(current, "_parent", None)
        except Exception:
            exception_once(
                logger,
                "app_events_get_parent_exc",
                "Failed to access _parent during pointer event bubbling (current=%s)",
                type(current).__name__,
            )
            current = None
    return None


def _deliver_pointer_event(app: Any, target: Any, event: PointerEvent) -> Optional[Any]:
    if target is None:
        return None
    handler = _bubble_pointer_event(target, event)
    if handler is not None:
        # Request redraw for handled events. Scroll should bypass FPS throttle.
        try:
            if event.type is PointerEventType.SCROLL:
                try:
                    app.invalidate(immediate=True)
                except TypeError:
                    app.invalidate()
            else:
                app.invalidate()
        except Exception:
            exception_once(logger, "app_events_invalidate_exc", "app.invalidate raised")
    return handler


def dispatch_mouse_motion(app: Any, x: int, y: int):
    manager = _pointer_manager(app)
    pointer_id = _primary_pointer_id(app)
    owner = manager.owner_of(pointer_id) if manager is not None else None

    if owner is not None:
        event = PointerEvent.mouse_event(pointer_id, PointerEventType.MOVE, x, y)
        _deliver_pointer_event(app, owner, event)
        if manager is not None:
            manager.update_event(event)
        return

    prev = getattr(app, "_last_hover_target", None)
    cur = None
    try:
        if app.root is not None:
            cur = app.root.hit_test(x, y)
    except Exception:
        exception_once(logger, "app_events_hit_test_exc", "hit_test raised")
        cur = None

    if prev is cur:
        if cur is not None:
            hover_event = PointerEvent.mouse_event(pointer_id, PointerEventType.HOVER, x, y)
            _deliver_pointer_event(app, cur, hover_event)
    else:
        if prev is not None:
            leave_event = PointerEvent.mouse_event(pointer_id, PointerEventType.LEAVE, x, y)
            _deliver_pointer_event(app, prev, leave_event)
        if cur is not None:
            enter_event = PointerEvent.mouse_event(pointer_id, PointerEventType.ENTER, x, y)
            _deliver_pointer_event(app, cur, enter_event)
            hover_event = PointerEvent.mouse_event(pointer_id, PointerEventType.HOVER, x, y)
            _deliver_pointer_event(app, cur, hover_event)
        try:
            app._last_hover_target = cur
        except Exception:
            exception_once(logger, "app_events_set_last_hover_target_exc", "Failed to set app._last_hover_target")


def _press_target_contains_focused_node(target: Any, focused_node: Any) -> bool:
    """Return True if ``target`` is the focused widget itself or one of its
    descendants.

    Used for the "click landed on the focused widget" case. The reverse
    direction (focused widget being a descendant of ``target``) is
    intentionally NOT covered here — see ``_handler_hosts_focused_node``
    which restricts that direction to actual press handlers so arbitrary
    layout ancestors do not spuriously keep focus.
    """
    if focused_node is None or target is None:
        return False
    focused_owner = getattr(focused_node, "owner", None)
    if focused_owner is None:
        return False

    current = target
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if current is focused_owner:
            return True
        current = getattr(current, "_parent", None)
    return False


def _handler_hosts_focused_node(handler: Any, focused_node: Any) -> bool:
    """Return True if ``handler`` is the focused widget's host.

    The press ``handler`` is the widget that actually consumed the event
    (typically a Clickable). When the focused widget is a descendant of
    that handler, the click belongs to the same "focus group" — for
    example, clicking a leading/trailing icon inside a TextField whose
    inner EditableText is focused must not blur the editable.

    This is restricted to the actual handler (rather than the deepest
    hit-test target or any ancestor) so that clicks on unrelated layout
    ancestors (Column, Container, etc.) still blur correctly.
    """
    if handler is None or focused_node is None:
        return False
    focused_owner = getattr(focused_node, "owner", None)
    if focused_owner is None:
        return False

    current = focused_owner
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if current is handler:
            return True
        current = getattr(current, "_parent", None)
    return False


def dispatch_mouse_press(app: Any, x: int, y: int):
    if app.root is None:
        return

    target = None
    try:
        target = app.root.hit_test(x, y)
    except Exception:
        exception_once(logger, "app_events_hit_test_exc", "hit_test raised")
        target = None

    # Capture focus state before dispatch so we can decide whether to blur.
    focused_before = getattr(app, "_focused_node", None)

    if target is None:
        # Click on empty area: blur any currently-focused node.
        if focused_before is not None:
            try:
                app.request_focus(None)
            except Exception:
                exception_once(
                    logger,
                    "app_events_blur_focus_no_target_exc",
                    "app.request_focus(None) raised (no hit target)",
                )
        return

    pointer_id = _primary_pointer_id(app)
    press_event = PointerEvent.mouse_event(pointer_id, PointerEventType.PRESS, x, y)
    handler = _deliver_pointer_event(app, target, press_event)
    manager = _pointer_manager(app)
    if handler is not None and manager is not None:
        manager.capture(handler, press_event, passive=True)
    if handler is not None:
        try:
            app._pressed_target = handler
        except Exception:
            exception_once(logger, "app_events_set_pressed_target_exc", "Failed to set app._pressed_target")

    # If the press did not transfer focus to a node within the press target
    # (e.g. click landed on a non-interactive area), blur the previously
    # focused node so that text fields lose focus when clicking outside.
    focused_after = getattr(app, "_focused_node", None)
    # Two complementary in-group checks:
    # - target check: the press hit the focused widget itself or a descendant.
    # - handler check: the consuming press handler is the focused widget's
    #   host (e.g. TextField containing a focused EditableText). Restricted
    #   to ``handler`` so unrelated layout ancestors do not preserve focus.
    if (
        focused_before is not None
        and focused_after is focused_before
        and not _press_target_contains_focused_node(target, focused_before)
        and not _handler_hosts_focused_node(handler, focused_before)
    ):
        try:
            app.request_focus(None)
        except Exception:
            exception_once(
                logger,
                "app_events_blur_focus_outside_exc",
                "app.request_focus(None) raised (click outside focus group)",
            )


def dispatch_mouse_release(app: Any, x: int, y: int):
    pointer_id = _primary_pointer_id(app)
    manager = _pointer_manager(app)
    owner = manager.owner_of(pointer_id) if manager is not None else None

    target = owner
    if target is None and app.root is not None:
        try:
            target = app.root.hit_test(x, y)
        except Exception:
            exception_once(logger, "app_events_hit_test_exc", "hit_test raised")
            target = None

    if target is None:
        if manager is not None:
            manager.release(pointer_id)
        return

    release_event = PointerEvent.mouse_event(pointer_id, PointerEventType.RELEASE, x, y)
    handler = _deliver_pointer_event(app, target, release_event)
    if manager is not None:
        if owner is not None:
            manager.release(pointer_id, owner)
        elif handler is not None:
            manager.release(pointer_id, handler)
    try:
        app._pressed_target = None
    except Exception:
        exception_once(logger, "app_events_clear_pressed_target_exc", "Failed to clear app._pressed_target")


def dispatch_mouse_scroll(app: Any, x: int, y: int, scroll_x: float, scroll_y: float):
    """Dispatch mouse scroll (wheel) event to the widget under the cursor."""
    if app.root is None:
        return

    target = None
    try:
        target = app.root.hit_test(x, y)
    except Exception:
        exception_once(logger, "app_events_hit_test_exc", "hit_test raised")
        target = None

    if target is None:
        return

    pointer_id = _primary_pointer_id(app)
    scroll_event = PointerEvent.scroll_event(pointer_id, x, y, scroll_x, scroll_y)
    _deliver_pointer_event(app, target, scroll_event)
