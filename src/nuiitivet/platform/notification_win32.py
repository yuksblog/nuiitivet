"""In-process Windows notifications via ``Shell_NotifyIcon`` balloons.

Windows 10/11 render notification-area balloons as regular toast
notifications, and unlike WinRT toasts they need no registered
AppUserModelID — a plain ``python app.py`` run and a frozen build both work,
attributed to the tray icon's tooltip text. The trade-offs are a transient
notification-area icon while the balloon is up and no rich content (buttons,
images); a WinRT backend can be layered on top later for registered apps.

The tray icon must belong to a window whose thread pumps messages, so a
dedicated daemon thread owns a message-only window and runs the loop;
``notify`` posts into it and is therefore safe from any thread. The icon is
added when a balloon is shown and removed again when the balloon closes
(dismissed, timed out, or clicked), keeping the notification area clean
between notifications. While a tray icon is installed the balloon attaches to
that icon and no transient one is added.
"""

from __future__ import annotations

import ctypes
import logging
import queue
import sys
import threading

if sys.platform != "win32":  # pragma: no cover - guards Windows-only ctypes use
    raise ImportError("notification_win32 is only available on Windows")

from ctypes import wintypes

from . import notify_icon_win32 as _w
from .notification import NotificationBackend, NotificationError
from .tray_win32 import active_bridge


logger = logging.getLogger(__name__)

_user32 = _w.user32
_shell32 = _w.shell32

_WM_SHOW_NOTIFICATION = _w.WM_APP + 1
_WM_ICON_EVENT = _w.WM_APP + 2

_HWND_MESSAGE = wintypes.HWND(-3)

_ICON_UID = 1


class Win32NotificationBackend(NotificationBackend):
    """Windows notifications via an in-process notification-area balloon."""

    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._hwnd: int | None = None
        self._error: Exception | None = None
        self._icon_added = False
        self._hicon = None
        self._ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="nuiitivet-notifications", daemon=True
        )
        self._thread.start()
        if not self._ready.wait(timeout=5.0) or not self._hwnd:
            raise NotificationError(
                f"notification window could not be created: {self._error}"
            )

    # --- NotificationBackend ----------------------------------------------

    def notify(self, title: str, body: str) -> None:
        tray = active_bridge()
        if tray is not None and tray.show_balloon(title, body):
            return
        self._queue.put((title, body))
        if not _user32.PostMessageW(self._hwnd, _WM_SHOW_NOTIFICATION, 0, 0):
            raise NotificationError(
                f"posting to the notification thread failed "
                f"(error {ctypes.get_last_error()})"
            )

    # --- notification thread ----------------------------------------------

    def _run(self) -> None:
        try:
            hinstance = _w.kernel32.GetModuleHandleW(None)
            # Keep a reference: the window class holds this pointer for the
            # life of the process.
            self._wndproc = _w.WNDPROC(self._on_message)
            wndclass = _w.WNDCLASSW()
            wndclass.lpfnWndProc = self._wndproc
            wndclass.hInstance = hinstance
            wndclass.lpszClassName = "NuiitivetNotificationWindow"
            if not _user32.RegisterClassW(ctypes.byref(wndclass)):
                raise NotificationError(
                    f"RegisterClassW failed (error {ctypes.get_last_error()})"
                )
            self._hicon = _user32.LoadIconW(None, wintypes.LPCWSTR(_w.IDI_APPLICATION))
            self._hwnd = _user32.CreateWindowExW(
                0,
                wndclass.lpszClassName,
                "nuiitivet notifications",
                0,
                0,
                0,
                0,
                0,
                _HWND_MESSAGE,
                None,
                hinstance,
                None,
            )
            if not self._hwnd:
                raise NotificationError(
                    f"CreateWindowExW failed (error {ctypes.get_last_error()})"
                )
        except Exception as exc:
            self._error = exc
            return
        finally:
            self._ready.set()

        _w.run_message_loop()

    def _on_message(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        if message == _WM_SHOW_NOTIFICATION:
            try:
                title, body = self._queue.get_nowait()
            except queue.Empty:
                return 0
            try:
                self._show_balloon(title, body)
            except Exception:
                logger.exception("showing a notification balloon failed")
            return 0
        if message == _WM_ICON_EVENT:
            if lparam in (_w.NIN_BALLOONHIDE, _w.NIN_BALLOONTIMEOUT, _w.NIN_BALLOONUSERCLICK):
                self._remove_icon()
            return 0
        return _user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def _icon_data(self) -> _w.NOTIFYICONDATAW:
        data = _w.NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(_w.NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = _ICON_UID
        return data

    def _show_balloon(self, title: str, body: str) -> None:
        data = self._icon_data()
        data.uFlags = _w.NIF_MESSAGE | _w.NIF_ICON | _w.NIF_TIP | _w.NIF_INFO
        data.uCallbackMessage = _WM_ICON_EVENT
        data.hIcon = self._hicon
        # The tooltip doubles as the toast's attribution line.
        data.szTip = title[:127]
        data.szInfoTitle = title[:63]
        # An empty szInfo means "remove the balloon", so never send one.
        data.szInfo = (body or title)[:255]
        data.dwInfoFlags = _w.NIIF_INFO
        message = _w.NIM_MODIFY if self._icon_added else _w.NIM_ADD
        if not _shell32.Shell_NotifyIconW(message, ctypes.byref(data)):
            # The icon and this flag can disagree after Explorer restarts;
            # retry once with the opposite operation.
            fallback = _w.NIM_ADD if message == _w.NIM_MODIFY else _w.NIM_MODIFY
            if not _shell32.Shell_NotifyIconW(fallback, ctypes.byref(data)):
                raise NotificationError(
                    f"Shell_NotifyIconW failed (error {ctypes.get_last_error()})"
                )
        self._icon_added = True

    def _remove_icon(self) -> None:
        data = self._icon_data()
        _shell32.Shell_NotifyIconW(_w.NIM_DELETE, ctypes.byref(data))
        self._icon_added = False
