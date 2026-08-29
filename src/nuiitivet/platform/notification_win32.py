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
between notifications.
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

from .notification import NotificationBackend, NotificationError


logger = logging.getLogger(__name__)

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_shell32 = ctypes.WinDLL("shell32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_WM_APP = 0x8000
_WM_SHOW_NOTIFICATION = _WM_APP + 1
_WM_ICON_EVENT = _WM_APP + 2

_NIF_MESSAGE = 0x01
_NIF_ICON = 0x02
_NIF_TIP = 0x04
_NIF_INFO = 0x10

_NIM_ADD = 0x0
_NIM_MODIFY = 0x1
_NIM_DELETE = 0x2

_NIIF_INFO = 0x1

# Balloon lifecycle events delivered through uCallbackMessage (legacy,
# pre-NOTIFYICON_VERSION_4 protocol: the event id arrives in lParam).
_NIN_BALLOONHIDE = 0x0403
_NIN_BALLOONTIMEOUT = 0x0404
_NIN_BALLOONUSERCLICK = 0x0405

_IDI_APPLICATION = 32512
_HWND_MESSAGE = wintypes.HWND(-3)

_LRESULT = ctypes.c_ssize_t
_WNDPROC = ctypes.WINFUNCTYPE(
    _LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class _NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", wintypes.UINT),  # union with uTimeout (deprecated)
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_ubyte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


_user32.CreateWindowExW.restype = wintypes.HWND
_user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.c_void_p,
    wintypes.HINSTANCE,
    ctypes.c_void_p,
]
_user32.DefWindowProcW.restype = _LRESULT
_user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
_user32.PostMessageW.restype = wintypes.BOOL
_user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
_user32.GetMessageW.restype = ctypes.c_int
_user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
_user32.LoadIconW.restype = wintypes.HICON
_user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
_kernel32.GetModuleHandleW.restype = wintypes.HMODULE
_kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
_shell32.Shell_NotifyIconW.restype = wintypes.BOOL
_shell32.Shell_NotifyIconW.argtypes = [
    wintypes.DWORD,
    ctypes.POINTER(_NOTIFYICONDATAW),
]

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
        self._queue.put((title, body))
        if not _user32.PostMessageW(self._hwnd, _WM_SHOW_NOTIFICATION, 0, 0):
            raise NotificationError(
                f"posting to the notification thread failed "
                f"(error {ctypes.get_last_error()})"
            )

    # --- notification thread ----------------------------------------------

    def _run(self) -> None:
        try:
            hinstance = _kernel32.GetModuleHandleW(None)
            # Keep a reference: the window class holds this pointer for the
            # life of the process.
            self._wndproc = _WNDPROC(self._on_message)
            wndclass = _WNDCLASSW()
            wndclass.lpfnWndProc = self._wndproc
            wndclass.hInstance = hinstance
            wndclass.lpszClassName = "NuiitivetNotificationWindow"
            if not _user32.RegisterClassW(ctypes.byref(wndclass)):
                raise NotificationError(
                    f"RegisterClassW failed (error {ctypes.get_last_error()})"
                )
            self._hicon = _user32.LoadIconW(None, wintypes.LPCWSTR(_IDI_APPLICATION))
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

        msg = wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

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
            if lparam in (_NIN_BALLOONHIDE, _NIN_BALLOONTIMEOUT, _NIN_BALLOONUSERCLICK):
                self._remove_icon()
            return 0
        return _user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def _icon_data(self) -> _NOTIFYICONDATAW:
        data = _NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(_NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = _ICON_UID
        return data

    def _show_balloon(self, title: str, body: str) -> None:
        data = self._icon_data()
        data.uFlags = _NIF_MESSAGE | _NIF_ICON | _NIF_TIP | _NIF_INFO
        data.uCallbackMessage = _WM_ICON_EVENT
        data.hIcon = self._hicon
        # The tooltip doubles as the toast's attribution line.
        data.szTip = title[:127]
        data.szInfoTitle = title[:63]
        # An empty szInfo means "remove the balloon", so never send one.
        data.szInfo = (body or title)[:255]
        data.dwInfoFlags = _NIIF_INFO
        message = _NIM_MODIFY if self._icon_added else _NIM_ADD
        if not _shell32.Shell_NotifyIconW(message, ctypes.byref(data)):
            # The icon and this flag can disagree after Explorer restarts;
            # retry once with the opposite operation.
            fallback = _NIM_ADD if message == _NIM_MODIFY else _NIM_MODIFY
            if not _shell32.Shell_NotifyIconW(fallback, ctypes.byref(data)):
                raise NotificationError(
                    f"Shell_NotifyIconW failed (error {ctypes.get_last_error()})"
                )
        self._icon_added = True

    def _remove_icon(self) -> None:
        data = self._icon_data()
        _shell32.Shell_NotifyIconW(_NIM_DELETE, ctypes.byref(data))
        self._icon_added = False
