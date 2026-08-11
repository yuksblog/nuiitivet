"""Every exception a test can receive from the harness, in one importable place.

Two of these are defined here because nothing below the harness raises them: the
interaction core reports ``handled`` in a dict and lets its caller judge, and it
has no notion of a stale query result. The other three are re-exported from
:mod:`nuiitivet._interaction.action`, which is private and stays that way -- a
test writing ``pytest.raises(TargetNotFoundError)`` must not have to import from
an underscore package, and ``nuiitivet.dev`` is not an alternative because it is
session-gated and never enters a production install.
"""

from __future__ import annotations

from nuiitivet._interaction.action import (
    LayoutNotConvergedError,
    TargetNotFoundError,
    TargetNotVisibleError,
)


class ActionNotHandledError(RuntimeError):
    """An action verb ran and nothing consumed it.

    ``type()`` with no focused widget, or ``key()`` with nothing bound to the
    keystroke, dispatches the input into an app that ignores it. The dev bridge
    reports that as ``handled: False`` and lets the assistant read it; an
    ``assert`` does not read it, so the same result here would let a test go
    green on input that never arrived. Pass ``require_handled=False`` to the verb
    to get the result dict back instead and assert on it.
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
    "LayoutNotConvergedError",
    "StaleNodeError",
    "TargetNotFoundError",
    "TargetNotVisibleError",
]
