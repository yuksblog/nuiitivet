"""Desktop notifications (title + body, fire-and-forget).

This module is OS-dependent but backend-agnostic. Each platform prefers an
in-process backend (``UNUserNotificationCenter`` on macOS, ``Shell_NotifyIcon``
on Windows) and falls back to an OS helper process (``osascript`` on macOS,
PowerShell on Windows) when the in-process route is unavailable — on macOS
that is every run without an app bundle, i.e. plain ``python app.py``. Linux
always uses ``notify-send``, which is a thin C client with no interpreter
startup cost.

Applications use ``nv.Desktop.notify`` (the :class:`~nuiitivet.platform.desktop.Desktop`
facade over :func:`notify`), which is safe from any thread and never raises: a
notification is a courtesy, and a platform that refuses one must never take
the app down.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from typing import Optional

from nuiitivet.common.logging_once import debug_once, exception_once


logger = logging.getLogger(__name__)


class NotificationError(RuntimeError):
    """A notification could not be raised (helper missing or helper failed)."""


class NotificationBackend(ABC):
    """Per-platform notification implementation.

    ``notify`` must be quick and non-blocking (subprocess backends spawn the
    helper without waiting for it) and safe to call from any thread. It raises
    :class:`NotificationError` when the notification cannot even be handed to
    the platform; delivery after that point is best-effort everywhere.
    """

    @abstractmethod
    def notify(self, title: str, body: str) -> None:
        raise NotImplementedError


def _applescript_quote(text: str) -> str:
    # An AppleScript string literal cannot contain a raw newline; emit a
    # concatenation with ``linefeed`` instead, parenthesized at the call site.
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r\n", "\n").replace("\r", "\n")
    escaped = escaped.replace("\n", '" & linefeed & "')
    return '("' + escaped + '")'


class MacNotificationBackend(NotificationBackend):
    """macOS notifications via ``osascript`` (``display notification``).

    The notification is attributed to Script Editor — the app's own name and
    icon require the in-process backend and an app bundle.
    """

    def notify(self, title: str, body: str) -> None:
        script = (
            f"display notification {_applescript_quote(body)}"
            f" with title {_applescript_quote(title)}"
        )
        try:
            subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise NotificationError(f"osascript could not be launched: {exc}") from exc


class LinuxNotificationBackend(NotificationBackend):
    """Linux notifications via ``notify-send`` (libnotify)."""

    def notify(self, title: str, body: str) -> None:
        # ``--`` keeps a title starting with ``-`` from being read as an option.
        cmd = ["notify-send", "--", title]
        if body:
            cmd.append(body)
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise NotificationError(
                f"notify-send could not be launched (install libnotify): {exc}"
            ) from exc


def _powershell_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


# PowerShell's own AppUserModelID: a registered identity that toast delivery
# accepts, at the cost of the notification being attributed to PowerShell.
_POWERSHELL_AUMID = (
    "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"
)


class WindowsNotificationBackend(NotificationBackend):
    """Windows notifications via PowerShell + WinRT toasts.

    Borrows PowerShell's AppUserModelID so the toast is accepted without any
    registration; the notification is attributed to PowerShell. This is the
    fallback for when the in-process ``Shell_NotifyIcon`` backend cannot start.
    """

    def notify(self, title: str, body: str) -> None:
        ns = "Windows.UI.Notifications"
        script = "; ".join(
            [
                f"$null = [{ns}.ToastNotificationManager, {ns}, ContentType = WindowsRuntime]",
                f"$null = [{ns}.ToastNotification, {ns}, ContentType = WindowsRuntime]",
                f"$xml = [{ns}.ToastNotificationManager]::GetTemplateContent("
                f"[{ns}.ToastTemplateType]::ToastText02)",
                "$texts = $xml.GetElementsByTagName('text')",
                "$null = $texts.Item(0).AppendChild("
                f"$xml.CreateTextNode({_powershell_quote(title)}))",
                "$null = $texts.Item(1).AppendChild("
                f"$xml.CreateTextNode({_powershell_quote(body)}))",
                f"$toast = [{ns}.ToastNotification]::new($xml)",
                f"[{ns}.ToastNotificationManager]::CreateToastNotifier("
                f"{_powershell_quote(_POWERSHELL_AUMID)}).Show($toast)",
            ]
        )
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as exc:
            raise NotificationError(f"PowerShell could not be launched: {exc}") from exc


class DummyNotificationBackend(NotificationBackend):
    """Fallback for unsupported platforms: every notification is a no-op."""

    def notify(self, title: str, body: str) -> None:
        debug_once(
            logger,
            "notification_unsupported",
            "desktop notifications are not supported on this platform",
        )


_backend: Optional[NotificationBackend] = None
_backend_lock = threading.Lock()


def _create_backend() -> NotificationBackend:
    if sys.platform == "darwin":
        # Prefer in-process UserNotifications: instant, and attributed to the
        # app's own bundle. Unavailable without a bundle identifier (any plain
        # ``python app.py`` run), where it falls back to the osascript helper.
        try:
            from .notification_cocoa import CocoaNotificationBackend

            return CocoaNotificationBackend()
        except NotificationError as exc:
            # The expected case for every unbundled run — keep it quiet.
            debug_once(
                logger,
                "notification_cocoa_unavailable",
                "in-process UserNotifications unavailable (%s); "
                "falling back to osascript",
                exc,
            )
            return MacNotificationBackend()
        except Exception:
            exception_once(
                logger,
                "notification_cocoa_unavailable",
                "in-process UserNotifications unavailable; "
                "falling back to osascript",
            )
            return MacNotificationBackend()
    if sys.platform == "linux":
        return LinuxNotificationBackend()
    if sys.platform == "win32":
        # Prefer the in-process notification-area balloon: instant, needs no
        # AppUserModelID registration, and Windows 10/11 render it as a toast.
        try:
            from .notification_win32 import Win32NotificationBackend

            return Win32NotificationBackend()
        except Exception:
            exception_once(
                logger,
                "notification_win32_unavailable",
                "in-process Shell_NotifyIcon backend unavailable; "
                "falling back to PowerShell",
            )
            return WindowsNotificationBackend()
    return DummyNotificationBackend()


def get_system_notification_backend() -> NotificationBackend:
    """Return the notification backend for the current platform (one per process)."""
    global _backend
    with _backend_lock:
        if _backend is None:
            _backend = _create_backend()
        return _backend


def notify(title: str, body: str = "") -> None:
    """Raise a desktop notification with ``title`` and an optional ``body``.

    Fire-and-forget: returns immediately, never raises, and is safe to call
    from an event handler or a worker thread alike. Failures are logged once
    per process instead of surfacing — a notification must never take the app
    down. Delivery is best-effort: the OS may still suppress it (permissions,
    focus modes) without an error.
    """
    try:
        get_system_notification_backend().notify(title, body)
    except Exception:
        exception_once(
            logger,
            "notification_failed",
            "desktop notification could not be raised",
        )
