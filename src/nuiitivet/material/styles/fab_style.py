"""Style preset for the Material Design 3 :class:`Fab` widget.

``FabStyle`` is a thin :class:`ButtonStyle` subclass that exposes the six
active color mappings defined by the current MD3 spec -- three *tonal*
container variants and three *solid* variants:

- :meth:`FabStyle.primary` -- ``primary container`` / ``on primary container``
- :meth:`FabStyle.secondary` -- ``secondary container`` / ``on secondary container``
- :meth:`FabStyle.tertiary` -- ``tertiary container`` / ``on tertiary container``
- :meth:`FabStyle.primary_solid` -- ``primary`` / ``on primary``
- :meth:`FabStyle.secondary_solid` -- ``secondary`` / ``on secondary``
- :meth:`FabStyle.tertiary_solid` -- ``tertiary`` / ``on tertiary``

Each factory accepts a :data:`FabSize` (``"s"`` / ``"m"`` / ``"l"``) that
selects container / icon / corner-radius tokens from
:data:`FAB_SIZE_TOKENS`.  The default size is ``"s"`` (the 56dp baseline FAB).
"""

from dataclasses import dataclass

from .button_size import FAB_SIZE_TOKENS, FabSize
from .button_style import ButtonStyle
from ..theme.color_role import ColorRole


@dataclass(frozen=True)
class FabStyle(ButtonStyle):
    """Style preset used by the :class:`Fab` widget.

    Inherits the field set of :class:`ButtonStyle` so that ``Fab`` can reuse
    the shared ``resolve_button_style_params`` machinery without changes.
    """

    focus_opacity: float = 0.1
    hover_opacity: float = 0.08
    pressed_opacity: float = 0.1
    focused_elevation: int = 3
    hovered_elevation: int = 4
    pressed_elevation: int = 3

    @staticmethod
    def _base(size: FabSize) -> dict:
        t = FAB_SIZE_TOKENS[size]
        return dict(
            border_width=0.0,
            corner_radius=t["corner_radius"],
            padding=(8, 8, 8, 8),
            container_height=t["container_height"],
            min_width=t["container_width"],
            min_height=t["container_height"],
            label_font_size=14,
            icon_size=t["icon_size"],
            elevation=3,
            overlay_alpha=0.08,
            focus_opacity=0.1,
            hover_opacity=0.08,
            pressed_opacity=0.1,
            focused_elevation=3,
            hovered_elevation=4,
            pressed_elevation=3,
        )

    @classmethod
    def primary(cls, size: FabSize = "s") -> "FabStyle":
        """Return the tonal-primary FAB style at the given size."""
        return cls(
            background=ColorRole.PRIMARY_CONTAINER,
            foreground=ColorRole.ON_PRIMARY_CONTAINER,
            overlay_color=ColorRole.ON_PRIMARY_CONTAINER,
            **cls._base(size),
        )

    @classmethod
    def secondary(cls, size: FabSize = "s") -> "FabStyle":
        """Return the tonal-secondary FAB style at the given size."""
        return cls(
            background=ColorRole.SECONDARY_CONTAINER,
            foreground=ColorRole.ON_SECONDARY_CONTAINER,
            overlay_color=ColorRole.ON_SECONDARY_CONTAINER,
            **cls._base(size),
        )

    @classmethod
    def tertiary(cls, size: FabSize = "s") -> "FabStyle":
        """Return the tonal-tertiary FAB style at the given size."""
        return cls(
            background=ColorRole.TERTIARY_CONTAINER,
            foreground=ColorRole.ON_TERTIARY_CONTAINER,
            overlay_color=ColorRole.ON_TERTIARY_CONTAINER,
            **cls._base(size),
        )

    @classmethod
    def primary_solid(cls, size: FabSize = "s") -> "FabStyle":
        """Return the solid-primary FAB style at the given size."""
        return cls(
            background=ColorRole.PRIMARY,
            foreground=ColorRole.ON_PRIMARY,
            overlay_color=ColorRole.ON_PRIMARY,
            **cls._base(size),
        )

    @classmethod
    def secondary_solid(cls, size: FabSize = "s") -> "FabStyle":
        """Return the solid-secondary FAB style at the given size."""
        return cls(
            background=ColorRole.SECONDARY,
            foreground=ColorRole.ON_SECONDARY,
            overlay_color=ColorRole.ON_SECONDARY,
            **cls._base(size),
        )

    @classmethod
    def tertiary_solid(cls, size: FabSize = "s") -> "FabStyle":
        """Return the solid-tertiary FAB style at the given size."""
        return cls(
            background=ColorRole.TERTIARY,
            foreground=ColorRole.ON_TERTIARY,
            overlay_color=ColorRole.ON_TERTIARY,
            **cls._base(size),
        )


__all__ = ["FabStyle"]
