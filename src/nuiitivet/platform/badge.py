"""App badge: a count or a short text on the app's Dock or taskbar icon.

``App.badge`` holds the value. While the event loop runs, a
:class:`BadgeBinding` shows every value the platform's own way: the Dock
tile's badge label on macOS, an overlay icon on the taskbar button on Windows,
the launcher count on Linux. A platform that cannot show the badge is logged
once and the app keeps running.
"""

from __future__ import annotations

import logging
import sys
from typing import Callable, Optional, Protocol, Union

from nuiitivet.common.logging_once import exception_once, warning_once
from nuiitivet.observable import Disposable, StateBase

logger = logging.getLogger(__name__)

BadgeValue = Union[int, str, None]

# Returns the main window's native handle, or ``None`` while it has none.
WindowHandle = Callable[[], Optional[int]]


def badge_label(value: BadgeValue) -> str:
    """Return the text the badge shows for ``value``.

    Args:
        value: A count, a short text, or ``None``.

    Returns:
        The text, or ``""`` for no badge: ``None``, a count of zero or less,
        and a blank text show none.

    Raises:
        TypeError: ``value`` is not an ``int``, a ``str`` or ``None``.
    """
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value) if value > 0 else ""
    if isinstance(value, str):
        return value.strip()
    raise TypeError(f"App.badge takes an int, a str or None, got {type(value).__name__}.")


class BadgeBridge(Protocol):
    """One platform's way to show the badge."""

    def show(self, label: str) -> None:
        """Show ``label``; an empty one removes the badge."""
        ...

    def close(self) -> None:
        """Release what the bridge holds."""
        ...


class BadgeBinding:
    """Shows a badge State on the platform while the loop runs. Framework-internal."""

    def __init__(self, badge: StateBase[BadgeValue], window_handle: WindowHandle) -> None:
        """Initialize BadgeBinding.

        Args:
            badge: The value to show.
            window_handle: Returns the main window's native handle; Windows
                puts the overlay on that window's taskbar button.
        """
        self._badge = badge
        self._window_handle = window_handle
        self._bridge: Optional[BadgeBridge] = None
        self._unavailable = False
        self._subscription: Optional[Disposable] = None

    def install(self) -> None:
        """Show the current value and every later one."""
        if self._subscription is not None:
            return
        self._subscription = self._badge.subscribe(self._show)
        self.refresh()

    def refresh(self) -> None:
        """Show the current value again; a taskbar button made anew has lost its overlay."""
        if self._subscription is not None:
            self._show(self._badge.value)

    def uninstall(self) -> None:
        """Remove the badge and stop following the value."""
        subscription, self._subscription = self._subscription, None
        if subscription is not None:
            subscription.dispose()
        bridge, self._bridge = self._bridge, None
        if bridge is None:
            return
        try:
            bridge.show("")
        except Exception:
            # The window the badge sat on is usually gone by now, and the badge with it.
            logger.debug("Removing the app badge raised", exc_info=True)
        try:
            bridge.close()
        except Exception:
            exception_once(logger, "badge_close_exc", "Closing the app badge bridge raised")

    def _show(self, value: BadgeValue) -> None:
        try:
            label = badge_label(value)
        except TypeError:
            exception_once(logger, "badge_value_exc", "App.badge holds a value that is not a badge; ignored")
            return
        bridge = self._bridge_for(label)
        if bridge is None:
            return
        try:
            bridge.show(label)
        except Exception:
            exception_once(logger, "badge_show_exc", "The app badge could not be shown; continuing without one")

    def _bridge_for(self, label: str) -> Optional[BadgeBridge]:
        # Made for the first badge shown, so an app without one opens no bus and no COM object.
        if self._bridge is not None or self._unavailable or not label:
            return self._bridge
        try:
            self._bridge = self._create_bridge()
        except Exception:
            exception_once(logger, "badge_create_exc", "The app badge is unavailable; continuing without one")
        else:
            if self._bridge is None:
                warning_once(logger, "badge_unsupported", "This platform shows no app badge; App.badge is ignored")
        self._unavailable = self._bridge is None
        return self._bridge

    def _create_bridge(self) -> Optional[BadgeBridge]:
        """Pick the platform bridge (separate so tests can substitute one)."""
        if sys.platform == "darwin":
            from .badge_cocoa import DockBadgeBridge

            return DockBadgeBridge()
        if sys.platform == "win32":
            from .badge_win32 import TaskbarOverlayBridge

            return TaskbarOverlayBridge(self._window_handle)
        if sys.platform == "linux":
            from .badge_launcher import LauncherEntryBridge

            return LauncherEntryBridge()
        return None
