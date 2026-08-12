"""Every exception a test can receive from the harness, in one importable place.

Four are defined here because nothing below the harness raises them: the
interaction core reports ``handled`` in a dict and lets its caller judge, it has
no notion of a stale query result, and waiting is the harness's job entirely. The
rest are re-exported -- three from :mod:`nuiitivet._interaction.action`, which is
private and stays that way, and ``UnschedulableAsyncWork``, which the framework
raises but only ever while a harness is observing. A test writing
``pytest.raises(TargetNotFoundError)`` must not have to import from an underscore
package, and ``nuiitivet.dev`` is not an alternative because it is session-gated
and never enters a production install.
"""

from __future__ import annotations

from nuiitivet._interaction.action import (
    LayoutNotConvergedError,
    TargetNotFoundError,
    TargetNotVisibleError,
)
from nuiitivet.widgeting.callbacks import UnschedulableAsyncWork


class ActionNotHandledError(RuntimeError):
    """An action verb ran and nothing consumed it.

    ``type()`` with no focused widget, or ``key()`` with nothing bound to the
    keystroke, dispatches the input into an app that ignores it. The dev bridge
    reports that as ``handled: False`` and lets the assistant read it; an
    ``assert`` does not read it, so the same result here would let a test go
    green on input that never arrived. Pass ``require_handled=False`` to the verb
    to get the result dict back instead and assert on it.
    """


class WaitTimeoutError(TimeoutError):
    """:meth:`~nuiitivet.testing.AppHarness.wait_for` gave up.

    The app never reached the state the test said it would. The message names
    what was still outstanding in *both* queues -- armed clock callbacks and
    pending tasks -- plus, for a tree condition, the identities that do exist.

    A :class:`TimeoutError`, so ``pytest.raises(TimeoutError)`` catches it and a
    suite that already treats timeouts as a category needs no new import. Note
    the deliberate divergence from the dev bridge, whose ``wait_for`` reports
    ``timed_out: True`` and never raises: an assistant reads that result and
    decides what to do, while an ``assert`` does not read it at all.
    """


class IdleTimeoutError(TimeoutError):
    """:meth:`~nuiitivet.testing.AppHarness.idle` never ran out of work.

    Rare by construction. ``idle()`` returns as soon as the loop is *quiescent*,
    which includes an app parked on an awaited dialog and an app animating
    forever, so reaching this means work that genuinely never stops -- a handler
    that spawns a handler, round after round.
    """


class SubscriptionLeakError(AssertionError):
    """Subscriptions outlived the widgets that made them.

    A widget subscribed to an ``Observable`` and never disposed the
    subscription, so the observable still holds a callback into a tree that has
    been unmounted. The message names each creation site; ``self.bind(...)`` is
    the fix, and ``leak_check="off"`` the escape hatch for a subscription that
    genuinely outlives its widget.

    An :class:`AssertionError` because it is an assertion the harness made on the
    test's behalf, not a harness malfunction.
    """


class StaleNodeError(RuntimeError):
    """A :class:`~nuiitivet.testing.node.Node` outlived the tree it described.

    A ``Node`` is a snapshot taken when the query ran. Once its widget has been
    unmounted -- most often because an action rebuilt the subtree it lived in --
    every attribute would still answer plausibly, about a discarded object. Raise
    instead, and re-query after the action.
    """


__all__ = [
    "ActionNotHandledError",
    "IdleTimeoutError",
    "LayoutNotConvergedError",
    "StaleNodeError",
    "SubscriptionLeakError",
    "TargetNotFoundError",
    "TargetNotVisibleError",
    "UnschedulableAsyncWork",
    "WaitTimeoutError",
]
