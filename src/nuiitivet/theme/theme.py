"""Core theme data structures.

This module defines the :class:`Theme` data class which acts as a container
for design-system specific theme data (extensions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, List, Type, TypeVar

from .types import ThemeExtension

_logger = logging.getLogger(__name__)

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

        Unlike the other ``of()`` APIs this one **never raises**: it falls back to
        a bare ``Theme(mode="light")`` when no ``AppScope`` is reachable. Paint
        code calls it on every frame — including for widgets that are deliberately
        detached (tests, offscreen measurement) — so a raising lookup would turn a
        cosmetic problem into a crash.

        The fallback has a sharp edge worth knowing: calling this from ``__init__``
        silently themes the widget with the light default *forever*, because the
        parent link needed to reach the app's theme does not exist yet. Read the
        theme in ``on_mount()`` or at paint time instead. That premature case logs
        a warning once per process; a genuinely detached context stays quiet.

        Args:
            context: A widget in the subtree from which to search upward.

        Returns:
            The app's current theme, or ``Theme(mode="light")`` when none is
            reachable.
        """
        from nuiitivet.common.logging_once import warning_once
        from nuiitivet.runtime.app import AppScope  # lazy import – avoids circular dep
        from nuiitivet.widgeting.context_lookup import find_provider, is_premature_lookup

        scope = find_provider(context, AppScope)
        if scope is None:
            if is_premature_lookup(context):
                warning_once(
                    _logger,
                    f"theme_of_before_mount:{type(context).__name__}",
                    "Theme.of() was called on %s before it was mounted (typically from "
                    "__init__); returning the default light theme, which will not follow "
                    "the app's theme. Read the theme in on_mount() instead.",
                    type(context).__name__,
                )
            return Theme(mode="light", extensions=[])
        return scope.theme_manager.current
