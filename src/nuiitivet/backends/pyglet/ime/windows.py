"""The Windows IME hook: an IMM32 application that draws the composition itself.

The hook subclasses the window procedure. While a text input is its window's
caret source, the hook keeps the composition messages from the OS, which would
draw the composition in a floating box, and places the IME's windows at the
caret.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import sys
from typing import TYPE_CHECKING, Any

from nuiitivet.common.logging_once import exception_once

if TYPE_CHECKING:
    from nuiitivet.runtime.window import Window


_logger = logging.getLogger(__name__)

WM_IME_STARTCOMPOSITION = 0x010D
WM_IME_ENDCOMPOSITION = 0x010E
WM_IME_COMPOSITION = 0x010F
WM_IME_SETCONTEXT = 0x0281
_IME_MESSAGES = frozenset({WM_IME_STARTCOMPOSITION, WM_IME_ENDCOMPOSITION, WM_IME_COMPOSITION, WM_IME_SETCONTEXT})

ISC_SHOWUICOMPOSITIONWINDOW = 0x80000000

GCS_COMPSTR = 0x0008
GCS_CURSORPOS = 0x0080
GCS_RESULTSTR = 0x0800

CFS_POINT = 0x0002
CFS_FORCE_POSITION = 0x0020
CFS_EXCLUDE = 0x0080

NI_COMPOSITIONSTR = 0x0015
CPS_CANCEL = 0x0004


class COMPOSITIONFORM(ctypes.Structure):
    """IMM32's ``COMPOSITIONFORM``: where the composition window goes."""

    _fields_ = [("dwStyle", wintypes.DWORD), ("ptCurrentPos", wintypes.POINT), ("rcArea", wintypes.RECT)]


class CANDIDATEFORM(ctypes.Structure):
    """IMM32's ``CANDIDATEFORM``: where a candidate window goes."""

    _fields_ = [
        ("dwIndex", wintypes.DWORD),
        ("dwStyle", wintypes.DWORD),
        ("ptCurrentPos", wintypes.POINT),
        ("rcArea", wintypes.RECT),
    ]


def caret_in_client_pixels(win: Window) -> tuple[int, int, int, int]:
    """Return the caret of ``win`` as ``(left, top, right, bottom)`` in client pixels."""
    rect = win.ime.cursor_rect
    scale = win.pixel_ratio
    return (
        int(rect.x * scale),
        int(rect.y * scale),
        int((rect.x + rect.width) * scale),
        int((rect.y + rect.height) * scale),
    )


def process_message(imm: Any, hwnd: int, window: Any, win: Window, msg: int, lparam: int) -> tuple[bool, int]:
    """Handle one ``WM_IME_*`` message of a hooked window.

    While a text input is the caret source of ``win``, a commit reaches
    ``window`` as an empty ``on_ime_composition`` and one ``on_text``, and the
    end of a composition as an empty ``on_ime_composition``.

    Args:
        imm: The IMM32 functions.
        hwnd: The window the message was sent to.
        window: The pyglet window, which the text events are dispatched to.
        win: The window model, whose caret places the IME's windows.
        msg: The message.
        lparam: The message's ``lParam``.

    Returns:
        Whether the original window procedure still gets the message, and the
        ``lParam`` it gets.
    """
    if msg == WM_IME_SETCONTEXT:
        return True, lparam & ~ISC_SHOWUICOMPOSITIONWINDOW
    drawn_here = win.ime.has_cursor_source
    if msg == WM_IME_ENDCOMPOSITION:
        if drawn_here:
            # A cancel sends no empty composition of its own on every IME.
            _dispatch(window, "on_ime_composition", "", 0, 0)
        return True, lparam
    himc = imm.ImmGetContext(hwnd)
    if not himc:
        return True, lparam
    try:
        if msg == WM_IME_COMPOSITION:
            _dispatch_composition(imm, himc, window, lparam, commit=drawn_here)
        if drawn_here:
            _place_ime_windows(imm, himc, win)
    finally:
        imm.ImmReleaseContext(hwnd, himc)
    return not drawn_here, lparam


def _dispatch_composition(imm: Any, himc: int, window: Any, lparam: int, *, commit: bool) -> None:
    # The original window procedure turns a result string into WM_CHAR. It
    # never sees a message this hook keeps, so the commit is dispatched here.
    if commit and lparam & GCS_RESULTSTR:
        result = _composition_string(imm, himc, GCS_RESULTSTR)
        if result:
            # The key that confirmed was pressed before this message. A commit
            # into a live composition would make the field take the next Enter for that key.
            _dispatch(window, "on_ime_composition", "", 0, 0)
            _dispatch(window, "on_text", result)
    if lparam & GCS_COMPSTR:
        text = _composition_string(imm, himc, GCS_COMPSTR)
        cursor = 0
        if lparam & GCS_CURSORPOS:
            cursor = int(imm.ImmGetCompositionStringW(himc, GCS_CURSORPOS, None, 0))
        # IMM32 reports the caret alone, so the selection inside the composition is empty.
        _dispatch(window, "on_ime_composition", text, cursor, 0)


def _composition_string(imm: Any, himc: int, flag: int) -> str:
    size = int(imm.ImmGetCompositionStringW(himc, flag, None, 0))
    if size <= 0:
        return ""
    # ``size`` is in bytes, two per UTF-16 unit.
    buf = ctypes.create_unicode_buffer(size // 2)
    imm.ImmGetCompositionStringW(himc, flag, buf, size)
    return buf.value


def _place_ime_windows(imm: Any, himc: int, win: Window) -> None:
    # A raise here must not reach the caller: the message would be forwarded
    # after its commit was dispatched, and the OS would deliver the text again.
    try:
        left, top, right, bottom = caret_in_client_pixels(win)
    except Exception:
        exception_once(_logger, "ime_windows_caret_exc", "Reading the caret for the IME raised")
        return
    point = wintypes.POINT(left, top)
    composition = COMPOSITIONFORM(CFS_POINT | CFS_FORCE_POSITION, point, wintypes.RECT())
    imm.ImmSetCompositionWindow(himc, ctypes.byref(composition))
    # The candidate list opens beside the excluded rect, so it never covers the caret's line.
    candidates = CANDIDATEFORM(0, CFS_EXCLUDE, point, wintypes.RECT(left, top, right, bottom))
    imm.ImmSetCandidateWindow(himc, ctypes.byref(candidates))


def _dispatch(window: Any, event: str, *args: Any) -> None:
    try:
        window.dispatch_event(event, *args)
    except Exception:
        exception_once(_logger, f"ime_windows_dispatch_{event}_exc", f"IME {event} dispatch raised")


if sys.platform == "win32":
    user32 = ctypes.windll.user32
    imm32 = ctypes.windll.imm32

    GWLP_WNDPROC = -4

    # WNDPROC type
    # LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM)
    # LRESULT is LONG_PTR (long long on 64-bit)
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        LRESULT: Any = ctypes.c_longlong
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

    imm32.ImmGetContext.argtypes = [wintypes.HWND]
    imm32.ImmGetContext.restype = wintypes.HANDLE
    imm32.ImmReleaseContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
    imm32.ImmReleaseContext.restype = wintypes.BOOL
    imm32.ImmGetCompositionStringW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    imm32.ImmGetCompositionStringW.restype = wintypes.LONG
    imm32.ImmSetCompositionWindow.argtypes = [wintypes.HANDLE, ctypes.POINTER(COMPOSITIONFORM)]
    imm32.ImmSetCompositionWindow.restype = wintypes.BOOL
    imm32.ImmSetCandidateWindow.argtypes = [wintypes.HANDLE, ctypes.POINTER(CANDIDATEFORM)]
    imm32.ImmSetCandidateWindow.restype = wintypes.BOOL
    imm32.ImmNotifyIME.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
    imm32.ImmNotifyIME.restype = wintypes.BOOL

    # Keyed by HWND: the original window procedure, the pyglet window the text
    # events are dispatched to, and the window model the caret is read from.
    _original_wndprocs: dict[int, int] = {}
    _hwnd_to_window: dict[int, Any] = {}
    _hwnd_to_win: dict[int, Window] = {}

    def _wnd_proc_hook(hwnd, msg, wParam, lParam):
        window = _hwnd_to_window.get(hwnd)
        win = _hwnd_to_win.get(hwnd)
        if msg in _IME_MESSAGES and window is not None and win is not None:
            try:
                forward, lParam = process_message(imm32, hwnd, window, win, msg, lParam)
            except Exception:
                exception_once(_logger, "ime_windows_process_message_exc", "IME message handling raised")
                forward = True
            if not forward:
                return 0

        original = _original_wndprocs.get(hwnd)
        if original:
            return CallWindowProc(original, hwnd, msg, wParam, lParam)
        return 0

    # Keep reference to the hook to prevent GC
    _hook_proto = WNDPROC(_wnd_proc_hook)

    def discard_conversation(window: Any) -> None:
        """Cancel the IME's pending composition string for ``window``.

        Called when the window loses the OS focus, after the model side
        committed the composition. ``CPS_CANCEL`` (not ``CPS_COMPLETE``)
        because a complete would deliver the result string as new input on
        top of the already-committed text.
        """
        hwnd = getattr(window, "_hwnd", None)
        if not hwnd:
            return
        himc = imm32.ImmGetContext(hwnd)
        if not himc:
            return
        try:
            imm32.ImmNotifyIME(himc, NI_COMPOSITIONSTR, CPS_CANCEL, 0)
        finally:
            imm32.ImmReleaseContext(hwnd, himc)

    def install_patch(window: Any, win: Window) -> None:
        """Install the IME hook on ``window``'s window procedure.

        ``window`` is the pyglet window (text events are dispatched to it),
        ``win`` the nuiitivet Window model whose per-window ``ime`` state
        places the IME's windows.
        """
        if not hasattr(window, "_hwnd"):
            return

        hwnd = window._hwnd
        _hwnd_to_window[hwnd] = window
        _hwnd_to_win[hwnd] = win

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

    def install_patch(window: Any, win: Window) -> None:
        pass

    def discard_conversation(window: Any) -> None:
        pass
