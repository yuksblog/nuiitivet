"""Sheet style definitions for modal side sheets and bottom sheets."""

from __future__ import annotations

from dataclasses import dataclass, replace

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class SideSheetStyle:
    """Immutable container style for a modal side sheet.

    The framework wraps caller-supplied content in a container sized by this style.
    ``height`` defaults to ``"100%"`` so the sheet spans the full screen height.
    ``corner_radius`` is applied to the inner (away-from-edge) corners only.
    ``background_color`` defaults to ``ColorRole.SURFACE_CONTAINER_LOW`` per M3 spec.
    """

    width: SizingLike = 400
    height: SizingLike = "100%"
    corner_radius: float = 16.0
    background_color: ColorSpec = ColorRole.SURFACE_CONTAINER_LOW

    def copy_with(self, **changes) -> "SideSheetStyle":
        """Return a copy with the given fields replaced."""
        return replace(self, **changes)


@dataclass(frozen=True)
class BottomSheetStyle:
    """Immutable container style for a modal bottom sheet.

    The framework wraps caller-supplied content in a container sized by this style.
    ``width`` defaults to ``"100%"`` so the sheet spans the full screen width.
    ``height=None`` means the container sizes to its content.
    ``corner_radius`` is applied to the top corners only.
    ``background_color`` defaults to ``ColorRole.SURFACE_CONTAINER_LOW`` per M3 spec.
    """

    width: SizingLike = "100%"
    height: SizingLike = None
    corner_radius: float = 28.0
    background_color: ColorSpec = ColorRole.SURFACE_CONTAINER_LOW

    def copy_with(self, **changes) -> "BottomSheetStyle":
        """Return a copy with the given fields replaced."""
        return replace(self, **changes)


__all__ = ["SideSheetStyle", "BottomSheetStyle"]
