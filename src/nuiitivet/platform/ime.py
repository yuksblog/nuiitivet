"""IME state shared across backends.

Backends may update cursor/window information to position native IME UI.
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
    _instance: "IMEManager | None" = None

    def __init__(self) -> None:
        self.cursor_rect = IMECursorInfo()
        self.window_location: tuple[int, int] = (0, 0)
        self.window_size: tuple[int, int] = (0, 0)

    @classmethod
    def get(cls) -> "IMEManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update_cursor_rect(self, x: float, y: float, width: float, height: float) -> None:
        self.cursor_rect.x = x
        self.cursor_rect.y = y
        self.cursor_rect.width = width
        self.cursor_rect.height = height

    def update_window_info(self, x: int, y: int, width: int, height: int) -> None:
        self.window_location = (x, y)
        self.window_size = (width, height)
