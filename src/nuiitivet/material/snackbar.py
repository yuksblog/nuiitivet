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
        key: Optional[str] = None,
    ) -> None:
        """Initialize Snackbar.

        Args:
            message: Text to display.
            padding: Insets from the allocated rect to the container.
            style: Visual style; defaults to :class:`SnackbarStyle`.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(padding=padding, key=key)
        self.message = str(message)
        self.style = style if style is not None else SnackbarStyle()

    def build(self) -> Widget:
        return Box(
            background_color=self.style.background,
            corner_radius=self.style.corner_radius,
            padding=self.style.content_insets,
            child=Text(
                self.message,
                style=TextStyle(color=self.style.foreground),
            ),
        )
