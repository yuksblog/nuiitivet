"""Scrollable placement style definitions.

Lives in the framework-common ``scrolling`` package (not under ``material``):
placement carries no design-system dependency.

Separates *placement* (where the viewport and bar sit) from *appearance*
(:class:`~nuiitivet.scrolling.ScrollbarStyle`, the bar's own look) and
*temporal behavior* (:class:`~nuiitivet.scrolling.ScrollbarBehavior`,
e.g. auto-hide). These are independent axes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from nuiitivet.rendering.padding import PaddingLike


@dataclass(frozen=True)
class ScrollableStyle:
    """Immutable placement style for a ``Scrollable``.

    Owns *where* the viewport and the scrollbar sit, independently of how the
    bar looks (:class:`ScrollbarStyle`) or when it is shown
    (:class:`~nuiitivet.scrolling.ScrollbarBehavior`).

    Attributes:
        viewport_padding: Inner padding of the viewport (scrolled area).
            Accepts a single int or a padding tuple. Defaults to ``0``.
        scrollbar_padding: Offset of the scrollbar from the viewport edge.
            Accepts a single int or a padding tuple. Defaults to ``2``.
        scrollbar_overlay: When ``True`` the bar is drawn on top of the content
            without reserving space (overlay). When ``False`` a gutter is
            reserved for the bar (inline). Defaults to ``True``.
    """

    viewport_padding: PaddingLike = 0
    scrollbar_padding: PaddingLike = 2
    scrollbar_overlay: bool = True

    def copy_with(self, **changes) -> "ScrollableStyle":
        """Return a copy of this style with the given fields overridden.

        Args:
            **changes: Fields to override.

        Returns:
            A new :class:`ScrollableStyle` with the specified changes applied.
        """
        return replace(self, **changes)
