import ctypes
from ctypes import wintypes
import logging
import sys

from nuiitivet.common.logging_once import exception_once


_logger = logging.getLogger(__name__)

if sys.platform == "win32":
    # Define types and constants
    user32 = ctypes.windll.user32
    imm32 = ctypes.windll.imm32
    kernel32 = ctypes.windll.kernel32

    GWLP_WNDPROC = -4
    WM_IME_COMPOSITION = 0x010F
    WM_IME_STARTCOMPOSITION = 0x010D
    WM_IME_ENDCOMPOSITION = 0x010E

    GCS_COMPSTR = 0x0008
    GCS_CURSORPOS = 0x0080

    # WNDPROC type
    # LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM)
    # LRESULT is LONG_PTR (long long on 64-bit)
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        LRESULT = ctypes.c_longlong
        SetWindowLongPtr = user32.SetWindowLongPtrW
    else:
        LRESULT = ctypes.c_long
        SetWindowLongPtr = user32.SetWindowLongW

    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, WNDPROC]
    SetWindowLongPtr.restype = LRESULT

    CallWindowProc = user32.CallWindowProcW
    CallWindowProc.argtypes = [LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    CallWindowProc.restype = LRESULT

    # Store original WndProc
    _original_wndprocs = {}
    _hwnd_to_window = {}

    def _get_composition_string(himc, flag):
        # Get size first
        size = imm32.ImmGetCompositionStringW(himc, flag, None, 0)
        if size <= 0:
            return ""

        # Get data
        buf = ctypes.create_unicode_buffer(size // 2)  # size is in bytes
        imm32.ImmGetCompositionStringW(himc, flag, buf, size)
        return buf.value

    def _wnd_proc_hook(hwnd, msg, wParam, lParam):
        window = _hwnd_to_window.get(hwnd)

        if msg == WM_IME_COMPOSITION:
            if lParam & GCS_COMPSTR:
                himc = imm32.ImmGetContext(hwnd)
                if himc:
                    try:
                        text = _get_composition_string(himc, GCS_COMPSTR)
                        # Cursor position
                        cursor_pos = 0
                        if lParam & GCS_CURSORPOS:
                            cursor_pos = imm32.ImmGetCompositionStringW(himc, GCS_CURSORPOS, None, 0)

                        # Dispatch event
                        if window:
                            # Selection length is not easily available from simple GCS_CURSORPOS.
                            # For now assume 0 length selection (cursor).
                            try:
                                window.dispatch_event("on_ime_composition", text, cursor_pos, 0)
                            except Exception:
                                exception_once(
                                    _logger,
                                    "ime_windows_dispatch_on_ime_composition_exc",
                                    "IME composition dispatch raised",
                                )
                    finally:
                        imm32.ImmReleaseContext(hwnd, himc)

        # Call original WndProc
        original = _original_wndprocs.get(hwnd)
        if original:
            return CallWindowProc(original, hwnd, msg, wParam, lParam)
        return 0

    # Keep reference to the hook to prevent GC
    _hook_proto = WNDPROC(_wnd_proc_hook)

    def install_patch(window):
        if not hasattr(window, "_hwnd"):
            return

        hwnd = window._hwnd
        _hwnd_to_window[hwnd] = window

        # Register event type
        try:
            window.register_event_type("on_ime_composition")
        except Exception:
            exception_once(
                _logger,
                "ime_windows_register_event_type_exc",
                "register_event_type(on_ime_composition) raised",
            )

        # Subclass
        # GetWindowLongPtrW might not be available directly in user32 on some systems
        # (it's a macro wrapping GetWindowLongW on 32bit)
        # But ctypes.windll.user32 usually exposes it on 64bit.
        try:
            get_ptr = user32.GetWindowLongPtrW
            get_ptr.argtypes = [wintypes.HWND, ctypes.c_int]
            get_ptr.restype = LRESULT
        except AttributeError:
            get_ptr = user32.GetWindowLongW
            get_ptr.argtypes = [wintypes.HWND, ctypes.c_int]
            get_ptr.restype = ctypes.c_long

        old_proc = get_ptr(hwnd, GWLP_WNDPROC)

        # Check if already hooked (simple check)
        hook_addr = ctypes.cast(_hook_proto, ctypes.c_void_p).value
        if old_proc != hook_addr:
            _original_wndprocs[hwnd] = old_proc
            SetWindowLongPtr(hwnd, GWLP_WNDPROC, _hook_proto)

else:

    def install_patch(window):
        pass
