"""ButtonGroup style definitions for M3 button groups.

Provides two concrete style classes:

- ``StandardButtonGroupStyle``: For action-oriented groups with independent
  fully-rounded pill segments.
- ``ConnectedButtonGroupStyle``: For option-selector / view-switcher groups
  with junction corners and selection state colours.

Each style offers ``filled()``, ``tonal()``, and ``outlined()`` factory
classmethods that accept a ``ButtonGroupSize`` to set M3-spec size tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal, Optional, TYPE_CHECKING, Union

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme import Theme

# ---------------------------------------------------------------------------
# Size type
# ---------------------------------------------------------------------------

ButtonGroupSize = Literal["xs", "s", "m", "l", "xl"]
"""Size variant for a ButtonGroup, mapping to M3 spec size tokens."""

# ---------------------------------------------------------------------------
# Size token tables (M3 spec)
# ---------------------------------------------------------------------------

_STANDARD_SIZE_TOKENS: dict[str, dict[str, int | float]] = {
    "xs": {
        "container_height": 32,
        "item_gap": 18,
        "outer_corner_radius": 16.0,
        "pressed_inner_corner_radius": 8.0,
    },
    "s": {
        "container_height": 40,
        "item_gap": 12,
        "outer_corner_radius": 20.0,
        "pressed_inner_corner_radius": 8.0,
    },
    "m": {
        "container_height": 56,
        "item_gap": 8,
        "outer_corner_radius": 28.0,
        "pressed_inner_corner_radius": 8.0,
    },
    "l": {
        "container_height": 96,
        "item_gap": 8,
        "outer_corner_radius": 48.0,
        "pressed_inner_corner_radius": 8.0,
    },
    "xl": {
        "container_height": 136,
        "item_gap": 8,
        "outer_corner_radius": 68.0,
        "pressed_inner_corner_radius": 8.0,
    },
}

_CONNECTED_SIZE_TOKENS: dict[str, dict[str, int | float]] = {
    "xs": {
        "container_height": 32,
        "item_gap": 2,
        "outer_corner_radius": 16.0,
        "inner_corner_radius": 8.0,
        "pressed_inner_corner_radius": 4.0,
    },
    "s": {
        "container_height": 40,
        "item_gap": 2,
        "outer_corner_radius": 20.0,
        "inner_corner_radius": 8.0,
        "pressed_inner_corner_radius": 4.0,
    },
    "m": {
        "container_height": 56,
        "item_gap": 2,
        "outer_corner_radius": 28.0,
        "inner_corner_radius": 8.0,
        "pressed_inner_corner_radius": 4.0,
    },
    "l": {
        "container_height": 96,
        "item_gap": 2,
        "outer_corner_radius": 48.0,
        "inner_corner_radius": 16.0,
        "pressed_inner_corner_radius": 12.0,
    },
    "xl": {
        "container_height": 136,
        "item_gap": 2,
        "outer_corner_radius": 68.0,
        "inner_corner_radius": 20.0,
        "pressed_inner_corner_radius": 16.0,
    },
}


# ===================================================================
# StandardButtonGroupStyle
# ===================================================================


@dataclass(frozen=True)
class StandardButtonGroupStyle:
    """Immutable style for ``StandardButtonGroup`` (M3-compliant).

    All segments are independent fully-rounded pills.  There is no
    junction-corner concept; ``inner_corner_radius`` always equals
    ``outer_corner_radius`` (exposed as a read-only property).

    Use ``filled()``, ``tonal()``, or ``outlined()`` to create a preset,
    optionally passing a ``ButtonGroupSize``.
    """

    # Container colours
    background: Optional[ColorSpec] = None
    foreground: Optional[ColorSpec] = None
    border_color: Optional[ColorSpec] = None
    border_width: float = 0.0

    # Selection colours
    selected_background: Optional[ColorSpec] = None
    selected_foreground: Optional[ColorSpec] = None

    # Sizing
    container_height: int = 40
    item_gap: int = 12
    min_item_width: int = 48

    # Shape tokens
    outer_corner_radius: float = 20.0
    pressed_outer_corner_radius: float = 8.0
    pressed_inner_corner_radius: float = 8.0

    # State overlay
    overlay_color: Optional[ColorSpec] = None
    overlay_alpha: float = 0.12

    # -- Derived properties (read-only interface for GroupButton) ----------

    @property
    def inner_corner_radius(self) -> float:
        """Inner corner radius equals outer (fully-rounded pill)."""
        return self.outer_corner_radius

    @property
    def selected_inner_corner_radius(self) -> float:
        """Not applicable; returns ``0.0``."""
        return 0.0

    @property
    def selected_border_color(self) -> Optional[ColorSpec]:
        """No distinct selected border; falls back to ``border_color``."""
        return self.border_color

    # -- Mutations ----------------------------------------------------------

    def copy_with(self, **changes: Any) -> "StandardButtonGroupStyle":
        """Return a copy with the specified fields replaced."""
        return replace(self, **changes)

    # -- Factory classmethods -----------------------------------------------

    @classmethod
    def filled(cls, size: ButtonGroupSize = "s") -> "StandardButtonGroupStyle":
        """Create a filled-variant style.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).
        """
        t = _STANDARD_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.SURFACE_CONTAINER_HIGHEST,
            foreground=ColorRole.ON_SURFACE,
            border_width=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.08,
            selected_background=ColorRole.PRIMARY,
            selected_foreground=ColorRole.ON_PRIMARY,
            container_height=int(t["container_height"]),
            item_gap=int(t["item_gap"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def tonal(cls, size: ButtonGroupSize = "s") -> "StandardButtonGroupStyle":
        """Create a tonal-variant style.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).
        """
        t = _STANDARD_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.SECONDARY_CONTAINER,
            foreground=ColorRole.ON_SECONDARY_CONTAINER,
            border_width=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.08,
            selected_background=ColorRole.SECONDARY,
            selected_foreground=ColorRole.ON_SECONDARY,
            container_height=int(t["container_height"]),
            item_gap=int(t["item_gap"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def outlined(cls, size: ButtonGroupSize = "s") -> "StandardButtonGroupStyle":
        """Create an outlined-variant style.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).
        """
        t = _STANDARD_SIZE_TOKENS[size]
        return cls(
            background=None,
            foreground=ColorRole.ON_SURFACE,
            border_color=ColorRole.OUTLINE,
            border_width=1.0,
            overlay_color=ColorRole.PRIMARY,
            overlay_alpha=0.08,
            selected_background=ColorRole.INVERSE_SURFACE,
            selected_foreground=ColorRole.INVERSE_ON_SURFACE,
            container_height=int(t["container_height"]),
            item_gap=int(t["item_gap"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def from_theme(
        cls,
        theme: "Theme | None",
        variant: str,
        size: ButtonGroupSize = "s",
    ) -> "StandardButtonGroupStyle":
        """Create a style from a theme and variant name.

        Args:
            theme: The active theme (currently unused; colours are role-based).
            variant: One of ``"filled"``, ``"tonal"``, or ``"outlined"``.
            size: M3 size token preset.
        """
        if variant == "tonal":
            return cls.tonal(size)
        if variant == "outlined":
            return cls.outlined(size)
        return cls.filled(size)


# ===================================================================
# ConnectedButtonGroupStyle
# ===================================================================


@dataclass(frozen=True)
class ConnectedButtonGroupStyle:
    """Immutable style for ``ConnectedButtonGroup`` (M3-compliant).

    Segments are tightly connected with distinct junction corners.
    Supports selection-state colours and a separate
    ``selected_inner_corner_radius``.

    Use ``filled()``, ``tonal()``, or ``outlined()`` to create a preset,
    optionally passing a ``ButtonGroupSize``.
    """

    # Container colours
    background: Optional[ColorSpec] = None
    foreground: Optional[ColorSpec] = None
    border_color: Optional[ColorSpec] = None
    border_width: float = 0.0

    # Selection colours
    selected_background: Optional[ColorSpec] = None
    selected_foreground: Optional[ColorSpec] = None
    selected_border_color: Optional[ColorSpec] = None

    # Sizing
    container_height: int = 40
    item_gap: int = 2
    min_item_width: int = 48

    # Shape tokens (idle)
    outer_corner_radius: float = 20.0
    inner_corner_radius: float = 8.0

    # Shape tokens (pressed)
    pressed_outer_corner_radius: float = 8.0
    pressed_inner_corner_radius: float = 4.0

    # Shape tokens (selected)
    selected_inner_corner_radius: float = 0.0  # 0.0 = fully rounded (= outer)

    # State overlay
    overlay_color: Optional[ColorSpec] = None
    overlay_alpha: float = 0.12

    # -- Mutations ----------------------------------------------------------

    def copy_with(self, **changes: Any) -> "ConnectedButtonGroupStyle":
        """Return a copy with the specified fields replaced."""
        return replace(self, **changes)

    # -- Factory classmethods -----------------------------------------------

    @classmethod
    def filled(cls, size: ButtonGroupSize = "s") -> "ConnectedButtonGroupStyle":
        """Create a filled-variant style.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).
        """
        t = _CONNECTED_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.SURFACE_CONTAINER_HIGHEST,
            foreground=ColorRole.ON_SURFACE,
            border_width=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.08,
            selected_background=ColorRole.PRIMARY,
            selected_foreground=ColorRole.ON_PRIMARY,
            container_height=int(t["container_height"]),
            item_gap=int(t["item_gap"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            inner_corner_radius=float(t["inner_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def tonal(cls, size: ButtonGroupSize = "s") -> "ConnectedButtonGroupStyle":
        """Create a tonal-variant style.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).
        """
        t = _CONNECTED_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.SECONDARY_CONTAINER,
            foreground=ColorRole.ON_SECONDARY_CONTAINER,
            border_width=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.08,
            selected_background=ColorRole.SECONDARY,
            selected_foreground=ColorRole.ON_SECONDARY,
            container_height=int(t["container_height"]),
            item_gap=int(t["item_gap"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            inner_corner_radius=float(t["inner_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def outlined(cls, size: ButtonGroupSize = "s") -> "ConnectedButtonGroupStyle":
        """Create an outlined-variant style.

        Args:
            size: M3 size token preset (``"xs"``–``"xl"``).
        """
        t = _CONNECTED_SIZE_TOKENS[size]
        return cls(
            background=None,
            foreground=ColorRole.ON_SURFACE,
            border_color=ColorRole.OUTLINE,
            border_width=1.0,
            overlay_color=ColorRole.PRIMARY,
            overlay_alpha=0.08,
            selected_background=ColorRole.INVERSE_SURFACE,
            selected_foreground=ColorRole.INVERSE_ON_SURFACE,
            selected_border_color=ColorRole.OUTLINE,
            container_height=int(t["container_height"]),
            item_gap=int(t["item_gap"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            inner_corner_radius=float(t["inner_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def from_theme(
        cls,
        theme: "Theme | None",
        variant: str,
        size: ButtonGroupSize = "s",
    ) -> "ConnectedButtonGroupStyle":
        """Create a style from a theme and variant name.

        Args:
            theme: The active theme (currently unused; colours are role-based).
            variant: One of ``"filled"``, ``"tonal"``, or ``"outlined"``.
            size: M3 size token preset.
        """
        if variant == "tonal":
            return cls.tonal(size)
        if variant == "outlined":
            return cls.outlined(size)
        return cls.filled(size)


# ===================================================================
# Union type alias
# ===================================================================

ButtonGroupStyle = Union[StandardButtonGroupStyle, ConnectedButtonGroupStyle]
"""Type alias accepted by ``GroupButton`` — either style variant."""

__all__ = [
    "ButtonGroupSize",
    "StandardButtonGroupStyle",
    "ConnectedButtonGroupStyle",
    "ButtonGroupStyle",
]
