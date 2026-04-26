"""Material Design 3 badge widgets."""

from __future__ import annotations

from typing import Optional, Tuple, Union

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
    """Large text badge widget."""

    def __init__(
        self,
        text: str,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int], None] = None,
        style: Optional[LargeBadgeStyle] = None,
    ) -> None:
        """Initialize LargeBadge.

        Args:
            text: Badge text to display. Must be non-empty.
            width: Badge width sizing.
            height: Badge height sizing. Defaults to style height.
            padding: External badge padding. Defaults to style padding.
            style: Optional style override.
        """
        if not text:
            raise ValueError("text must be non-empty")

        self.text = text

        effective_style = style or LargeBadgeStyle()
        resolved_height = height if height is not None else Sizing.fixed(effective_style.height)
        resolved_padding = effective_style.padding if padding is None else padding

        label = Text(
            text,
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
