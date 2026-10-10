"""Initial placement of a pyglet window from a ``WindowPosition``.

The alignment is resolved against the screen's work area (the part not covered
by the taskbar, the menu bar or the dock) and applied to the window's outer
frame, title bar included. pyglet's ``set_location`` takes the client area's
top-left corner in top-left screen coordinates on every backend, so the frame
extents are added back before the call.

Each OS query falls back to the full screen and a zero frame when the platform
API is unavailable, so a failure costs accuracy, never the placement itself.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from dataclasses import dataclass
from typing import Any

import pyglet

from nuiitivet.common.logging_once import exception_once
from nuiitivet.layout.alignment import normalize_alignment
from nuiitivet.runtime.window_sizing import WindowPosition

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScreenRect:
    """A rectangle in top-left screen coordinates, ``+y`` down.

    Attributes:
        x: Left edge.
        y: Top edge.
        width: Width in screen pixels.
        height: Height in screen pixels.
    """

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class FrameExtents:
    """Pixels the OS frame adds around the client area on each side.

    Attributes:
        left: Frame width left of the client area.
        top: Frame height above the client area; the title bar.
        right: Frame width right of the client area.
        bottom: Frame height below the client area.
    """

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0


def client_location(
    pos: WindowPosition,
    work_area: ScreenRect,
    frame: FrameExtents,
    client_width: int,
    client_height: int,
) -> tuple[int, int]:
    """Return the client-area top-left that aligns the framed window inside ``work_area``.

    Args:
        pos: Alignment, offset and screen index. The offset moves the window
            in top-left coordinates: ``+x`` right, ``+y`` down.
        work_area: The target screen's work area.
        frame: The window's frame extents.
        client_width: Client-area width in screen pixels.
        client_height: Client-area height in screen pixels.
    """
    horizontal, vertical = normalize_alignment(pos.alignment_key, default=("center", "center"))
    outer_width = client_width + frame.left + frame.right
    outer_height = client_height + frame.top + frame.bottom
    outer_x = _align(horizontal, work_area.x, work_area.width, outer_width)
    outer_y = _align(vertical, work_area.y, work_area.height, outer_height)
    dx, dy = pos.offset
    return int(outer_x + frame.left + dx), int(outer_y + frame.top + dy)


def _align(axis: str, origin: int, extent: int, size: int) -> int:
    if axis == "start":
        return origin
    if axis == "end":
        return origin + extent - size
    return origin + (extent - size) // 2


def apply_initial_position(window: Any, pos: WindowPosition) -> None:
    """Move a freshly created pyglet window to ``pos``.

    Args:
        window: The pyglet window; its size is read as the client size.
        pos: Where the window goes.
    """
    screen = _target_screen(window, pos.screen_index)
    if screen is None:
        return
    work_area = work_area_of(screen, window)
    frame = frame_extents_of(window)
    x, y = client_location(pos, work_area, frame, int(window.width), int(window.height))
    window.set_location(x, y)


def _target_screen(window: Any, screen_index: int) -> Any:
    screens: list[Any] = []
    try:
        screens = list(pyglet.display.get_display().get_screens())
    except Exception:
        exception_once(logger, "window_placement_screens_exc", "Could not list screens")
    if not screens:
        return getattr(window, "screen", None)
    index = min(max(int(screen_index), 0), len(screens) - 1)
    return screens[index]


def work_area_of(screen: Any, window: Any) -> ScreenRect:
    """Return the screen's work area, or its full bounds when the OS gives none.

    Args:
        screen: A pyglet screen.
        window: The pyglet window, used on macOS for the coordinate flip.
    """
    bounds = ScreenRect(int(screen.x), int(screen.y), int(screen.width), int(screen.height))
    try:
        if sys.platform == "darwin":
            return _cocoa_work_area(screen, window) or bounds
        if sys.platform == "win32":
            return _win32_work_area(screen, ctypes.windll.user32) or bounds  # type: ignore[attr-defined]
        if sys.platform.startswith("linux"):
            from pyglet.libs.x11 import xlib

            return _x11_work_area(screen, window, xlib) or bounds
    except Exception:
        exception_once(logger, "window_placement_work_area_exc", "Could not read the screen's work area")
    return bounds


def frame_extents_of(window: Any) -> FrameExtents:
    """Return the window's frame extents, or a zero frame when the OS gives none.

    Args:
        window: The pyglet window.
    """
    try:
        if sys.platform == "darwin":
            return _cocoa_frame_extents(window._nswindow)
        if sys.platform == "win32":
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            return _win32_frame_extents(window._hwnd, user32) or FrameExtents()
        if sys.platform.startswith("linux"):
            from pyglet.libs.x11 import xlib

            return _x11_frame_extents(window, xlib) or FrameExtents()
    except Exception:
        exception_once(logger, "window_placement_frame_exc", "Could not read the window's frame extents")
    return FrameExtents()


# macOS: AppKit rectangles are bottom-left origin; pyglet's set_location flips
# y with the height of the window's current screen, so the same height flips
# the work area back.


def _cocoa_work_area(screen: Any, window: Any) -> ScreenRect | None:
    ns_screen = getattr(screen, "_ns_screen", None)
    if ns_screen is None:
        ns_screen = screen.get_nsscreen()
    if ns_screen is None:
        return None
    visible = ns_screen.visibleFrame()
    window_screen = window._nswindow.screen()
    flip_height = (window_screen if window_screen is not None else ns_screen).frame().size.height
    top = flip_height - (visible.origin.y + visible.size.height)
    return ScreenRect(int(visible.origin.x), int(top), int(visible.size.width), int(visible.size.height))


def _cocoa_frame_extents(nswindow: Any) -> FrameExtents:
    frame = nswindow.frame()
    content = nswindow.contentRectForFrameRect_(frame)
    return FrameExtents(
        left=int(content.origin.x - frame.origin.x),
        top=int((frame.origin.y + frame.size.height) - (content.origin.y + content.size.height)),
        right=int((frame.origin.x + frame.size.width) - (content.origin.x + content.size.width)),
        bottom=int(content.origin.y - frame.origin.y),
    )


# Windows: handles are passed as c_void_p so a 64-bit HWND or HMONITOR is not
# truncated to a C int by ctypes' default conversion.


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", ctypes.c_ulong),
    ]


def _handle(value: Any) -> ctypes.c_void_p:
    raw = getattr(value, "value", value)
    return ctypes.c_void_p(int(raw) if raw is not None else 0)


def _win32_work_area(screen: Any, user32: Any) -> ScreenRect | None:
    monitor = getattr(screen, "_handle", None)
    if not monitor:
        return None
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not user32.GetMonitorInfoW(_handle(monitor), ctypes.byref(info)):
        return None
    work = info.rcWork
    return ScreenRect(int(work.left), int(work.top), int(work.right - work.left), int(work.bottom - work.top))


def _win32_frame_extents(hwnd: Any, user32: Any) -> FrameExtents | None:
    if not hwnd:
        return None
    handle = _handle(hwnd)
    frame = _RECT()
    client = _RECT()
    origin = _POINT(0, 0)
    if not user32.GetWindowRect(handle, ctypes.byref(frame)):
        return None
    if not user32.GetClientRect(handle, ctypes.byref(client)):
        return None
    if not user32.ClientToScreen(handle, ctypes.byref(origin)):
        return None
    return FrameExtents(
        left=int(origin.x - frame.left),
        top=int(origin.y - frame.top),
        right=int(frame.right - (origin.x + client.right)),
        bottom=int(frame.bottom - (origin.y + client.bottom)),
    )


# X11: the work area and the frame extents are EWMH properties. A window
# manager sets _NET_FRAME_EXTENTS only after it has managed the window, so a
# window placed before that gets a zero frame.

_XA_CARDINAL = 6


def _x11_work_area(screen: Any, window: Any, xlib: Any) -> ScreenRect | None:
    display = window._x_display
    root = xlib.XRootWindow(display, window._x_screen_id)
    areas = _x11_cardinals(xlib, display, root, b"_NET_WORKAREA")
    current = _x11_cardinals(xlib, display, root, b"_NET_CURRENT_DESKTOP")
    desktop = current[0] if current else 0
    chunk = areas[desktop * 4 : desktop * 4 + 4]
    if len(chunk) < 4:
        return None
    # _NET_WORKAREA spans every monitor; the target screen's part is wanted.
    left = max(chunk[0], int(screen.x))
    top = max(chunk[1], int(screen.y))
    right = min(chunk[0] + chunk[2], int(screen.x) + int(screen.width))
    bottom = min(chunk[1] + chunk[3], int(screen.y) + int(screen.height))
    if right <= left or bottom <= top:
        return None
    return ScreenRect(left, top, right - left, bottom - top)


def _x11_frame_extents(window: Any, xlib: Any) -> FrameExtents | None:
    values = _x11_cardinals(xlib, window._x_display, window._window, b"_NET_FRAME_EXTENTS")
    if len(values) < 4:
        return None
    left, right, top, bottom = values[:4]
    return FrameExtents(left=left, top=top, right=right, bottom=bottom)


def _x11_cardinals(xlib: Any, display: Any, xwindow: Any, name: bytes) -> list[int]:
    atom = xlib.XInternAtom(display, name, True)
    if not atom:
        return []
    actual_type = xlib.Atom()
    actual_format = ctypes.c_int()
    count = ctypes.c_ulong()
    remaining = ctypes.c_ulong()
    data = ctypes.POINTER(ctypes.c_ubyte)()
    status = xlib.XGetWindowProperty(
        display,
        xwindow,
        atom,
        0,
        64,
        False,
        _XA_CARDINAL,
        ctypes.byref(actual_type),
        ctypes.byref(actual_format),
        ctypes.byref(count),
        ctypes.byref(remaining),
        ctypes.byref(data),
    )
    if status != 0 or not data:
        return []
    try:
        if actual_format.value != 32:
            return []
        longs = ctypes.cast(data, ctypes.POINTER(ctypes.c_long))
        return [int(longs[i]) for i in range(count.value)]
    finally:
        xlib.XFree(data)


__all__ = [
    "FrameExtents",
    "ScreenRect",
    "apply_initial_position",
    "client_location",
    "frame_extents_of",
    "work_area_of",
]
