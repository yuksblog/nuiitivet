"""Material Design 3 badge widgets and value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal, Optional, Tuple, Union

from nuiitivet.material.styles.badge_style import LargeBadgeStyle, SmallBadgeStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.text import Text
from nuiitivet.modifiers.stick import StickModifier, stick
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box


class SmallBadge(Box):
    """Small dot badge widget."""

    def __init__(
        self,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional[SmallBadgeStyle] = None,
    ) -> None:
        """Initialize SmallBadge.

        Args:
            width: Badge width sizing. Defaults to style width.
            height: Badge height sizing. Defaults to style height.
            padding: External badge padding.
            style: Optional style override.
        """
        effective_style = style or SmallBadgeStyle()
        resolved_width = width if width is not None else Sizing.fixed(effective_style.width)
        resolved_height = height if height is not None else Sizing.fixed(effective_style.height)

        super().__init__(
            child=None,
            width=resolved_width,
            height=resolved_height,
            padding=padding,
            background_color=effective_style.background_color,
            corner_radius=effective_style.corner_radius,
        )

    def stick_modifier(self, *, badge: Optional[Widget] = None) -> StickModifier:
        """Create a spec-aligned stick modifier for attaching this small badge.

        Args:
            badge: Optional badge widget to place. Defaults to this badge instance.

        Returns:
            Stick modifier configured for MD3-like small badge placement.
        """
        target_badge = badge if badge is not None else self
        return stick(
            target_badge,
            alignment="top-right",
            anchor="bottom-left",
            offset=(-6.0, 6.0),
        )


class LargeBadge(Box):
    """Large text/count badge widget."""

    def __init__(
        self,
        count: int,
        *,
        max: int = 999,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int], None] = None,
        style: Optional[LargeBadgeStyle] = None,
    ) -> None:
        """Initialize LargeBadge.

        Args:
            count: Badge count. Must be >= 1.
            max: Overflow threshold. When count > max, shows ``"{max}+"``.
            width: Badge width sizing.
            height: Badge height sizing. Defaults to style height.
            padding: External badge padding. Defaults to style padding.
            style: Optional style override.
        """
        if int(count) < 1:
            raise ValueError("count must be >= 1")
        if int(max) < 1:
            raise ValueError("max must be >= 1")

        self.count = int(count)
        self.max = int(max)

        effective_style = style or LargeBadgeStyle()
        resolved_height = height if height is not None else Sizing.fixed(effective_style.height)
        resolved_padding = effective_style.padding if padding is None else padding

        label = Text(
            self.format_count(self.count, self.max),
            style=TextStyle(
                color=effective_style.content_color,
                font_size=effective_style.font_size,
                text_alignment="center",
                overflow="clip",
            ),
        )

        super().__init__(
            child=label,
            width=width,
            height=resolved_height,
            padding=resolved_padding,
            background_color=effective_style.background_color,
            corner_radius=effective_style.corner_radius,
            alignment="center",
        )

    def stick_modifier(self, *, badge: Optional[Widget] = None) -> StickModifier:
        """Create a spec-aligned stick modifier for attaching this large badge.

        Args:
            badge: Optional badge widget to place. Defaults to this badge instance.

        Returns:
            Stick modifier configured for MD3-like large badge placement.
        """
        target_badge = badge if badge is not None else self
        return stick(
            target_badge,
            alignment="top-right",
            anchor="bottom-left",
            offset=(-12.0, 14.0),
        )

    @staticmethod
    def format_count(count: int, max_value: int) -> str:
        """Format badge count with overflow cap.

        Args:
            count: Raw count value.
            max_value: Overflow threshold.

        Returns:
            Formatted count string.
        """
        return f"{max_value}+" if int(count) > int(max_value) else str(int(count))


@dataclass(frozen=True, slots=True)
class BadgeValue:
    """Value object representing badge state for declarative APIs."""

    kind: Literal["none", "small", "large"]
    count: Optional[int] = None
    max: int = 999
    NONE: ClassVar["BadgeValue"]

    @classmethod
    def none(cls) -> "BadgeValue":
        """Create the hidden badge state."""
        return cls(kind="none")

    @classmethod
    def small(cls) -> "BadgeValue":
        """Create the small dot badge state."""
        return cls(kind="small")

    @classmethod
    def large(cls, count: int, *, max: int = 999) -> "BadgeValue":
        """Create the large count badge state.

        Args:
            count: Badge count. Must be >= 1.
            max: Overflow threshold. Must be >= 1.
        """
        if int(count) < 1:
            raise ValueError("count must be >= 1")
        if int(max) < 1:
            raise ValueError("max must be >= 1")
        return cls(kind="large", count=int(count), max=int(max))

    def to_widget(self) -> Optional[Widget]:
        """Create a concrete badge widget from this value.

        Returns:
            Badge widget instance, or None when kind is ``none``.
        """
        if self.kind == "none":
            return None
        if self.kind == "small":
            return SmallBadge()
        if self.count is None:
            raise ValueError("large badge requires count")
        return LargeBadge(self.count, max=self.max)


BadgeValue.NONE = BadgeValue.none()
