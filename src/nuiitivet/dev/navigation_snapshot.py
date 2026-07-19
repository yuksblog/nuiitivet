"""Snapshot & restore the declarative navigation stack across a reload (#378).

A reload rebuilds the whole widget tree from the factory, so the freshly built
``Navigator`` starts at its initial route and every pushed route is lost. This is
the navigation analogue of the ``Observable`` restore in :mod:`.snapshot`:
capture the *descriptors* of routes the author pushed declaratively (intents /
route-table keys) before the swap, then replay them onto the rebuilt navigator.

Only the process-global root navigator (``Navigator.root()``) is handled. Routes
pushed as raw ``Route``/``Widget`` instances are opaque — they cannot be rebuilt
against the new code — and stop the replay, leaving the rest collapsed. Open
overlays/dialogs are explicitly out of scope and keep resetting (§11 of
``docs/design/HOT_RELOAD.md``).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from nuiitivet.navigation.navigator import _PushDescriptor

logger = logging.getLogger(__name__)


def snapshot_navigation() -> list["_PushDescriptor | None"]:
    """Capture the root navigator's pushed-route descriptors, or ``[]`` if none.

    Safe to call in any reload state: a missing or unset navigator root yields an
    empty snapshot rather than raising, so a reload is never aborted by it.
    """
    from nuiitivet.navigation import Navigator

    try:
        navigator = Navigator.root()
    except RuntimeError:
        return []
    try:
        return navigator.snapshot_stack()
    except Exception:
        logger.debug("navigation snapshot failed", exc_info=True)
        return []


def restore_navigation(descriptors: Sequence["_PushDescriptor | None"]) -> int:
    """Replay pushed-route descriptors onto the freshly built root navigator.

    Args:
        descriptors: The list from :func:`snapshot_navigation`, captured before
            the reload rebuilt the tree.

    Returns:
        The number of routes restored. Zero when there is nothing to restore or
        the navigator root is unavailable.
    """
    if not descriptors:
        return 0

    from nuiitivet.navigation import Navigator

    try:
        navigator = Navigator.root()
    except RuntimeError:
        return 0
    try:
        return navigator.restore_stack(descriptors)
    except Exception:
        logger.debug("navigation restore failed", exc_info=True)
        return 0
