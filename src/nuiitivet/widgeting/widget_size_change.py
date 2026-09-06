"""Post-layout dispatch of what the layout pass measured.

An ``Observable`` write from inside ``layout()`` propagates synchronously and
tears the frame for consumers measured earlier in the same pass, so layout only
*queues* here; the app flushes the queue between frames, before the next frame's
build flush. Size-change callbacks (arbitrary user code) and deferred publishes
(framework state such as ``Geometry``'s size and scroll metrics) both ride the
queue, keyed by owner and coalesced to the latest entry. Size-change entries
hold a weak reference, so a widget dropped before the flush is skipped.
"""

from __future__ import annotations

import logging
import weakref
from collections.abc import Awaitable
from typing import Any, Callable, Dict, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.size import Size

from .callbacks import invoke_event_handler, report_contained

_logger = logging.getLogger(__name__)

#: Single :class:`Size` argument callback (e.g. ``on_size_changed``).
SizeCallback = Union[Callable[[Size], None], Callable[[Size], Awaitable[None]]]

_PendingEntry = Tuple["weakref.ReferenceType[Any]", Size]
_pending_size_changes: Dict[int, _PendingEntry] = {}
_pending_publishes: Dict[int, Callable[[], None]] = {}


def _make_finalizer(key: int) -> Callable[[Any], None]:
    def _cleanup(_ref: Any) -> None:
        _pending_size_changes.pop(key, None)

    return _cleanup


def _request_flush_frame(widget: Any) -> None:
    """Request the frame whose start flushes the queues (an idle app has none)."""
    invalidate = getattr(widget, "invalidate", None)
    if not callable(invalidate):
        return
    try:
        invalidate()
    except Exception as exc:
        exception_once(
            _logger,
            f"widget_size_change_invalidate_exc:{type(widget).__name__}",
            "Exception in invalidate() after a size change for widget=%s",
            type(widget).__name__,
        )
        report_contained(
            exc,
            owner=type(widget).__name__,
            site="invalidate() after a size change",
        )


def queue_size_change(widget: Any, size: Size) -> None:
    """Queue *widget*'s new measured *size* for dispatch after layout.

    Requests a frame on the first queued entry. A measurement equal to the last
    reported size queues nothing, so a clean relayout schedules no extra frame.
    """
    key = id(widget)
    first_insert = key not in _pending_size_changes
    if first_insert:
        if size == getattr(widget, "_reported_size", None):
            return
        _pending_size_changes[key] = (weakref.ref(widget, _make_finalizer(key)), size)
        _request_flush_frame(widget)
    else:
        _pending_size_changes[key] = (_pending_size_changes[key][0], size)


def queue_deferred_publish(key: Any, publish: Callable[[], None], *, widget: Any = None) -> None:
    """Queue *publish* (an Observable write) to run at the next flush.

    Keyed by *key*, latest entry wins — *publish* should read the owner's
    current state rather than close over values. *widget*, when given, has a
    frame requested on the first queued entry.
    """
    first_insert = id(key) not in _pending_publishes
    _pending_publishes[id(key)] = publish
    if first_insert and widget is not None:
        _request_flush_frame(widget)


def flush_size_change_callbacks() -> bool:
    """Run queued deferred publishes, then dispatch queued size changes.

    Called at the start of a frame, before the build flush, so a write lands in
    that frame's recomposition; publishes run first so callbacks read fresh
    framework state. Safe to call from tests. Returns whether anything ran,
    which is how a one-shot render knows the tree has settled.
    """
    dispatched = False
    if _pending_publishes:
        publishes = list(_pending_publishes.values())
        _pending_publishes.clear()
        for publish in publishes:
            try:
                publish()
            except Exception:
                exception_once(
                    _logger,
                    "widget_size_change_publish_exc",
                    "Exception in a deferred layout-result publish",
                )
        dispatched = True
    if not _pending_size_changes:
        return dispatched
    pending = list(_pending_size_changes.values())
    _pending_size_changes.clear()
    for ref, size in pending:
        widget = ref()
        if widget is None or getattr(widget, "_unmounted", False):
            continue
        dispatch = getattr(widget, "_dispatch_size_change", None)
        if callable(dispatch) and dispatch(size):
            dispatched = True
    return dispatched


def invoke_size_callback(callback: SizeCallback, size: Size, *, owner_name: str) -> None:
    """Invoke a size callback, containing exceptions and awaiting nothing.

    An async callback is scheduled as a task, like every other event handler.
    """
    invoke_event_handler(
        callback,
        size,
        error_key="widget_size_change_callback",
        error_msg="Exception in size change callback",
        owner_name=owner_name,
    )


__all__ = [
    "SizeCallback",
    "flush_size_change_callbacks",
    "invoke_size_callback",
    "queue_deferred_publish",
    "queue_size_change",
]
