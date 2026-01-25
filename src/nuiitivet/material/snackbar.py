"""Material Design Snackbar."""

from __future__ import annotations

from typing import Optional, Tuple, Union

from nuiitivet.material.styles.snackbar_style import SnackbarStyle
from nuiitivet.material.styles.text_style import TextStyle
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.text import TextBase as Text


class Snackbar(ComposableWidget):
    """Material Design Snackbar.

    Displays a brief message at the bottom of the screen.
    """

    def __init__(
        self,
        message: str,
        *,
        padding: Optional[Union[int, Tuple[int, int, int, int]]] = None,
        style: Optional[SnackbarStyle] = None,
    ) -> None:
        super().__init__()
        self.message = str(message)

        resolved_style = style if style is not None else SnackbarStyle()
        self.style = resolved_style
        self.padding = padding if padding is not None else resolved_style.padding

    def build(self) -> Widget:
        return Box(
            background_color=self.style.background,
            corner_radius=self.style.corner_radius,
            padding=self.padding,
            child=Text(
                self.message,
                style=TextStyle(color=self.style.foreground),
            ),
        )
