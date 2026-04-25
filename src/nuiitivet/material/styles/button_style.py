"""Canonical ButtonStyle definition for M3 buttons.

``ButtonStyle`` is used by the unified :class:`Button` widget (common style
for all visual variants).  Variant-specific styling is delivered through
size-aware factory methods: :meth:`ButtonStyle.filled`,
:meth:`ButtonStyle.outlined`, :meth:`ButtonStyle.text`,
:meth:`ButtonStyle.elevated`, and :meth:`ButtonStyle.tonal`.

The companion :class:`IconButtonStyle` / :class:`IconToggleButtonStyle`
presets share the same ``ButtonSize`` token set as Button, but pull
container / icon / spacing values from
:data:`ICON_BUTTON_SIZE_TOKENS`.  FAB styling lives in
:mod:`nuiitivet.material.styles.fab_style`.
"""

from dataclasses import dataclass, replace
from typing import Optional, Union, TYPE_CHECKING

from .button_size import (
    BUTTON_SIZE_TOKENS,
    ButtonSize,
    ICON_BUTTON_SIZE_TOKENS,
)
from ..theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

PaddingLike = Union[int, tuple[int, int, int, int]]

if TYPE_CHECKING:
    from ...theme import Theme


def _size_padding(size: ButtonSize) -> PaddingLike:
    """Return the (leading, 0, trailing, 0) padding for the given size."""
    tokens = BUTTON_SIZE_TOKENS[size]
    return (tokens["leading_space"], 0, tokens["trailing_space"], 0)


def _size_min_width(size: ButtonSize) -> int:
    """Return a reasonable ``min_width`` for the given size.

    For xs/s/m a 64-dp floor matches the historical touch-target; for l/xl
    the container_height already exceeds that, so we use it as the floor.
    """
    h = BUTTON_SIZE_TOKENS[size]["container_height"]
    return max(64, h)


def _size_min_height(size: ButtonSize) -> int:
    """Return the minimum touch-target height (>= 48 dp per MD3)."""
    return max(48, BUTTON_SIZE_TOKENS[size]["container_height"])


@dataclass(frozen=True)
class ButtonStyle:
    """Immutable style for the :class:`Button` widget (M3-compliant).

    Use the ``filled`` / ``outlined`` / ``text`` / ``elevated`` / ``tonal``
    factory classmethods (each accepting a :data:`ButtonSize`) rather than
    constructing directly where possible.
    """

    # Container properties
    background: Optional[ColorSpec] = None
    foreground: Optional[ColorSpec] = None
    border_color: Optional[ColorSpec] = None
    border_width: float = 0.0
    corner_radius: int = 20

    # Sizing
    container_height: int = 40
    padding: PaddingLike = (16, 0, 16, 0)
    spacing: int = 8
    min_width: int = 64
    min_height: int = 48
    label_font_size: int = 14
    icon_size: int = 20

    # Elevation (for elevated buttons / FAB)
    elevation: float = 0.0

    # State overlay (hover/press)
    overlay_color: Optional[ColorSpec] = None
    overlay_alpha: float = 0.0

    def copy_with(self, **changes) -> "ButtonStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict:
        """Resolve :class:`ColorRole` entries to concrete RGBA values."""
        from ...theme.resolver import resolve_color_to_rgba

        return {
            "background": resolve_color_to_rgba(self.background, theme=theme) if self.background else None,
            "foreground": resolve_color_to_rgba(self.foreground, theme=theme) if self.foreground else None,
            "border_color": resolve_color_to_rgba(self.border_color, theme=theme) if self.border_color else None,
            "overlay_color": resolve_color_to_rgba(self.overlay_color, theme=theme) if self.overlay_color else None,
        }

    def resolve(self, theme: "Theme | None" = None) -> dict:
        """Compatibility resolver returning a dict shaped like the legacy style."""
        colors = self.resolve_colors(theme=theme)
        resolved = {
            "background": colors.get("background"),
            "foreground": colors.get("foreground"),
            "border_color": colors.get("border_color"),
            "corner_radius": self.corner_radius,
            "padding": self.padding,
            "spacing": getattr(self, "spacing", 8),
            "min_size": (self.min_width, self.min_height),
            "text_style": None,
        }

        if self.overlay_color is not None:
            try:
                resolved["overlay"] = (self.overlay_color, float(self.overlay_alpha or 0.0))
            except Exception:
                resolved["overlay"] = None
        else:
            resolved["overlay"] = None

        return resolved

    # -- Factory classmethods (size-aware) ----------------------------------

    @classmethod
    def filled(cls, size: ButtonSize = "s") -> "ButtonStyle":
        """Return the filled-variant style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.PRIMARY,
            foreground=ColorRole.ON_PRIMARY,
            border_width=0.0,
            corner_radius=t["corner_radius"],
            container_height=t["container_height"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=_size_min_width(size),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            elevation=0.0,
            overlay_color=ColorRole.ON_PRIMARY,
            overlay_alpha=0.08,
        )

    @classmethod
    def outlined(cls, size: ButtonSize = "s") -> "ButtonStyle":
        """Return the outlined-variant style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            background=None,
            foreground=ColorRole.ON_SURFACE_VARIANT,
            border_color=ColorRole.OUTLINE_VARIANT,
            border_width=t["outline_width"],
            corner_radius=t["corner_radius"],
            container_height=t["container_height"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=_size_min_width(size),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            elevation=0.0,
            overlay_color=ColorRole.ON_SURFACE_VARIANT,
            overlay_alpha=0.08,
        )

    @classmethod
    def text(cls, size: ButtonSize = "s") -> "ButtonStyle":
        """Return the text-variant style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            background=None,
            foreground=ColorRole.PRIMARY,
            border_width=0.0,
            corner_radius=t["corner_radius"],
            container_height=t["container_height"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=max(48, t["container_height"]),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            elevation=0.0,
            overlay_color=ColorRole.PRIMARY,
            overlay_alpha=0.08,
        )

    @classmethod
    def elevated(cls, size: ButtonSize = "s") -> "ButtonStyle":
        """Return the elevated-variant style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.SURFACE_CONTAINER_LOW,
            foreground=ColorRole.PRIMARY,
            border_width=0.0,
            corner_radius=t["corner_radius"],
            container_height=t["container_height"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=_size_min_width(size),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            elevation=1.0,
            overlay_color=ColorRole.PRIMARY,
            overlay_alpha=0.08,
        )

    @classmethod
    def tonal(cls, size: ButtonSize = "s") -> "ButtonStyle":
        """Return the tonal-variant style at the given M3 size."""
        t = BUTTON_SIZE_TOKENS[size]
        return cls(
            background=ColorRole.SECONDARY_CONTAINER,
            foreground=ColorRole.ON_SECONDARY_CONTAINER,
            border_width=0.0,
            corner_radius=t["corner_radius"],
            container_height=t["container_height"],
            padding=_size_padding(size),
            spacing=t["icon_label_space"],
            min_width=_size_min_width(size),
            min_height=_size_min_height(size),
            label_font_size=t["label_font_size"],
            icon_size=t["icon_size"],
            elevation=0.0,
            overlay_color=ColorRole.ON_SECONDARY_CONTAINER,
            overlay_alpha=0.08,
        )


class IconButtonStyle:
    """Preset factories for icon-only button styles.

    Each factory accepts a :data:`ButtonSize` argument that drives container
    size, icon size, corner radius, and outline width from
    :data:`ICON_BUTTON_SIZE_TOKENS`.  Defaults to ``"s"`` (40dp).
    """

    @staticmethod
    def _base(size: ButtonSize) -> dict:
        """Return common size-driven keyword arguments for IconButton styles."""
        t = ICON_BUTTON_SIZE_TOKENS[size]
        h = t["container_height"]
        return dict(
            corner_radius=t["corner_radius"],
            container_height=h,
            padding=0,
            min_width=max(48, h),
            min_height=max(48, h),
            icon_size=t["icon_size"],
        )

    @classmethod
    def standard(cls, size: ButtonSize = "s") -> ButtonStyle:
        """Return the standard icon-button style at the given M3 size."""
        return ButtonStyle(
            background=None,
            foreground=ColorRole.ON_SURFACE_VARIANT,
            border_width=0.0,
            elevation=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.12,
            **cls._base(size),
        )

    @classmethod
    def filled(cls, size: ButtonSize = "s") -> ButtonStyle:
        """Return the filled icon-button style at the given M3 size."""
        return ButtonStyle(
            background=ColorRole.PRIMARY,
            foreground=ColorRole.ON_PRIMARY,
            border_width=0.0,
            elevation=0.0,
            overlay_color=ColorRole.ON_PRIMARY,
            overlay_alpha=0.12,
            **cls._base(size),
        )

    @classmethod
    def outlined(cls, size: ButtonSize = "s") -> ButtonStyle:
        """Return the outlined icon-button style at the given M3 size."""
        t = ICON_BUTTON_SIZE_TOKENS[size]
        return ButtonStyle(
            background=None,
            foreground=ColorRole.ON_SURFACE_VARIANT,
            border_color=ColorRole.OUTLINE,
            border_width=t["outline_width"],
            elevation=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.12,
            **cls._base(size),
        )

    @classmethod
    def tonal(cls, size: ButtonSize = "s") -> ButtonStyle:
        """Return the tonal icon-button style at the given M3 size."""
        return ButtonStyle(
            background=ColorRole.SECONDARY_CONTAINER,
            foreground=ColorRole.ON_SECONDARY_CONTAINER,
            border_width=0.0,
            elevation=0.0,
            overlay_color=ColorRole.ON_SECONDARY_CONTAINER,
            overlay_alpha=0.12,
            **cls._base(size),
        )

    @classmethod
    def vibrant(cls, size: ButtonSize = "s") -> ButtonStyle:
        """Return the vibrant icon-button style at the given M3 size.

        Intended for use on vibrant containers such as a vibrant toolbar.
        """
        return ButtonStyle(
            background=None,
            foreground=ColorRole.ON_PRIMARY_CONTAINER,
            border_width=0.0,
            elevation=0.0,
            overlay_color=ColorRole.ON_PRIMARY_CONTAINER,
            overlay_alpha=0.12,
            **cls._base(size),
        )

    @classmethod
    def filled_vibrant(cls, size: ButtonSize = "s") -> ButtonStyle:
        """Return the filled vibrant icon-button style at the given M3 size."""
        return ButtonStyle(
            background=ColorRole.PRIMARY,
            foreground=ColorRole.ON_PRIMARY,
            border_width=0.0,
            elevation=0.0,
            overlay_color=ColorRole.ON_PRIMARY,
            overlay_alpha=0.12,
            **cls._base(size),
        )

    @classmethod
    def outlined_vibrant(cls, size: ButtonSize = "s") -> ButtonStyle:
        """Return the outlined vibrant icon-button style at the given M3 size."""
        t = ICON_BUTTON_SIZE_TOKENS[size]
        return ButtonStyle(
            background=None,
            foreground=ColorRole.ON_PRIMARY_CONTAINER,
            border_color=ColorRole.ON_PRIMARY_CONTAINER,
            border_width=t["outline_width"],
            elevation=0.0,
            overlay_color=ColorRole.ON_PRIMARY_CONTAINER,
            overlay_alpha=0.12,
            **cls._base(size),
        )

    @classmethod
    def tonal_vibrant(cls, size: ButtonSize = "s") -> ButtonStyle:
        """Return the tonal vibrant icon-button style at the given M3 size."""
        return ButtonStyle(
            background=ColorRole.SURFACE_CONTAINER_HIGHEST,
            foreground=ColorRole.ON_SURFACE,
            border_width=0.0,
            elevation=0.0,
            overlay_color=ColorRole.ON_SURFACE,
            overlay_alpha=0.12,
            **cls._base(size),
        )


@dataclass(frozen=True)
class IconToggleButtonStyle:
    """State-paired style for icon toggle button widgets."""

    selected: ButtonStyle
    unselected: ButtonStyle

    @classmethod
    def standard(cls, size: ButtonSize = "s") -> "IconToggleButtonStyle":
        """Return styles for the standard icon-toggle button variant."""
        base = IconButtonStyle._base(size)
        return cls(
            selected=ButtonStyle(
                background=ColorRole.SECONDARY_CONTAINER,
                foreground=ColorRole.ON_SECONDARY_CONTAINER,
                border_width=0.0,
                elevation=0.0,
                overlay_color=ColorRole.ON_SECONDARY_CONTAINER,
                overlay_alpha=0.12,
                **base,
            ),
            unselected=IconButtonStyle.standard(size),
        )

    @classmethod
    def filled(cls, size: ButtonSize = "s") -> "IconToggleButtonStyle":
        """Return styles for the filled icon-toggle button variant."""
        base = IconButtonStyle._base(size)
        return cls(
            selected=IconButtonStyle.filled(size),
            unselected=ButtonStyle(
                background=ColorRole.SURFACE_CONTAINER_HIGHEST,
                foreground=ColorRole.ON_SURFACE_VARIANT,
                border_width=0.0,
                elevation=0.0,
                overlay_color=ColorRole.ON_SURFACE,
                overlay_alpha=0.12,
                **base,
            ),
        )

    @classmethod
    def outlined(cls, size: ButtonSize = "s") -> "IconToggleButtonStyle":
        """Return styles for the outlined icon-toggle button variant."""
        t = ICON_BUTTON_SIZE_TOKENS[size]
        base = IconButtonStyle._base(size)
        return cls(
            selected=ButtonStyle(
                background=ColorRole.INVERSE_SURFACE,
                foreground=ColorRole.INVERSE_ON_SURFACE,
                border_color=ColorRole.INVERSE_SURFACE,
                border_width=t["outline_width"],
                elevation=0.0,
                overlay_color=ColorRole.INVERSE_ON_SURFACE,
                overlay_alpha=0.12,
                **base,
            ),
            unselected=IconButtonStyle.outlined(size),
        )

    @classmethod
    def tonal(cls, size: ButtonSize = "s") -> "IconToggleButtonStyle":
        """Return styles for the tonal icon-toggle button variant."""
        base = IconButtonStyle._base(size)
        return cls(
            selected=ButtonStyle(
                background=ColorRole.TERTIARY_CONTAINER,
                foreground=ColorRole.ON_TERTIARY_CONTAINER,
                border_width=0.0,
                elevation=0.0,
                overlay_color=ColorRole.ON_TERTIARY_CONTAINER,
                overlay_alpha=0.12,
                **base,
            ),
            unselected=ButtonStyle(
                background=ColorRole.SECONDARY_CONTAINER,
                foreground=ColorRole.ON_SECONDARY_CONTAINER,
                border_width=0.0,
                elevation=0.0,
                overlay_color=ColorRole.ON_SECONDARY_CONTAINER,
                overlay_alpha=0.12,
                **base,
            ),
        )


__all__ = ["ButtonStyle", "IconButtonStyle", "IconToggleButtonStyle"]
