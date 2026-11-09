"""Linux app badge: the ``com.canonical.Unity.LauncherEntry`` count.

The bridge emits the ``Update`` signal on the session bus. A dock that honours
it draws the count on the app's launcher; a desktop that does not ignores the
signal, and nothing tells the app.
"""

from __future__ import annotations

import logging
import os
import sys

if sys.platform != "linux":  # pragma: no cover - guards the Linux-only dependency
    raise ImportError("badge_launcher is only available on Linux")

from jeepney import DBusAddress, new_signal
from jeepney.io.blocking import open_dbus_connection

from nuiitivet.common.logging_once import warning_once

from .badge_launcher_plan import desktop_entry_uri, launcher_properties

logger = logging.getLogger(__name__)

_ENTRY = DBusAddress("/com/canonical/unity/launcherentry/nuiitivet", interface="com.canonical.Unity.LauncherEntry")


class LauncherEntryBridge:
    """Shows the badge as a launcher entry count. Framework-internal."""

    def __init__(self) -> None:
        """Connect to the session bus; raises when the session has none."""
        self._conn = open_dbus_connection(bus="SESSION")
        self._uri = desktop_entry_uri(os.environ, os.getpid(), os.getppid(), sys.argv[0])

    def show(self, label: str) -> None:
        """Send ``label`` as the count; a text that is not a count shows no badge."""
        properties = launcher_properties(label)
        if properties is None:
            warning_once(logger, "badge_launcher_text", "A Linux launcher shows a count only; badge text is not shown")
            properties = launcher_properties("")
        self._conn.send(new_signal(_ENTRY, "Update", "sa{sv}", (self._uri, properties)))

    def close(self) -> None:
        """Close the bus connection."""
        self._conn.close()
