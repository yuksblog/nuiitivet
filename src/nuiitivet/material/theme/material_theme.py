"""Material Theme factory."""

from __future__ import annotations

from typing import Tuple

from nuiitivet.scrolling import ScrollbarThemeData
from nuiitivet.theme.theme import Theme
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.material.theme.palette import from_seed
from nuiitivet.material.theme.scheme_variant import (
    DEFAULT_CONTRAST_LEVEL,
    DEFAULT_VARIANT,
    SchemeVariant,
)


def _material_scrollbar_theme_data() -> ScrollbarThemeData:
    """Default scrollbar palette mapped onto Material color roles.

    Colors are stored as tokens (not resolved RGBA), so the same instance
    resolves to the correct light/dark values against whichever theme is active.
    """
    return ScrollbarThemeData(
        track=(ColorRole.ON_SURFACE, 0.12),
        thumb=(ColorRole.ON_SURFACE, 0.70),
        thumb_hover=(ColorRole.PRIMARY, 0.90),
        thumb_active=(ColorRole.PRIMARY, 1.0),
    )


class MaterialThemeFactory:
    """Factory for creating Themes with Material Design configuration."""

    @staticmethod
    def from_seed(
        seed_color: str,
        mode: str = "light",
        name: str = "",
        *,
        variant: SchemeVariant = DEFAULT_VARIANT,
        contrast_level: float = DEFAULT_CONTRAST_LEVEL,
    ) -> Theme:
        """Create a Material theme from a seed color.

        `variant` and `contrast_level` default to the Material 3 defaults; see
        `nuiitivet.material.theme.palette.from_seed`.
        """
        roles = from_seed(
            seed_color, dark=(mode == "dark"), variant=variant, contrast_level=contrast_level
        )

        material_data = MaterialThemeData(roles=roles)
        return Theme(
            mode=mode,
            extensions=[material_data, _material_scrollbar_theme_data()],
            name=name,
        )

    @staticmethod
    def light(
        seed_color: str,
        *,
        variant: SchemeVariant = DEFAULT_VARIANT,
        contrast_level: float = DEFAULT_CONTRAST_LEVEL,
    ) -> Theme:
        return MaterialThemeFactory.from_seed(
            seed_color, mode="light", variant=variant, contrast_level=contrast_level
        )

    @staticmethod
    def dark(
        seed_color: str,
        *,
        variant: SchemeVariant = DEFAULT_VARIANT,
        contrast_level: float = DEFAULT_CONTRAST_LEVEL,
    ) -> Theme:
        return MaterialThemeFactory.from_seed(
            seed_color, mode="dark", variant=variant, contrast_level=contrast_level
        )

    @staticmethod
    def from_seed_pair(
        seed_color: str,
        name: str = "",
        *,
        variant: SchemeVariant = DEFAULT_VARIANT,
        contrast_level: float = DEFAULT_CONTRAST_LEVEL,
    ) -> Tuple[Theme, Theme]:
        """Create light and dark themes from a seed color."""
        return (
            MaterialThemeFactory.from_seed(
                seed_color, mode="light", name=name, variant=variant, contrast_level=contrast_level
            ),
            MaterialThemeFactory.from_seed(
                seed_color, mode="dark", name=name, variant=variant, contrast_level=contrast_level
            ),
        )
