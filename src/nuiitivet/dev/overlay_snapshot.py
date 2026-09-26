"""Snapshot & restore the intent-shown overlay entries across a reload.

A reload rebuilds the window's overlay, so every open entry would close. An entry
shown from an intent is recorded by the overlay; it is shown again on the rebuilt
overlay and keeps its handle. An entry shown from a widget closes as before.
Only the App's own overlay is handled, as with the navigation stack.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from nuiitivet.overlay.overlay import _ShowRecord
    from nuiitivet.runtime.window import Window

logger = logging.getLogger(__name__)


def snapshot_overlay(app: "Window") -> list["_ShowRecord"]:
    """Capture the App overlay's intent-shown entries, or ``[]`` if none.

    Args:
        app: The App being reloaded. Read after the rebuild and before the
            commit, so this is still the overlay on screen.
    """
    overlay = app._overlay
    if overlay is None:
        return []
    try:
        return overlay.snapshot_stack()
    except Exception:
        logger.debug("overlay snapshot failed", exc_info=True)
        return []


def restore_overlay(app: "Window", records: Sequence["_ShowRecord"]) -> int:
    """Show the captured entries again on the freshly committed overlay.

    Args:
        app: The App being reloaded, after the rebuilt content root is committed.
        records: The list from :func:`snapshot_overlay`.

    Returns:
        The number of entries shown again.
    """
    if not records:
        return 0
    overlay = app._overlay
    if overlay is None:
        return 0
    try:
        return overlay.restore_stack(records)
    except Exception:
        logger.debug("overlay restore failed", exc_info=True)
        return 0
