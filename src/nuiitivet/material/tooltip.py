"""Material Design 3 tooltip widgets."""

from __future__ import annotations

from typing import Callable

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.layout.row import Row
from nuiitivet.material.buttons import Button
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.styles.tooltip_style import RichTooltipStyle, TooltipStyle
from nuiitivet.material.text import Text
from nuiitivet.rendering.elevation import resolve_shadow_params
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.theme.manager import manager
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box


def _resolve_shadow(elevation: float, color_spec):
    if elevation <= 0.0:
        return None, (0.0, 0.0), 0.0
    resolved = resolve_shadow_params(float(elevation))
    return color_spec, resolved.offset, resolved.blur


class Tooltip(ComposableWidget):
    """Material Design 3 plain tooltip widget."""

    def __init__(
        self,
        message: str,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        style: TooltipStyle | None = None,
    ) -> None:
        """Initialize Tooltip.

        Args:
            message: Short plain-text tooltip message.
            width: Optional width sizing.
            height: Optional height sizing.
            style: Optional style token set. Defaults to TooltipStyle.standard().
        """
        super().__init__(width=width, height=height)
        self.message = str(message)
        self._user_style = style

    @property
    def style(self) -> TooltipStyle:
        """Return tooltip style resolved from user style or current theme."""
        if self._user_style is not None:
            return self._user_style
        return TooltipStyle.from_theme(manager.current)

    def build(self) -> Widget:
        style = self.style
        shadow_color, shadow_offset, shadow_blur = _resolve_shadow(style.elevation, style.elevation_color)
        label = Text(
            self.message,
            style=TextStyle(
                font_size=style.text_size,
                color=style.content_color,
                overflow="ellipsis",
            ),
        )
        content_height = self.height_sizing if self.height_sizing.kind == "fixed" else style.min_height
        return Box(
            child=Container(
                child=label,
                height=content_height,
                alignment="center-left",
            ),
            width=self.width_sizing,
            height=self.height_sizing,
            padding=(
                style.horizontal_padding,
                style.vertical_padding,
                style.horizontal_padding,
                style.vertical_padding,
            ),
            background_color=style.container_color,
            corner_radius=style.corner_radius,
            shadow_color=shadow_color,
            shadow_offset=shadow_offset,
            shadow_blur=shadow_blur,
        )


class RichTooltip(ComposableWidget):
    """Material Design 3 rich tooltip widget."""

    def __init__(
        self,
        supporting_text: str,
        *,
        subhead: str | None = None,
        action_label: str | None = None,
        on_action_click: Callable[[], None] | None = None,
        action_label_2: str | None = None,
        on_action_click_2: Callable[[], None] | None = None,
        width: SizingLike = None,
        height: SizingLike = None,
        style: RichTooltipStyle | None = None,
    ) -> None:
        """Initialize RichTooltip.

        Args:
            supporting_text: Main explanatory text.
            subhead: Optional short title line.
            action_label: Optional primary text button label.
            on_action_click: Optional callback for primary action.
            action_label_2: Optional secondary text button label.
            on_action_click_2: Optional callback for secondary action.
            width: Optional width sizing.
            height: Optional height sizing.
            style: Optional style token set. Defaults to RichTooltipStyle.standard().
        """
        super().__init__(width=width, height=height)
        self.supporting_text = str(supporting_text)
        self.subhead = subhead
        self.action_label = action_label
        self.on_action_click = on_action_click
        self.action_label_2 = action_label_2
        self.on_action_click_2 = on_action_click_2
        self._user_style = style

    @property
    def style(self) -> RichTooltipStyle:
        """Return rich tooltip style resolved from user style or current theme."""
        if self._user_style is not None:
            return self._user_style
        return RichTooltipStyle.from_theme(manager.current)

    def build(self) -> Widget:
        style = self.style
        shadow_color, shadow_offset, shadow_blur = _resolve_shadow(style.elevation, style.elevation_color)

        children: list[Widget] = []
        if self.subhead is not None:
            children.append(
                Text(
                    self.subhead,
                    style=TextStyle(
                        font_size=style.subhead_text_size,
                        color=style.subhead_color,
                    ),
                )
            )

        children.append(
            Text(
                self.supporting_text,
                style=TextStyle(
                    font_size=style.supporting_text_size,
                    color=style.supporting_text_color,
                ),
            )
        )

        action_style = ButtonStyle.text().copy_with(
            foreground=style.action_color,
            overlay_color=style.action_color,
            container_height=32,
            min_width=0,
            min_height=32,
            padding=(8, 0, 8, 0),
        )
        action_buttons: list[Widget] = []
        if self.action_label is not None:
            action_buttons.append(Button(self.action_label, on_click=self.on_action_click, style=action_style))
        if self.action_label_2 is not None:
            action_buttons.append(Button(self.action_label_2, on_click=self.on_action_click_2, style=action_style))
        if action_buttons:
            children.append(
                Container(
                    child=Row(
                        action_buttons,
                        gap=8,
                        main_alignment="end",
                        cross_alignment="center",
                    ),
                    alignment="center-right",
                )
            )

        body = Column(
            children,
            gap=8,
            cross_alignment="start",
        )
        content_width = self.width_sizing if self.width_sizing.kind == "fixed" else style.min_width
        return Box(
            child=body,
            width=content_width,
            height=self.height_sizing,
            padding=(style.horizontal_padding, style.top_padding, style.horizontal_padding, style.bottom_padding),
            background_color=style.container_color,
            corner_radius=style.corner_radius,
            shadow_color=shadow_color,
            shadow_offset=shadow_offset,
            shadow_blur=shadow_blur,
        )


__all__ = ["Tooltip", "RichTooltip"]
