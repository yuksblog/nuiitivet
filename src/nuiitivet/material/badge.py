"""Material Design 3 badge widgets."""

from __future__ import annotations

from typing import Optional, Tuple, Union

from nuiitivet.material.styles.badge_style import LargeBadgeStyle, SmallBadgeStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.text import Text
from nuiitivet.modifiers.stick import StickModifier, stick
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.box import Box


class SmallBadge(Box):
    """Small dot badge widget."""

    def __init__(
        self,
        *,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional[SmallBadgeStyle] = None,
    ) -> None:
        """Initialize SmallBadge.

        The dot dimensions are MD3-fixed (spec size tokens), so they are not
        constructor parameters; customize them via ``style`` instead
        (SIZE_POLICY: MD3 fixes the axis -> style only).

        Args:
            padding: External badge padding.
            style: Optional style override.
        """
        effective_style = style or SmallBadgeStyle()

        super().__init__(
            child=None,
            width=Sizing.fixed(effective_style.width),
            height=Sizing.fixed(effective_style.height),
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
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int], None] = None,
        style: Optional[LargeBadgeStyle] = None,
    ) -> None:
        """Initialize LargeBadge.

        The height is MD3-fixed (spec) and the width is content-driven, so
        neither is a constructor parameter; customize the height via ``style``
        (SIZE_POLICY: MD3 fixes the axis -> style only).

        Args:
            text: Badge text to display. Must be non-empty.
            padding: External badge padding. Defaults to style padding.
            style: Optional style override.
        """
        if not text:
            raise ValueError("text must be non-empty")

        self.text = text

        effective_style = style or LargeBadgeStyle()
        resolved_height = Sizing.fixed(effective_style.height)
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
