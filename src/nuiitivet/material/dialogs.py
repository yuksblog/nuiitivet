"""Material Design Dialogs.

This module contains Material Design 3 implementations of standard dialogs.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from nuiitivet.layout.column import Column
from nuiitivet.layout.row import Row
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.observable import Observable
from nuiitivet.theme.types import ColorSpec
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.text import TextBase as Text


class AlertDialog(ComposableWidget):
    """Material Alert dialog widget.

    Displays a modal dialog with title, content, and action buttons.
    Follows Material Design 3 dialog guidelines.

    Args:
        title: Optional title widget (typically Text).
        content: Optional content widget.
        actions: List of action widgets (typically Buttons).
        background_color: Dialog background color.
        padding: Padding around the content.
        corner_radius: Corner radius for the dialog.
        width: Dialog width.
    """

    def __init__(
        self,
        *,
        title: Optional[Widget] = None,
        content: Optional[Widget] = None,
        actions: Optional[List[Widget]] = None,
        background_color: ColorSpec = ColorRole.SURFACE,
        padding: int = 24,
        corner_radius: float = 28.0,
        width: Optional[float] = 312.0,
    ):
        super().__init__()
        self.title = title
        self.content = content
        self.actions = actions or []
        self.background_color = background_color
        self.padding = padding
        self.corner_radius = corner_radius
        self.width = width

    def build(self) -> Widget:
        children: List[Widget] = []

        # Add title if present
        if self.title is not None:
            children.append(self.title)

        # Add content if present
        if self.content is not None:
            children.append(self.content)

        # Add actions if present
        if self.actions:
            children.append(
                Row(
                    children=self.actions,
                    gap=8,
                    main_alignment="end",
                )
            )

        return Box(
            background_color=self.background_color,
            corner_radius=self.corner_radius,
            padding=self.padding,
            width=self.width,
            child=Column(
                children=children,
                gap=16,
            ),
        )
