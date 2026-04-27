from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Tuple, TYPE_CHECKING

from ..theme.color_role import ColorRole
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from ...theme import Theme


TextFieldMode = Literal["filled", "outlined"]


@dataclass(frozen=True)
class TextFieldStyle:
    """Style configuration for :class:`TextField` (M3-compliant).

    The visual variant is captured by the :attr:`mode` field: ``"filled"``
    draws an underline indicator with top-rounded container corners while
    ``"outlined"`` draws a full rectangular border. Use the :meth:`filled`
    and :meth:`outlined` factory methods to obtain the standard presets.
    """

    # Visual mode (drives container shape and indicator drawing)
    mode: TextFieldMode = "filled"

    # Container
    container_color: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGHEST

    # Border / Indicator
    indicator_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    indicator_width: float = 1.0
    focused_indicator_color: ColorSpec = ColorRole.PRIMARY
    focused_indicator_width: float = 2.0
    error_indicator_color: ColorSpec = ColorRole.ERROR

    # Text
    text_color: ColorSpec = ColorRole.ON_SURFACE
    label_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    focused_label_color: ColorSpec = ColorRole.PRIMARY
    error_label_color: ColorSpec = ColorRole.ERROR
    supporting_text_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    error_supporting_text_color: ColorSpec = ColorRole.ERROR

    # Cursor & Selection
    cursor_color: ColorSpec = ColorRole.PRIMARY
    error_cursor_color: ColorSpec = ColorRole.ERROR
    selection_color: ColorSpec = ColorRole.PRIMARY_CONTAINER  # Usually with opacity

    # Shape
    border_radius: float = 4.0  # Top corners for filled, all for outlined

    # Layout
    content_padding: Tuple[int, int, int, int] = (16, 16, 16, 16)  # L, T, R, B

    def copy_with(self, **changes) -> "TextFieldStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    @classmethod
    def filled(cls) -> "TextFieldStyle":
        """Default M3 Filled TextField style."""
        return cls(
            mode="filled",
            container_color=ColorRole.SURFACE_CONTAINER_HIGHEST,
            indicator_color=ColorRole.ON_SURFACE_VARIANT,
            border_radius=4.0,
            content_padding=(16, 8, 16, 8),  # Adjusted for label
        )

    @classmethod
    def outlined(cls) -> "TextFieldStyle":
        """Default M3 Outlined TextField style."""
        return cls(
            mode="outlined",
            container_color=(0, 0, 0, 0),  # Transparent
            indicator_color=ColorRole.OUTLINE,
            focused_indicator_width=3.0,  # MD3: focused outline width = 3dp
            border_radius=4.0,
            content_padding=(16, 16, 16, 16),
        )

    @classmethod
    def from_theme(cls, theme: "Theme") -> "TextFieldStyle":
        """Resolve the default :class:`TextFieldStyle` for the given theme.

        Returns the theme's filled text field style if a Material theme
        extension is present, otherwise a fresh :meth:`filled` preset.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        if theme_data:
            return theme_data.filled_text_field_style
        return cls.filled()
