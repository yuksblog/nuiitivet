"""Per-window IME state shared across backends.

Each :class:`~nuiitivet.runtime.window.Window` owns one :class:`IMEManager`
(``Window.ime``). The window's focused text field publishes its cursor rect
into it, the backend publishes the window's screen geometry, and the platform
IME hook for that OS window reads both back to position native IME UI (the
candidate window). There is no process-wide instance: two windows never share
composition geometry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IMECursorInfo:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0


class IMEManager:
    """IME geometry for one window: cursor rect and window location/size."""

    def __init__(self) -> None:
        self.cursor_rect = IMECursorInfo()
        self.window_location: tuple[int, int] = (0, 0)
        self.window_size: tuple[int, int] = (0, 0)

    def update_cursor_rect(self, x: float, y: float, width: float, height: float) -> None:
        """Publish the focused text field's cursor rect, in window-local logical coordinates."""
        self.cursor_rect.x = x
        self.cursor_rect.y = y
        self.cursor_rect.width = width
        self.cursor_rect.height = height

    def update_window_info(self, x: int, y: int, width: int, height: int) -> None:
        """Publish the window's screen location and logical size."""
        self.window_location = (x, y)
        self.window_size = (width, height)
