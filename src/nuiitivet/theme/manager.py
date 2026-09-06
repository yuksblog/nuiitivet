"""Theme manager.

Responsibilities:
- Keep track of the active ``Theme`` instance and tell its owner when it
    changes.

Theme construction and color algorithms belong in ``material_theme.py``.

There is deliberately **no subscriber registry** here. Widgets do not subscribe
to the theme; they read it, and the read registers a dependency that the
framework invalidates (``nuiitivet/theme/dependency.py``). The single
:attr:`on_change` hook belongs to the provider that owns this manager -- the
``AppScope`` -- and is what drives that invalidation.
"""

from __future__ import annotations

from typing import Callable, Optional
import logging
import threading

from .theme import Theme

logger = logging.getLogger(__name__)


class ThemeManager:
    """Holds the current Theme and notifies its owner on changes."""

    def __init__(
        self,
        initial: Optional[Theme] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._current = initial if initial is not None else Theme(mode="light", extensions=[])
        self._generation = 0
        #: Set by the owning provider. Not a subscriber list: exactly one owner.
        self.on_change: Optional[Callable[[Theme], None]] = None

    @property
    def current(self) -> Theme:
        # No lock: this is one reference read on every paint of every leaf, and
        # ``set_theme`` swaps the reference atomically.
        return self._current

    @property
    def generation(self) -> int:
        """Count of theme changes so far.

        Bumped before :attr:`on_change` runs, so anything deriving a value from
        the theme can tell whether what it holds is still current.
        """
        return self._generation

    def set_theme(self, theme: Theme) -> None:
        """Replace the current theme and notify the owner.

        Args:
            theme: The theme to make current.
        """
        with self._lock:
            self._current = theme
            self._generation += 1
            handler = self.on_change
        if handler is None:
            return
        try:
            handler(theme)
        except Exception:
            logger.exception("ThemeManager.on_change handler raised")


__all__ = ["ThemeManager"]
