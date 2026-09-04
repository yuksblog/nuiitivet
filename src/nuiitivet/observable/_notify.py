"""Delivering one value to every subscriber, including after one of them raises.

A subscriber is application code, and application code has bugs. Iterating the
list bare lets the first raising callback abort the loop, so every subscriber
registered *after* it silently stops receiving the value -- registration order
decides who breaks, and the symptom is a binding that "sometimes does not
update". The guard is therefore per callback rather than one ``try`` around the
loop, which would only move the truncation.

An exception reaching here is a bug in the subscriber, not a value the framework
can publish, so it is logged and the remaining subscribers are notified.

**Only application subscribers are guarded.** The observable graph subscribes to
itself -- a computed's dependency edges, a wrapper's edge to its source -- and
those callbacks are tagged (:func:`~nuiitivet.observable.protocols.mark_internal_subscription`).
An exception on one of them is not a broken subscriber but the framework's own
signal, such as the batch queue's infinite-loop guard, and swallowing it would
turn a loud protection into a silent one. They re-raise. Each internal edge that
can run application code -- ``filter``'s predicate, a derivation's function --
therefore guards it at its own site, where the log can name what actually broke.
"""

from __future__ import annotations

import logging
from typing import Callable, List, TypeVar

from nuiitivet.common.logging_once import exception_once_per_exc

from .protocols import is_internal_subscription

T = TypeVar("T")


def notify_all(
    subscribers: List[Callable[[T], None]],
    current: Callable[[], T],
    *,
    logger: logging.Logger,
    key: str,
) -> None:
    """Notify each of ``subscribers`` in turn, surviving any that raise.

    ``subscribers`` is snapshotted first, so a callback that subscribes or
    unsubscribes while being notified does not disturb this emission.

    The value is read from ``current`` **per callback**, not captured once. A
    subscriber may write back to the observable it is being notified by -- an
    application normalizing what a text field just produced is the in-tree case
    -- and the subscribers after it must be handed what that write left behind,
    not the value the emission started with. Callers whose value cannot change
    mid-emission pass a thunk over their own local.

    ``key`` names the emitting observable for the log's de-duplication; the
    raising callback's own type and location are added by
    :func:`~nuiitivet.common.logging_once.exception_once_per_exc`, so two
    different broken subscribers are reported separately while one that keeps
    failing stays a single line.
    """
    for callback in list(subscribers):
        try:
            callback(current())
        except Exception:
            if is_internal_subscription(callback):
                raise
            exception_once_per_exc(
                logger,
                f"observable_subscriber_raised:{key}",
                "Observable subscriber raised; the remaining subscribers were still notified",
            )
