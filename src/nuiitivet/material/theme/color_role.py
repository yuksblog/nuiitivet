"""ColorRole enum separated into its own module.

This file contains the Material 3 canonical color role enumeration so it can
be imported independently from other theme utilities.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from nuiitivet.theme.manager import manager

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


class ColorRole(Enum):
    """Material 3 Color Roles — canonical 26 roles used by M3."""

    def resolve(self, theme: "Theme | None" = None) -> str | None:
        try:
            from nuiitivet.material.theme.theme_data import MaterialThemeData

            source_theme = theme if theme is not None else manager.current
            theme_data = source_theme.extension(MaterialThemeData)
            if theme_data is None:
                return None
            return theme_data.roles.get(self)
        except Exception:
            return None

    PRIMARY = "primary"
    ON_PRIMARY = "onPrimary"
    PRIMARY_CONTAINER = "primaryContainer"
    ON_PRIMARY_CONTAINER = "onPrimaryContainer"
    INVERSE_PRIMARY = "inversePrimary"

    SECONDARY = "secondary"
    ON_SECONDARY = "onSecondary"
    SECONDARY_CONTAINER = "secondaryContainer"
    ON_SECONDARY_CONTAINER = "onSecondaryContainer"

    TERTIARY = "tertiary"
    ON_TERTIARY = "onTertiary"
    TERTIARY_CONTAINER = "tertiaryContainer"
    ON_TERTIARY_CONTAINER = "onTertiaryContainer"

    BACKGROUND = "background"
    ON_BACKGROUND = "onBackground"

    SURFACE = "surface"
    ON_SURFACE = "onSurface"
    SURFACE_VARIANT = "surfaceVariant"
    ON_SURFACE_VARIANT = "onSurfaceVariant"
    SURFACE_CONTAINER_HIGHEST = "surfaceContainerHighest"

    OUTLINE = "outline"
    SHADOW = "shadow"
    SCRIM = "scrim"

    ERROR = "error"
    ON_ERROR = "onError"
    ERROR_CONTAINER = "errorContainer"
    ON_ERROR_CONTAINER = "onErrorContainer"


__all__ = ["ColorRole"]
