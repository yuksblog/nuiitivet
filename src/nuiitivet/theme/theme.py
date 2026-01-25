"""Core theme data structures.

This module defines the :class:`Theme` data class which acts as a container
for design-system specific theme data (extensions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Type, TypeVar

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

    def extension(self, type: Type[T]) -> T | None:
        """Get an extension by type."""
        for ext in self.extensions:
            if isinstance(ext, type):
                return ext
        return None
