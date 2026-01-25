"""Material Design 3 Text.

Provides a Material-decorated Text that defaults to the current Material theme.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union, TYPE_CHECKING

from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.theme.manager import manager
from nuiitivet.observable import Observable
from nuiitivet.widgets.text import TextBase
from nuiitivet.widgets.text_style import TextStyleProtocol

if TYPE_CHECKING:
    from nuiitivet.material.styles.text_style import TextStyle


class Text(TextBase):
    """Material text widget.

    Defaults to the current Material theme TextStyle.
    """

    def __init__(
        self,
        label: Union[str, Observable],
        style: Optional["TextStyle"] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
    ):
        from nuiitivet.material.styles.text_style import TextStyle

        if style is not None and not isinstance(style, TextStyle):
            raise TypeError("style must be a material TextStyle")

        super().__init__(
            label=label,
            style=style,
            width=width,
            height=height,
            padding=padding,
        )

    @property
    def style(self) -> TextStyleProtocol:
        """Return the current text style, resolving from theme if necessary."""
        if self._style is not None:
            return self._style  # type: ignore
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme = manager.current.extension(MaterialThemeData)
        if theme is None:
            raise ValueError("MaterialThemeData not found in current theme")
        return theme.text_style


__all__ = ["Text"]
