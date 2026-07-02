"""Scrollbar style definitions.

Lives in the framework-common ``scrolling`` package (not under ``material``):
the scrollbar is a generic widget, and this style carries no design-system
dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ScrollbarStyle:
    """Immutable visual style for the scrollbar of a ``Scrollable``.

    Holds only the bar's own appearance. Placement (viewport padding, offset
    from the edge, overlay vs. inline) lives in
    :class:`~nuiitivet.scrolling.ScrollableStyle`; dynamic visibility is
    controlled by the ``scrollbar_visible`` parameter of the scrollable widget,
    and interaction behavior (auto-hide, track clicks, etc.) lives in
    :class:`~nuiitivet.widgets.scrollbar.ScrollbarBehavior`.

    Attributes:
        thickness: Scrollbar thickness in pixels. Defaults to ``8``.
        min_thumb_length: Minimum thumb length in pixels. Defaults to ``24``.
    """

    thickness: int = 8
    min_thumb_length: int = 24

    def copy_with(self, **changes) -> "ScrollbarStyle":
        """Return a copy of this style with the given fields overridden.

        Args:
            **changes: Fields to override.

        Returns:
            A new :class:`ScrollbarStyle` with the specified changes applied.
        """
        return replace(self, **changes)
