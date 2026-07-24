"""Material Design 3 Text.

Provides a Material-decorated Text that defaults to the current Material theme.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Tuple, Union, TYPE_CHECKING

from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.observable import ReadOnlyObservableProtocol
from nuiitivet.theme.type_scale import TypeScaleToken
from nuiitivet.widgets.text import TextBase
from nuiitivet.widgets.text_style import TextStyleProtocol

if TYPE_CHECKING:
    from nuiitivet.material.styles.text_style import TextStyle


# Canonical union for anything a text/label-accepting widget can take: a static
# ``str`` or an observable string. Shared by Material widgets that surface a
# label (FAB menu, navigation rail) so the accepted label surface stays
# consistent with :class:`Text`.
LabelLike = Union[str, ReadOnlyObservableProtocol[str]]


class Text(TextBase):
    """Material text widget.

    Defaults to the current Material theme TextStyle.
    """

    def __init__(
        self,
        label: Union[str, ReadOnlyObservableProtocol[Any]],
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional["TextStyle"] = None,
        type_scale: Optional[TypeScaleToken] = None,
        alignment: Literal["start", "center", "end"] = "start",
        max_lines: Optional[int] = None,
        overflow: Literal["visible", "clip", "ellipsis"] = "visible",
        truncation: Literal["tail", "head", "middle"] = "tail",
        soft_wrap: bool = True,
    ):
        """Initialize Material Text widget.

        Args:
            label: The text content to display. Can be a string or an Observable.
            width: Width specification.
            height: Height specification.
            padding: Padding around the text.
            style: Custom Material TextStyle (color, font_family).
            type_scale: MD3 type-scale token supplying typography. Defaults to
                Body Medium.
            alignment: Horizontal text alignment (``"start"``, ``"center"``,
                ``"end"``).
            max_lines: Maximum number of lines (``None`` = unbounded).
            overflow: Overflow handling: ``"visible"``, ``"clip"`` or ``"ellipsis"``.
            truncation: Ellipsis position: ``"tail"``, ``"head"`` or ``"middle"``.
            soft_wrap: Whether to wrap at soft line breaks when width is bounded.
        """
        from nuiitivet.material.styles.text_style import TextStyle

        if style is not None and not isinstance(style, TextStyle):
            raise TypeError("style must be a material TextStyle")

        super().__init__(
            label=label,
            style=style,
            width=width,
            height=height,
            padding=padding,
            type_scale=type_scale,
            alignment=alignment,
            max_lines=max_lines,
            overflow=overflow,
            truncation=truncation,
            soft_wrap=soft_wrap,
        )

    @property
    def style(self) -> TextStyleProtocol:
        """Return the current text style, resolving from theme if necessary."""
        if self._style is not None:
            return self._style  # type: ignore
        from nuiitivet.material.theme.theme_data import MaterialThemeData
        from nuiitivet.theme.theme import Theme

        mat = Theme.of(self).extension(MaterialThemeData)
        if mat is None:
            from nuiitivet.material.styles.text_style import TextStyle

            return TextStyle()
        return mat.text_style


__all__ = ["Text"]
