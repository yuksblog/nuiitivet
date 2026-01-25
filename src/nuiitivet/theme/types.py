"""Theme-level type aliases and protocols.

`ColorLike` is the canonical type alias for color-like values and lives
under the `theme` package as it is a theme/domain concept.
"""

from __future__ import annotations

from typing import Any, Protocol, Tuple, Union, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


ColorLike = Union[
    str,  # "#RRGGBB" or "#RRGGBBAA"
    Tuple[int, int, int],  # RGB
    Tuple[int, int, int, int],  # RGBA
    int,  # 0xRRGGBBAA
    None,
]


@runtime_checkable
class ColorToken(Protocol):
    """Theme color token.

    This is a marker protocol to keep the theme layer decoupled from any
    specific design system token types.
    """

    def resolve(self, theme: "Theme | None" = None) -> ColorLike | None:
        """Resolve this token into a concrete ColorLike.

        Returns None if the token cannot be resolved in the current theme.
        """
        ...


ColorBase = Union[
    ColorLike,
    ColorToken,
]


ColorSpec = Union[
    ColorBase,
    Tuple[ColorBase, float],  # (base, alpha) where alpha multiplies resolved alpha (0.0..1.0)
]


@runtime_checkable
class ThemeExtension(Protocol):
    """Protocol for theme extensions (design system specific data)."""

    def copy_with(self, **kwargs: Any) -> "ThemeExtension":
        """Create a copy of this extension with the given fields replaced."""
        ...


__all__ = ["ColorBase", "ColorLike", "ColorSpec", "ColorToken", "ThemeExtension"]
