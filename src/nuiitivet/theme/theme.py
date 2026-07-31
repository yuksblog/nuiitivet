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

        **Reading registers a dependency.** The reader is recorded, and a theme
        change invalidates it: a composable is rebuilt, a leaf is re-measured and
        repainted. Nothing subscribes and nothing has to unsubscribe.

        Read where the value is consumed. A widget with a ``build()`` reads
        there; a leaf has no ``build()``, so it reads in ``paint()`` or
        ``preferred_size()``. Never read in ``__init__`` or ``on_mount``: what is
        resolved at mount and kept on a field is never corrected again.

        A detached context — a widget deliberately measured outside an App, as
        tests and offscreen sizing do — resolves no ``AppScope`` and quietly
        falls back to the light default rather than raising. Paint code runs this
        on every frame, so a raising lookup there would turn a cosmetic problem
        into a crash. Under a pull that fallback is self-correcting: the next
        read, once the widget is attached, resolves the real theme.

        Args:
            context: A widget in the subtree from which to search upward.

        Returns:
            The app's current theme, or ``Theme(mode="light")`` when no
            ``AppScope`` is reachable.

        Raises:
            RuntimeError: If ``context`` has not run ``Widget.__init__`` yet, so
                it has no parent link to resolve against and no identity to
                attribute a dependency to. Reading in ``__init__`` *after*
                ``super().__init__()`` is indistinguishable at runtime from
                measuring an unattached widget, so it is not rejected here;
                what makes it a bug is keeping the result, which the "read,
                never hold" rule forbids.
        """
        from nuiitivet.runtime.app import AppScope  # lazy import – avoids circular dep
        from nuiitivet.theme.dependency import register_theme_dependency
        from nuiitivet.widgeting.context_lookup import find_provider, is_uninitialized_context

        scope = find_provider(context, AppScope)
        if scope is None:
            if is_uninitialized_context(context):
                raise RuntimeError(
                    f"Theme.of() was called on {type(context).__name__} before super().__init__() "
                    f"had run, so it has no parent link yet and cannot resolve a theme. "
                    f"Read the theme where its value is used: in build() if the widget has one, "
                    f"otherwise in paint() or preferred_size()."
                )
            return Theme(mode="light", extensions=[])
        register_theme_dependency(context)
        return scope.theme_manager.current
