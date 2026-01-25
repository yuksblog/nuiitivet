"""Theme manager and global state.

Responsibilities:
- Keep track of the active ``Theme`` instance and notify subscribers when
    it changes.

Public API provided here focuses on applying themes and on
subscription management. Theme construction and color algorithms belong in
``material_theme.py``.
"""

from __future__ import annotations

from typing import Callable, Optional, Set
import logging
import threading

from .theme import Theme

logger = logging.getLogger(__name__)


class ThemeManager:
    """Holds the current Theme and notifies subscribers on changes."""

    def __init__(
        self,
        initial: Optional[Theme] = None,
    ) -> None:
        self._subscribers: Set[Callable[[Theme], None]] = set()
        self._lock = threading.RLock()
        self._current = initial

    @property
    def current(self) -> Theme:
        with self._lock:
            if self._current is None:
                self._current = Theme(mode="light", extensions=[])
            return self._current

    def set_theme(self, theme: Theme) -> None:
        with self._lock:
            self._current = theme
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber(theme)
            except Exception:
                logger.exception("subscriber in ThemeManager raised")

    def subscribe(self, fn: Callable[[Theme], None]) -> None:
        with self._lock:
            self._subscribers.add(fn)

    def unsubscribe(self, fn: Callable[[Theme], None]) -> None:
        with self._lock:
            self._subscribers.discard(fn)


manager = ThemeManager()

__all__ = ["ThemeManager", "manager"]
