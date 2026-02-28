"""Divider style definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class DividerStyle:
    """Immutable style for the Divider widget.

    Attributes:
        color: Line color. Defaults to the M3 Outline Variant color role.
        thickness: Line thickness in pixels. Defaults to ``1`` (1dp per M3 spec).
        inset_left: Left-side inset in pixels. Defaults to ``0``.
            For vertical orientation this is applied to the top side.
        inset_right: Right-side inset in pixels. Defaults to ``0``.
            For vertical orientation this is applied to the bottom side.
    """

    color: ColorSpec = ColorRole.OUTLINE_VARIANT
    thickness: int = 1
    inset_left: int = 0
    inset_right: int = 0

    def copy_with(self, **changes) -> "DividerStyle":
        """Return a copy of this style with the given fields overridden.

        Args:
            **changes: Fields to override.

        Returns:
            A new :class:`DividerStyle` with the specified changes applied.
        """
        return replace(self, **changes)
