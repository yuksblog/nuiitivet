"""Dialog widget style.

Provides the DialogStyle dataclass for Dialog widget styling.
"""

from dataclasses import dataclass, replace
from typing import Optional, Tuple, Union, TYPE_CHECKING

from nuiitivet.theme.types import ColorSpec
from ..theme.color_role import ColorRole
from .text_style import TextStyle

if TYPE_CHECKING:
    from ...theme import Theme


PaddingLike = Union[int, Tuple[int, int], Tuple[int, int, int, int]]


@dataclass(frozen=True)
class DialogStyle:
    """Immutable style for Dialog widgets (MD3 Basic Dialog)."""

    # Container properties
    background: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGHEST
    elevation: float = 6.0

    # Shape
    corner_radius: float = 28.0

    # Layout Constraints
    min_width: float = 280.0
    max_width: float = 560.0
    padding: PaddingLike = 24  # Container internal padding

    # Text Styles (Optional overrides)
    title_text_style: Optional[TextStyle] = None  # Defaults to headlineSmall (24sp)
    content_text_style: Optional[TextStyle] = None  # Defaults to bodyMedium (14sp)

    # Content Layout
    icon_size: int = 24
    icon_bottom_gap: int = 16  # Gap between icon and title
    title_content_gap: int = 16
    content_actions_gap: int = 24
    actions_padding: PaddingLike = (0, 0, 0, 0)  # Additional padding for actions area if needed
    actions_gap: int = 8
    actions_alignment: str = "end"  # 'start', 'center', 'end', 'space-between'

    def copy_with(self, **changes) -> "DialogStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    def resolve_colors(self, theme: "Theme | None" = None) -> dict:
        """Resolve abstract colors to concrete RGBA."""
        from ...theme.resolver import resolve_color_to_rgba

        return {
            "background": resolve_color_to_rgba(self.background, theme=theme),
        }

    @classmethod
    def basic(cls) -> "DialogStyle":
        """Default Basic Dialog style."""
        return cls()

    @classmethod
    def alert(cls) -> "DialogStyle":
        """Alert Dialog style (alias for basic, can be customized)."""
        return cls()
