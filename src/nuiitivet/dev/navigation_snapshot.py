"""Snapshot & restore the declarative navigation stack across a reload (#378).

A reload rebuilds the whole widget tree from the factory, so the freshly built
``Navigator`` starts at its initial route and every pushed route is lost. This is
the navigation analogue of the ``Observable`` restore in :mod:`.snapshot`:
capture the *descriptors* of routes the author pushed declaratively (intents /
route-table keys) before the swap, then replay them onto the rebuilt navigator.

Only the App's own navigator is handled. Routes pushed as raw ``Route``/``Widget``
instances are opaque — they cannot be rebuilt against the new code — and stop the
replay, leaving the rest collapsed. Open overlays/dialogs are explicitly out of
scope and keep resetting (§11 of ``docs/design/HOT_RELOAD.md``).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from nuiitivet.navigation.navigator import _PushDescriptor
    from nuiitivet.runtime.app import App

logger = logging.getLogger(__name__)


def snapshot_navigation(app: "App") -> list["_PushDescriptor | None"]:
    """Capture the App navigator's pushed-route descriptors, or ``[]`` if none.

    Args:
        app: The App being reloaded. Read *before* the rebuild, so this is still
            the navigator that is on screen.

    Returns:
        The descriptors to hand to :func:`restore_navigation`. Safe to call in
        any reload state: an App with no navigator yet yields an empty snapshot
        rather than raising, so a reload is never aborted by it.
    """
    navigator = app._navigator
    if navigator is None:
        return []
    try:
        return navigator.snapshot_stack()
    except Exception:
        logger.debug("navigation snapshot failed", exc_info=True)
        return []


def restore_navigation(app: "App", descriptors: Sequence["_PushDescriptor | None"]) -> int:
    """Replay pushed-route descriptors onto the freshly committed navigator.

    Args:
        app: The App being reloaded. Must be called *after* the rebuilt content
            root has been committed, so this is the new navigator.
        descriptors: The list from :func:`snapshot_navigation`, captured before
            the reload rebuilt the tree.

    Returns:
        The number of routes restored. Zero when there is nothing to restore or
        the App has no navigator.
    """
    if not descriptors:
        return 0

    navigator = app._navigator
    if navigator is None:
        return 0
    try:
        return navigator.restore_stack(descriptors)
    except Exception:
        logger.debug("navigation restore failed", exc_info=True)
        return 0
