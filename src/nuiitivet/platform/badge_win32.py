"""Windows app badge: an overlay icon on the main window's taskbar button.

``ITaskbarList3::SetOverlayIcon`` puts a small icon on the button's corner;
the badge text is drawn into that icon. The taskbar keeps its own copy of the
icon, and drops it when the button goes away with a hidden window.
"""

from __future__ import annotations

import sys

if sys.platform != "win32":  # pragma: no cover - guards Windows-only ctypes use
    raise ImportError("badge_win32 is only available on Windows")

from ctypes import byref, c_void_p, c_wchar_p, wintypes

from .badge import WindowHandle
from .badge_win32_plan import overlay_label, render_overlay_bgra
from .file_dialog_win32 import _CLSCTX_INPROC_SERVER, _COINIT_APARTMENTTHREADED, _GUID, _com_call, _ole32, _release
from .tray_win32 import _SM_CXSMICON, _create_icon, _user32

_CLSID_TaskbarList = "{56FDF344-FD6D-11D0-958A-006097C9A090}"
_IID_ITaskbarList3 = "{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}"

# --- ITaskbarList3 vtable slots (IUnknown 0-2) -----------------------------
_HR_INIT = 3
_SET_OVERLAY_ICON = 18


class TaskbarOverlayBridge:
    """Shows the badge as a taskbar overlay icon. Framework-internal."""

    def __init__(self, window_handle: WindowHandle) -> None:
        """Create the taskbar object; raises where COM cannot make one.

        Args:
            window_handle: Returns the ``HWND`` whose taskbar button carries
                the overlay, or ``None`` while that window does not exist.
        """
        self._window_handle = window_handle
        try:
            _ole32.CoInitializeEx(None, _COINIT_APARTMENTTHREADED)
        except OSError:
            # RPC_E_CHANGED_MODE: the thread already runs COM in another mode, which serves as well.
            pass
        self._taskbar = c_void_p()
        _ole32.CoCreateInstance(
            byref(_GUID(_CLSID_TaskbarList)),
            None,
            _CLSCTX_INPROC_SERVER,
            byref(_GUID(_IID_ITaskbarList3)),
            byref(self._taskbar),
        )
        _com_call(self._taskbar, _HR_INIT, argtypes=[])

    def show(self, label: str) -> None:
        """Show ``label`` on the taskbar button; an empty one removes the overlay."""
        hwnd = self._window_handle()
        if not hwnd or not self._taskbar:
            return
        hicon = None
        if label:
            size = _user32.GetSystemMetrics(_SM_CXSMICON)
            hicon = _create_icon(render_overlay_bgra(overlay_label(label), size), size)
            if not hicon:
                raise RuntimeError("the badge overlay icon could not be created")
        try:
            _com_call(
                self._taskbar,
                _SET_OVERLAY_ICON,
                hwnd,
                hicon,
                label or None,
                argtypes=[wintypes.HWND, wintypes.HICON, c_wchar_p],
            )
        finally:
            if hicon:
                _user32.DestroyIcon(hicon)

    def close(self) -> None:
        """Release the taskbar object."""
        taskbar, self._taskbar = self._taskbar, c_void_p()
        _release(taskbar)
