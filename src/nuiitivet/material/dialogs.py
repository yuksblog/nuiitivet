"""Material Design Basic Dialog implementation.

This module contains the implementation of the Material Design 3 Basic Dialog,
specifically AlertDialog.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Union, TYPE_CHECKING

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.icon import Icon
from nuiitivet.material.styles.dialog_style import DialogStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.text import Text
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable import Observable, ObservableProtocol
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box

if TYPE_CHECKING:
    from nuiitivet.material.symbols import Symbol
    from nuiitivet.theme.types import ColorSpec

_logger = logging.getLogger(__name__)


class AlertDialog(ComposableWidget):
    """Material Alert dialog widget (Basic Dialog).

    Displays a modal dialog with optional icon, title, content, and action buttons.
    Follows Material Design 3 dialog guidelines.

    Args:
        title: Optional title text (str or Observable).
        message: Optional message text (str or Observable).
        icon: Optional icon (str, Symbol, or Observable).
        actions: list of action widgets (typically TextButtons).
        style: Optional DialogStyle. If None, uses theme default.
    """

    def __init__(
        self,
        title: Optional[Union[str, Observable]] = None,
        message: Optional[Union[str, Observable]] = None,
        *,
        icon: Optional[Union[str, "Symbol", ObservableProtocol]] = None,
        actions: Optional[List[Widget]] = None,
        style: Optional[DialogStyle] = None,
    ):
        super().__init__()
        self.title = title
        self.message = message
        self.icon = icon
        self.actions = actions or []
        self._user_style = style

    @property
    def style(self) -> DialogStyle:
        """Get the resolved dialog style."""
        if self._user_style is not None:
            return self._user_style

        from nuiitivet.theme.manager import manager
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = manager.current.extension(MaterialThemeData)
        if theme_data:
            return theme_data.alert_dialog_style

        return DialogStyle.basic()

    def build(self) -> Widget:
        style = self.style

        children: List[Widget] = []

        # 1. Icon
        if self.icon is not None:
            # MD3 Basic Dialog Icon: Secondary Color
            # Create a simple IconStyle override for color
            from nuiitivet.material.styles.icon_style import IconStyle

            # Note: Icon widget takes 'style' which is IconStyle.
            icon_style = IconStyle(color=ColorRole.SECONDARY, default_size=style.icon_size)

            children.append(
                Icon(
                    name=self.icon,
                    style=icon_style,
                )
            )
            children.append(Box(height=style.icon_bottom_gap))

        # 2. Title
        if self.title is not None:
            title_style = style.title_text_style
            if title_style is None:
                title_style = TextStyle(
                    font_size=24, color=ColorRole.ON_SURFACE, text_alignment="center" if self.icon else "start"
                )

            children.append(
                Text(
                    label=self.title,
                    style=title_style,
                )
            )
            children.append(Box(height=style.title_content_gap))

        # 3. Content
        if self.message is not None:
            content_style = style.content_text_style
            if content_style is None:
                content_style = TextStyle(
                    font_size=14,
                    color=ColorRole.ON_SURFACE_VARIANT,
                )

            children.append(
                Text(
                    label=self.message,
                    style=content_style,
                )
            )

        # 4. Actions
        if self.actions:
            children.append(Box(height=style.content_actions_gap))
            children.append(
                Row(
                    children=self.actions,
                    gap=style.actions_gap,
                    main_alignment=style.actions_alignment,
                    padding=style.actions_padding,
                )
            )

        return Box(
            background_color=style.background,
            corner_radius=style.corner_radius,
            padding=style.padding,
            width=312.0,  # Fixed width for Basic Dialog (until constraints supported)
            # Elevation mapping (simplified)
            shadow_blur=style.elevation,
            shadow_color=ColorRole.SHADOW,
            child=Column(
                children=children,
                gap=0,
                cross_alignment="start",
            ),
        )
