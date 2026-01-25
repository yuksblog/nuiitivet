"""Snackbar style definition."""

from dataclasses import dataclass, replace
from typing import Optional, Union

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

PaddingLike = Union[int, tuple[int, int, int, int]]


@dataclass(frozen=True)
class SnackbarStyle:
    """Immutable style for Snackbar widgets."""

    background: Optional[ColorSpec] = ColorRole.ON_SURFACE
    foreground: Optional[ColorSpec] = ColorRole.SURFACE
    corner_radius: float = 4.0
    padding: PaddingLike = 16

    def copy_with(self, **changes) -> "SnackbarStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)
