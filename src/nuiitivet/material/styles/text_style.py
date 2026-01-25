"""Text widget style.

Provides the TextStyle dataclass for Text widget styling, following the
same pattern as ButtonStyle, IconStyle, and CheckboxStyle.
"""

from dataclasses import dataclass, replace
from typing import Literal

from nuiitivet.theme.types import ColorSpec
from ..theme.color_role import ColorRole


@dataclass(frozen=True)
class TextStyle:
    """Immutable style for Text widgets (M3-compliant).

    Provides typography and layout styling for Text widgets.
    Use copy_with() to create style variants.

    Material Design 3 Text specifications:
    - Default font size: 14pt (body medium)
    - Default color: ON_SURFACE
    - Default alignment: left
    - Default overflow: visible
    """

    # Typography
    font_size: int = 14
    font_family: str | None = None

    # Color
    color: ColorSpec = ColorRole.ON_SURFACE

    # Layout
    text_alignment: Literal["start", "center", "end"] = "start"
    overflow: Literal["visible", "clip", "ellipsis"] = "visible"

    def copy_with(self, **changes) -> "TextStyle":
        """Create a new style instance with specified fields changed.

        Example:
            base_style = TextStyle(font_size=14)
            large_style = base_style.copy_with(font_size=24)
            error_style = base_style.copy_with(color=ColorRole.ERROR)
        """
        return replace(self, **changes)


__all__ = ["TextStyle"]
