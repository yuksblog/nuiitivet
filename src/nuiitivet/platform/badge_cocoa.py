"""macOS app badge: the Dock tile's badge label.

Talks to AppKit through pyglet's bundled cocoapy, like the tray bridge. The
binding calls on the UI thread, which is the main thread AppKit requires.
"""

from __future__ import annotations

import sys

if sys.platform != "darwin":  # pragma: no cover - guards Darwin-only ObjC use
    raise ImportError("badge_cocoa is only available on macOS")


class DockBadgeBridge:
    """Shows the badge as ``NSDockTile.badgeLabel``. Framework-internal."""

    def show(self, label: str) -> None:
        """Show ``label`` in the Dock's red bubble; an empty one removes it."""
        from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString

        tile = ObjCClass("NSApplication").sharedApplication().dockTile()
        tile.setBadgeLabel_(get_NSString(label) if label else None)

    def close(self) -> None:
        """Nothing to release: the Dock tile belongs to the application."""
