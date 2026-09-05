"""ButtonGroup style definitions for M3 button groups.

Provides two concrete style classes:

- ``StandardButtonGroupStyle``: For action-oriented groups with independent
  fully-rounded pill segments.
- ``ConnectedButtonGroupStyle``: For option-selector / view-switcher groups
  with junction corners and selection state colours.

Each style offers ``filled()``, ``tonal()``, and ``outlined()`` factory
classmethods that accept a :data:`ButtonSize` to set M3-spec size tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Optional, TYPE_CHECKING, Union

from nuiitivet.animation.motion import Motion
from nuiitivet.material.motion import SPRING_STANDARD_FAST_SPATIAL
from nuiitivet.material.styles.button_size import ButtonSize
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme import Theme

# Pressed item width spring.
STANDARD_BUTTON_GROUP_WIDTH: Motion = SPRING_STANDARD_FAST_SPATIAL

# ---------------------------------------------------------------------------
# Size token tables (M3 spec)
# ---------------------------------------------------------------------------

_STANDARD_SIZE_TOKENS: dict[str, dict[str, int | float]] = {
    "xs": {
        "container_height": 32,
        "item_gap": 18,
        "inner_padding": 12,
        "icon_size": 20,
        "label_size": 14,
        "icon_label_space": 8,
        "outer_corner_radius": 16.0,
        "pressed_corner_radius": 12.0,
    },
    "s": {
        "container_height": 40,
        "item_gap": 12,
        "inner_padding": 16,
        "icon_size": 20,
        "label_size": 14,
        "icon_label_space": 8,
        "outer_corner_radius": 20.0,
        "pressed_corner_radius": 12.0,
    },
    "m": {
        "container_height": 56,
        "item_gap": 8,
        "inner_padding": 24,
        "icon_size": 24,
        "label_size": 16,
        "icon_label_space": 8,
        "outer_corner_radius": 28.0,
        "pressed_corner_radius": 16.0,
    },
    "l": {
        "container_height": 96,
        "item_gap": 8,
        "inner_padding": 48,
        "icon_size": 32,
        "label_size": 24,
        "icon_label_space": 12,
        "outer_corner_radius": 48.0,
        "pressed_corner_radius": 28.0,
    },
    "xl": {
        "container_height": 136,
        "item_gap": 8,
        "inner_padding": 64,
        "icon_size": 40,
        "label_size": 32,
        "icon_label_space": 16,
        "outer_corner_radius": 68.0,
        "pressed_corner_radius": 28.0,
    },
}

_CONNECTED_SIZE_TOKENS: dict[str, dict[str, int | float]] = {
    "xs": {
        "container_height": 32,
        "item_gap": 2,
        "icon_size": 20,
        "label_size": 14,
        "icon_label_space": 8,
        "outer_corner_radius": 16.0,
        "inner_corner_radius": 8.0,
        "pressed_inner_corner_radius": 4.0,
    },
    "s": {
        "container_height": 40,
        "item_gap": 2,
        "icon_size": 20,
        "label_size": 14,
        "icon_label_space": 8,
        "outer_corner_radius": 20.0,
        "inner_corner_radius": 8.0,
        "pressed_inner_corner_radius": 4.0,
    },
    "m": {
        "container_height": 56,
        "item_gap": 2,
        "icon_size": 24,
        "label_size": 16,
        "icon_label_space": 8,
        "outer_corner_radius": 28.0,
        "inner_corner_radius": 8.0,
        "pressed_inner_corner_radius": 4.0,
    },
    "l": {
        "container_height": 96,
        "item_gap": 2,
        "icon_size": 32,
        "label_size": 24,
        "icon_label_space": 12,
        "outer_corner_radius": 48.0,
        "inner_corner_radius": 16.0,
        "pressed_inner_corner_radius": 12.0,
    },
    "xl": {
        "container_height": 136,
        "item_gap": 2,
        "icon_size": 40,
        "label_size": 32,
        "icon_label_space": 16,
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
    optionally passing a ``ButtonSize``.
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
    item_gap: int = 12  # between-space: gap between adjacent segments
    min_item_width: int = 48
    # Per-segment horizontal padding.  Sourced from the MD3 *button*
    # leading-space / trailing-space tokens (xs=12, s=16, m=24, l=48, xl=64),
    # NOT the group between-space — each segment is a button and keeps the
    # button's own side padding.
    inner_padding: int = 16

    # Content metrics (scale with size, sourced from the MD3 button tokens)
    icon_size: int = 20
    label_size: int = 14
    icon_label_space: int = 8

    # Shape tokens.  The pressed/selected "squared" shape is the MD3 button
    # square shape (== "selected container shape round"): xs/s=12, m=16, l/xl=28.
    # Standard pills are uniform, so outer and inner share this value; a selected
    # segment keeps the same shape as a pressed one (matching the MD3 demo).
    outer_corner_radius: float = 20.0
    pressed_outer_corner_radius: float = 12.0
    pressed_inner_corner_radius: float = 12.0

    # Adjacent-interaction motion (M3): while an item is *pressed* it grows by
    # this fraction of its natural width and its direct neighbors shrink to
    # compensate; on release the width returns to idle (selection is shown by
    # colour/shape, not width).  Spec value: 15% for all sizes.
    pressed_width_multiplier: float = 0.15

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
    def filled(cls, size: ButtonSize = "s") -> "StandardButtonGroupStyle":
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
            icon_size=int(t["icon_size"]),
            label_size=int(t["label_size"]),
            icon_label_space=int(t["icon_label_space"]),
            inner_padding=int(t["inner_padding"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            pressed_outer_corner_radius=float(t["pressed_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_corner_radius"]),
        )

    @classmethod
    def tonal(cls, size: ButtonSize = "s") -> "StandardButtonGroupStyle":
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
            icon_size=int(t["icon_size"]),
            label_size=int(t["label_size"]),
            icon_label_space=int(t["icon_label_space"]),
            inner_padding=int(t["inner_padding"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            pressed_outer_corner_radius=float(t["pressed_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_corner_radius"]),
        )

    @classmethod
    def outlined(cls, size: ButtonSize = "s") -> "StandardButtonGroupStyle":
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
            icon_size=int(t["icon_size"]),
            label_size=int(t["label_size"]),
            icon_label_space=int(t["icon_label_space"]),
            inner_padding=int(t["inner_padding"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            pressed_outer_corner_radius=float(t["pressed_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_corner_radius"]),
        )

    @classmethod
    def preset(cls) -> "StandardButtonGroupStyle":
        """Return the framework preset, ignoring any theme.

        This is what a standard button group renders with before it is
        mounted, and what :meth:`from_theme` falls back to when no Material
        theme is installed.

        Returns:
            The filled standard-group style at size ``"s"``.
        """
        return cls.filled("s")

    @classmethod
    def from_theme(cls, theme: "Theme | None") -> "StandardButtonGroupStyle":
        """Resolve the standard button group style from ``theme``.

        Args:
            theme: The active theme, or ``None`` when there is none.

        Returns:
            Resolved standard-group style.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        if theme is not None:
            theme_data = theme.extension(MaterialThemeData)
            if theme_data is not None:
                return theme_data.standard_button_group_style
        return cls.preset()


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
    optionally passing a ``ButtonSize``.
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

    # Content metrics (scale with size, sourced from the MD3 button tokens)
    icon_size: int = 20
    label_size: int = 14
    icon_label_space: int = 8

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
    def filled(cls, size: ButtonSize = "s") -> "ConnectedButtonGroupStyle":
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
            icon_size=int(t["icon_size"]),
            label_size=int(t["label_size"]),
            icon_label_space=int(t["icon_label_space"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            inner_corner_radius=float(t["inner_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def tonal(cls, size: ButtonSize = "s") -> "ConnectedButtonGroupStyle":
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
            icon_size=int(t["icon_size"]),
            label_size=int(t["label_size"]),
            icon_label_space=int(t["icon_label_space"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            inner_corner_radius=float(t["inner_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def outlined(cls, size: ButtonSize = "s") -> "ConnectedButtonGroupStyle":
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
            icon_size=int(t["icon_size"]),
            label_size=int(t["label_size"]),
            icon_label_space=int(t["icon_label_space"]),
            outer_corner_radius=float(t["outer_corner_radius"]),
            inner_corner_radius=float(t["inner_corner_radius"]),
            pressed_inner_corner_radius=float(t["pressed_inner_corner_radius"]),
        )

    @classmethod
    def preset(cls) -> "ConnectedButtonGroupStyle":
        """Return the framework preset, ignoring any theme.

        This is what a connected button group renders with before it is
        mounted, and what :meth:`from_theme` falls back to when no Material
        theme is installed.

        Returns:
            The filled connected-group style at size ``"s"``.
        """
        return cls.filled("s")

    @classmethod
    def from_theme(cls, theme: "Theme | None") -> "ConnectedButtonGroupStyle":
        """Resolve the connected button group style from ``theme``.

        Args:
            theme: The active theme, or ``None`` when there is none.

        Returns:
            Resolved connected-group style.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        if theme is not None:
            theme_data = theme.extension(MaterialThemeData)
            if theme_data is not None:
                return theme_data.connected_button_group_style
        return cls.preset()


# ===================================================================
# Union type alias
# ===================================================================

ButtonGroupStyle = Union[StandardButtonGroupStyle, ConnectedButtonGroupStyle]
"""Type alias accepted by ``GroupButton`` — either style variant."""

__all__ = [
    "ButtonSize",
    "STANDARD_BUTTON_GROUP_WIDTH",
    "StandardButtonGroupStyle",
    "ConnectedButtonGroupStyle",
    "ButtonGroupStyle",
]
