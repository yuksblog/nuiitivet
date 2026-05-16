"""Core theme data structures.

This module defines the :class:`Theme` data class which acts as a container
for design-system specific theme data (extensions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Type, TypeVar

from .types import ThemeExtension

T = TypeVar("T", bound=ThemeExtension)

ColorValue = str


@dataclass(frozen=True)
class Theme:
    """Theme container holding design system extensions.

    The Theme class itself is design-agnostic. It holds a list of
    ThemeExtension objects (like MaterialThemeData, CupertinoThemeData)
    that define the actual look and feel.
    """

    mode: str  # 'light' | 'dark' etc.
    extensions: List[ThemeExtension] = field(default_factory=list)
    name: str = ""

    def __post_init__(self) -> None:
        types = [type(e) for e in self.extensions]
        if len(types) != len(set(types)):
            raise ValueError("Duplicate ThemeExtension types are not allowed")

    def extension(self, type: Type[T]) -> T | None:
        """Get an extension by type."""
        for ext in self.extensions:
            if isinstance(ext, type):
                return ext
        return None

    @staticmethod
    def of(context: Any) -> "Theme":
        """Return the current :class:`Theme` from the nearest :class:`AppScope`.

        Falls back to a bare ``Theme(mode="light")`` when called outside of a
        mounted widget tree (e.g. during construction or in tests).
        """
        from nuiitivet.runtime.app import AppScope  # lazy import – avoids circular dep

        scope = None
        try:
            scope = context.find_ancestor(AppScope)
        except AttributeError:
            pass  # Widget not yet initialized (_parent not set)
        if scope is None:
            return Theme(mode="light", extensions=[])
        return scope.theme_manager.current
