"""Post-layout dispatch of widget size-change callbacks.

A size-change callback is arbitrary user code: it may push a route, reassign
children, or write an Observable that rebuilds a subtree. Running it inline from
:meth:`WidgetKernel.set_layout_rect` would re-enter the tree *during* layout, so
a measurement is instead queued here and dispatched **between frames**, at the
same point in the frame as any other user code — the same deferral ``Geometry``
gets for free by writing only to an Observable (see ``docs/design/GEOMETRY.md``
§3 and §11).

The queue is keyed by widget identity and holds the *latest* measurement, so a
widget laid out several times within one frame reports once, with its final size.
Entries hold a weak reference: a widget dropped from the tree before the flush is
skipped rather than resurrected.
"""

from __future__ import annotations

import logging
import weakref
from collections.abc import Awaitable
from typing import Any, Callable, Dict, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.size import Size

from .callbacks import invoke_event_handler

_logger = logging.getLogger(__name__)

#: Single :class:`Size` argument callback (e.g. ``on_size_changed``).
SizeCallback = Union[Callable[[Size], None], Callable[[Size], Awaitable[None]]]

_PendingEntry = Tuple["weakref.ReferenceType[Any]", Size]
_pending_size_changes: Dict[int, _PendingEntry] = {}


def _make_finalizer(key: int) -> Callable[[Any], None]:
    def _cleanup(_ref: Any) -> None:
        _pending_size_changes.pop(key, None)

    return _cleanup


def queue_size_change(widget: Any, size: Size) -> None:
    """Queue *widget*'s new measured *size* for dispatch after layout.

    Requests a frame on the first queued entry: the callback fires from the
    next frame's flush, and on an idle (draw-on-demand) app nothing else would
    schedule that frame.
    """
    key = id(widget)
    first_insert = key not in _pending_size_changes
    if first_insert:
        _pending_size_changes[key] = (weakref.ref(widget, _make_finalizer(key)), size)
    else:
        _pending_size_changes[key] = (_pending_size_changes[key][0], size)

    if not first_insert:
        return
    invalidate = getattr(widget, "invalidate", None)
    if callable(invalidate):
        try:
            invalidate()
        except Exception:
            exception_once(
                _logger,
                f"widget_size_change_invalidate_exc:{type(widget).__name__}",
                "Exception in invalidate() after a size change for widget=%s",
                type(widget).__name__,
            )


def flush_size_change_callbacks() -> bool:
    """Dispatch every queued size change to its widget's callbacks.

    Called by the app at the start of a frame, before the build flush, so an
    Observable a callback writes is picked up by that frame's recomposition.
    Safe to call from tests to settle a size change without running a frame.

    Returns:
        Whether any callback ran. A one-shot render uses this to know when the
        tree has stopped changing (``App._settle_pending_size_changes``).
    """
    if not _pending_size_changes:
        return False
    pending = list(_pending_size_changes.values())
    _pending_size_changes.clear()
    dispatched = False
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
    "queue_size_change",
]
