"""Material Text widget style.

Provides the TextStyle dataclass for Text widget styling, following the
same pattern as ButtonStyle, IconStyle, and CheckboxStyle.

Layer boundaries:

* Typography (font size / line height / weight / tracking) lives on the
  ``type_scale`` :class:`~nuiitivet.theme.type_scale.TypeScaleToken`.
* Layout / flow behavior (alignment, wrapping, overflow) lives on the Text
  widget itself.
* This style carries only the reusable visual look — ``color`` and
  ``font_family``.
"""

from dataclasses import dataclass, replace

from nuiitivet.theme.types import ColorSpec
from ..theme.color_role import ColorRole


@dataclass(frozen=True)
class TextStyle:
    """Immutable visual style for Material Text widgets (M3-compliant).

    Use copy_with() to create style variants.

    Material Design 3 Text specifications:
    - Default color: ON_SURFACE

    Typography comes from the widget's ``type_scale`` and alignment from the
    widget itself, so neither lives here.
    """

    color: ColorSpec = ColorRole.ON_SURFACE
    font_family: str | None = None

    def copy_with(self, **changes) -> "TextStyle":
        """Create a new style instance with specified fields changed.

        Example:
            error_style = TextStyle().copy_with(color=ColorRole.ERROR)
        """
        return replace(self, **changes)


__all__ = ["TextStyle"]
