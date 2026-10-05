"""Per-window IME state shared across backends.

Each :class:`~nuiitivet.runtime.window.Window` owns one :class:`IMEManager`
(``Window.ime``). The window's focused text field registers where its caret
is, the backend publishes the window's screen geometry, and the platform IME
hook for that OS window reads both back to position native IME UI (the
candidate window). There is no process-wide instance: two windows never share
composition geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

CursorSource = Callable[[], Optional[Tuple[float, float, float, float]]]


@dataclass
class IMECursorInfo:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0


class IMEManager:
    """IME geometry for one window: cursor rect and window location/size."""

    def __init__(self) -> None:
        self._cursor_rect = IMECursorInfo()
        self._cursor_source: Optional[CursorSource] = None
        self.window_location: tuple[int, int] = (0, 0)
        self.window_size: tuple[int, int] = (0, 0)

    @property
    def cursor_rect(self) -> IMECursorInfo:
        """The caret's rect in window-local logical coordinates, as of this read."""
        source = self._cursor_source
        rect = source() if source is not None else None
        if rect is not None:
            self._cursor_rect = IMECursorInfo(*rect)
        return self._cursor_rect

    @property
    def has_cursor_source(self) -> bool:
        """Whether a text field has registered its caret, which it does while it holds the focus."""
        return self._cursor_source is not None

    def set_cursor_source(self, source: CursorSource) -> None:
        """Register the function asked for the caret's rect on every read.

        A field whose caret moves without the field hearing of it, as when the
        content around it scrolls, registers a source and publishes nothing.

        Args:
            source: Returns ``(x, y, width, height)`` in window-local logical
                coordinates, or ``None`` to keep the last rect.
        """
        self._cursor_source = source

    def clear_cursor_source(self, source: CursorSource) -> None:
        """Drop *source* if it is the one registered; another field's stays.

        Args:
            source: The function passed to :meth:`set_cursor_source`.
        """
        if self._cursor_source == source:
            self._cursor_source = None

    def update_cursor_rect(self, x: float, y: float, width: float, height: float) -> None:
        """Publish a cursor rect, in window-local logical coordinates.

        It replaces a registered source: the last writer owns the caret.

        Args:
            x: Left edge.
            y: Top edge.
            width: Caret width.
            height: Caret height.
        """
        self._cursor_source = None
        self._cursor_rect = IMECursorInfo(x, y, width, height)

    def update_window_info(self, x: int, y: int, width: int, height: int) -> None:
        """Publish the window's screen location and logical size."""
        self.window_location = (x, y)
        self.window_size = (width, height)
