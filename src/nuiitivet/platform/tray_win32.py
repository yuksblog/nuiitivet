"""Windows tray icon: ``TrayIcon`` model → ``Shell_NotifyIcon``.

A dedicated daemon thread owns a hidden window and its message loop, and the
icon belongs to that window. The popup menu is built from the model on every
right click, so Observable ``label`` / ``enabled`` / ``checked`` are current
without a sync step. Activations hop onto the UI thread through the runtime
clock before they touch the model.

While a tray icon is installed, notification balloons attach to it
(:func:`active_bridge`) and no second icon appears.
"""

from __future__ import annotations

import ctypes
import logging
import queue
import sys
import threading
from typing import TYPE_CHECKING, Any, Callable, Optional, Sequence, Tuple

if sys.platform != "win32":  # pragma: no cover - guards Windows-only ctypes use
    raise ImportError("tray_win32 is only available on Windows")

from ctypes import wintypes

from nuiitivet.menus import read_value
from nuiitivet.observable import ObservableBase, runtime

from . import notify_icon_win32 as _w
from .tray_win32_plan import MF_POPUP, MenuItemPlan, load_icon_bgra, plan_menu

if TYPE_CHECKING:
    from .tray import TrayIcon

logger = logging.getLogger(__name__)

_gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

_WM_NULL = 0x0000
_WM_DESTROY = 0x0002
_WM_LBUTTONDBLCLK = 0x0203
_WM_RBUTTONUP = 0x0205

_WM_ICON_EVENT = _w.WM_APP + 1
_WM_SYNC_TOOLTIP = _w.WM_APP + 2
_WM_SHOW_BALLOON = _w.WM_APP + 3
_WM_STOP = _w.WM_APP + 4

_SM_CXSMICON = 49

_TPM_RIGHTBUTTON = 0x0002
_TPM_BOTTOMALIGN = 0x0020
_TPM_NONOTIFY = 0x0080
_TPM_RETURNCMD = 0x0100

_CLASS_NAME = "NuiitivetTrayWindow"
_ICON_UID = 1
_READY_TIMEOUT = 5.0
_STOP_TIMEOUT = 2.0


class _ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


_user32 = _w.user32
_user32.RegisterWindowMessageW.restype = wintypes.UINT
_user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
_user32.UnregisterClassW.restype = wintypes.BOOL
_user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
_user32.DestroyWindow.restype = wintypes.BOOL
_user32.DestroyWindow.argtypes = [wintypes.HWND]
_user32.PostQuitMessage.restype = None
_user32.PostQuitMessage.argtypes = [ctypes.c_int]
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.GetCursorPos.restype = wintypes.BOOL
_user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
_user32.GetSystemMetrics.restype = ctypes.c_int
_user32.GetSystemMetrics.argtypes = [ctypes.c_int]
_user32.CreatePopupMenu.restype = wintypes.HMENU
_user32.CreatePopupMenu.argtypes = []
_user32.AppendMenuW.restype = wintypes.BOOL
_user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
_user32.TrackPopupMenu.restype = ctypes.c_int
_user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.c_void_p,
]
_user32.DestroyMenu.restype = wintypes.BOOL
_user32.DestroyMenu.argtypes = [wintypes.HMENU]
_user32.CreateIconIndirect.restype = wintypes.HICON
_user32.CreateIconIndirect.argtypes = [ctypes.POINTER(_ICONINFO)]
_user32.DestroyIcon.restype = wintypes.BOOL
_user32.DestroyIcon.argtypes = [wintypes.HICON]
_gdi32.CreateBitmap.restype = wintypes.HBITMAP
_gdi32.CreateBitmap.argtypes = [
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
]
_gdi32.DeleteObject.restype = wintypes.BOOL
_gdi32.DeleteObject.argtypes = [ctypes.c_void_p]

_active: Optional["TrayWin32Bridge"] = None


def active_bridge() -> Optional["TrayWin32Bridge"]:
    """The installed tray bridge, or ``None`` while no tray icon is showing."""
    return _active


def _create_icon(pixels: bytes, size: int) -> Optional[int]:
    """Build an ``HICON`` from ``size`` x ``size`` top-down BGRA pixels."""
    color = _gdi32.CreateBitmap(size, size, 1, 32, pixels)
    # The alpha channel decides transparency; the mask is required but unused.
    mask_stride = ((size + 15) // 16) * 2
    mask = _gdi32.CreateBitmap(size, size, 1, 1, bytes(mask_stride * size))
    try:
        if not color or not mask:
            return None
        info = _ICONINFO(True, 0, 0, mask, color)
        hicon: Optional[int] = _user32.CreateIconIndirect(ctypes.byref(info))
        return hicon
    finally:
        # CreateIconIndirect copies both bitmaps.
        if color:
            _gdi32.DeleteObject(color)
        if mask:
            _gdi32.DeleteObject(mask)


def _build_menu(items: Sequence[MenuItemPlan]) -> int:
    """Create the ``HMENU`` for ``items``; destroying it destroys its submenus."""
    hmenu: Optional[int] = _user32.CreatePopupMenu()
    if not hmenu:
        raise RuntimeError(f"CreatePopupMenu failed (error {ctypes.get_last_error()})")
    for item in items:
        target = _build_menu(item.children) if item.flags & MF_POPUP else item.command_id
        _user32.AppendMenuW(hmenu, item.flags, target, item.label or None)
    return hmenu


class TrayWin32Bridge:
    """Installs a :class:`TrayIcon` in the Windows notification area. Framework-internal."""

    def __init__(self, tray: "TrayIcon") -> None:
        self._tray = tray
        self._hwnd: Optional[int] = None
        self._hicon: Optional[int] = None
        self._owns_icon = False
        self._taskbar_created = 0
        self._error: Optional[Exception] = None
        self._ready = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._wndproc: Any = None
        self._subscription: Any = None
        self._balloons: "queue.Queue[Tuple[str, str]]" = queue.Queue()

    def install(self) -> None:
        """Show the icon; raises when the notification area refuses it."""
        global _active
        self._thread = threading.Thread(target=self._run, name="nuiitivet-tray", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=_READY_TIMEOUT) or not self._hwnd:
            raise RuntimeError(f"tray icon could not be installed: {self._error}")

        tooltip = self._tray.tooltip
        if isinstance(tooltip, ObservableBase):

            def on_change(_value: Any) -> None:
                self._post(_WM_SYNC_TOOLTIP)

            self._subscription = tooltip.subscribe(on_change)
        _active = self

    def uninstall(self) -> None:
        """Remove the icon and stop the tray thread."""
        global _active
        if _active is self:
            _active = None
        subscription, self._subscription = self._subscription, None
        dispose = getattr(subscription, "dispose", None)
        if callable(dispose):
            dispose()
        thread, self._thread = self._thread, None
        if self._post(_WM_STOP) and thread is not None:
            thread.join(timeout=_STOP_TIMEOUT)

    def show_balloon(self, title: str, body: str) -> bool:
        """Show a notification balloon on the tray icon; safe from any thread.

        Args:
            title: The balloon title.
            body: The balloon text.

        Returns:
            ``False`` when the icon is gone and the balloon was not handed over.
        """
        self._balloons.put((title, body))
        return self._post(_WM_SHOW_BALLOON)

    def _post(self, message: int) -> bool:
        hwnd = self._hwnd
        return bool(hwnd) and bool(_user32.PostMessageW(hwnd, message, 0, 0))

    # ---- Tray thread --------------------------------------------------------

    def _run(self) -> None:
        hinstance = _w.kernel32.GetModuleHandleW(None)
        registered = False
        try:
            try:
                # Keep a reference: the window class holds this pointer.
                self._wndproc = _w.WNDPROC(self._on_message)
                wndclass = _w.WNDCLASSW()
                wndclass.lpfnWndProc = self._wndproc
                wndclass.hInstance = hinstance
                wndclass.lpszClassName = _CLASS_NAME
                if not _user32.RegisterClassW(ctypes.byref(wndclass)):
                    raise RuntimeError(f"RegisterClassW failed (error {ctypes.get_last_error()})")
                registered = True
                self._taskbar_created = _user32.RegisterWindowMessageW("TaskbarCreated")
                self._hicon, self._owns_icon = self._load_icon()
                # Top-level and never shown: a message-only window receives no
                # broadcasts, and TaskbarCreated is one.
                self._hwnd = _user32.CreateWindowExW(
                    0, _CLASS_NAME, "nuiitivet tray", 0, 0, 0, 0, 0, None, None, hinstance, None
                )
                if not self._hwnd:
                    raise RuntimeError(f"CreateWindowExW failed (error {ctypes.get_last_error()})")
                if not self._add_icon():
                    raise RuntimeError(f"Shell_NotifyIconW failed (error {ctypes.get_last_error()})")
            except Exception as exc:
                self._error = exc
                hwnd, self._hwnd = self._hwnd, None
                if hwnd:
                    _user32.DestroyWindow(hwnd)
                return
            finally:
                self._ready.set()
            _w.run_message_loop()
        finally:
            if self._owns_icon and self._hicon:
                _user32.DestroyIcon(self._hicon)
            if registered:
                # A later install registers the class again with its own WndProc.
                _user32.UnregisterClassW(_CLASS_NAME, hinstance)

    def _on_message(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        try:
            if self._handle(hwnd, message, lparam):
                return 0
        except Exception:
            logger.exception("tray window procedure raised")
            return 0
        result: int = _user32.DefWindowProcW(hwnd, message, wparam, lparam)
        return result

    def _handle(self, hwnd: int, message: int, lparam: int) -> bool:
        if message == _WM_ICON_EVENT:
            event = lparam & 0xFFFF
            if event == _WM_RBUTTONUP:
                self._show_menu()
            elif event == _WM_LBUTTONDBLCLK:
                self._hop(self._tray._fire_activate)
            return True
        if message == _WM_SYNC_TOOLTIP:
            data = self._icon_data(_w.NIF_TIP)
            data.szTip = self._tooltip_text()
            _w.shell32.Shell_NotifyIconW(_w.NIM_MODIFY, ctypes.byref(data))
            return True
        if message == _WM_SHOW_BALLOON:
            self._show_balloon()
            return True
        if message == _WM_STOP:
            _w.shell32.Shell_NotifyIconW(_w.NIM_DELETE, ctypes.byref(self._icon_data(0)))
            _user32.DestroyWindow(hwnd)
            return True
        if message == _WM_DESTROY:
            self._hwnd = None
            _user32.PostQuitMessage(0)
            return True
        if self._taskbar_created and message == self._taskbar_created:
            # Explorer restarted and dropped every icon.
            self._add_icon()
            return True
        return False

    def _icon_data(self, flags: int) -> Any:
        data = _w.NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(_w.NOTIFYICONDATAW)
        data.hWnd = self._hwnd
        data.uID = _ICON_UID
        data.uFlags = flags
        return data

    def _tooltip_text(self) -> str:
        return str(read_value(self._tray.tooltip) or "")[:127]

    def _add_icon(self) -> bool:
        data = self._icon_data(_w.NIF_MESSAGE | _w.NIF_ICON | _w.NIF_TIP)
        data.uCallbackMessage = _WM_ICON_EVENT
        data.hIcon = self._hicon
        data.szTip = self._tooltip_text()
        return bool(_w.shell32.Shell_NotifyIconW(_w.NIM_ADD, ctypes.byref(data)))

    def _load_icon(self) -> Tuple[Optional[int], bool]:
        """Return the ``HICON`` and whether this bridge must destroy it."""
        path = self._tray.icon_path
        if path is not None:
            size = _user32.GetSystemMetrics(_SM_CXSMICON)
            try:
                pixels = load_icon_bgra(path, size)
            except Exception:
                pixels = None
            hicon = _create_icon(pixels, size) if pixels is not None else None
            if hicon:
                return hicon, True
            logger.warning("Tray icon image failed to load: %s", path)
        # The notification area requires an icon; the stock application icon is shared.
        return _user32.LoadIconW(None, wintypes.LPCWSTR(_w.IDI_APPLICATION)), False

    def _show_balloon(self) -> None:
        try:
            title, body = self._balloons.get_nowait()
        except queue.Empty:
            return
        data = self._icon_data(_w.NIF_INFO)
        data.szInfoTitle = title[:63]
        # An empty szInfo means "remove the balloon", so never send one.
        data.szInfo = (body or title)[:255]
        data.dwInfoFlags = _w.NIIF_INFO
        if not _w.shell32.Shell_NotifyIconW(_w.NIM_MODIFY, ctypes.byref(data)):
            logger.warning("showing a notification balloon on the tray icon failed")

    def _show_menu(self) -> None:
        if not self._tray.menu:
            return
        items, commands = plan_menu(self._tray.menu)
        hmenu = _build_menu(items)
        try:
            point = wintypes.POINT()
            _user32.GetCursorPos(ctypes.byref(point))
            # A menu whose owner is not the foreground window stays open on an outside click.
            _user32.SetForegroundWindow(self._hwnd)
            command = _user32.TrackPopupMenu(
                hmenu,
                _TPM_RIGHTBUTTON | _TPM_BOTTOMALIGN | _TPM_NONOTIFY | _TPM_RETURNCMD,
                point.x,
                point.y,
                0,
                self._hwnd,
                None,
            )
            # Forces a task switch so the next right click opens the menu again.
            _user32.PostMessageW(self._hwnd, _WM_NULL, 0, 0)
        finally:
            _user32.DestroyMenu(hmenu)
        entry = commands.get(command)
        if entry is not None:
            self._hop(lambda: self._tray._activate_item(entry))

    def _hop(self, fn: Callable[[], None]) -> None:
        """Run ``fn`` on the UI thread."""
        runtime.clock.schedule_once(lambda _dt: fn(), 0.0)
