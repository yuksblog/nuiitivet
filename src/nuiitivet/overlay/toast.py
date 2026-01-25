"""Toast widget for displaying temporary messages."""

from __future__ import annotations

from typing import Tuple, Union

from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.text_style import TextStyle
from nuiitivet.theme.types import ColorSpec


class PlainToast(ComposableWidget):
    """A temporary message that appears at the bottom of the screen.

    Toasts are used to show brief messages that don't require user interaction.
    They automatically disappear after a short duration.

    Example:
        toast = PlainToast(message="File saved successfully")
    """

    def __init__(
        self,
        message: str,
        *,
        background_color: ColorSpec = (50, 50, 50, 230),
        text_color: ColorSpec = (255, 255, 255, 255),
        padding: Union[int, Tuple[int, int, int, int]] = 16,
        corner_radius: float = 8.0,
    ):
        """Create a toast widget.

        Args:
            message: The message to display.
            background_color: Background color of the toast.
            text_color: Text color.
            padding: Padding around the text.
            corner_radius: Corner radius for rounded corners.
        """
        super().__init__()
        self.message = message
        self.background_color = background_color
        self.text_color = text_color
        self.padding = padding
        self.corner_radius = corner_radius

    def build(self) -> Widget:
        """Build the toast widget tree.

        Returns:
            A Box containing the message text.
        """
        return Box(
            background_color=self.background_color,
            corner_radius=self.corner_radius,
            padding=self.padding,
            child=Text(
                self.message,
                style=TextStyle(color=self.text_color),
            ),
        )
