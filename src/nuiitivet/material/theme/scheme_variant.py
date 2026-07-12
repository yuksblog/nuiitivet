"""Material 3 dynamic color scheme variants."""

from __future__ import annotations

from enum import Enum


class SchemeVariant(Enum):
    """Algorithm used to derive a tonal palette from a seed color.

    Each member's value is the corresponding ``material_color_utilities.Variant``
    attribute name.
    """

    MONOCHROME = "MONOCHROME"
    NEUTRAL = "NEUTRAL"
    TONAL_SPOT = "TONALSPOT"
    VIBRANT = "VIBRANT"
    EXPRESSIVE = "EXPRESSIVE"
    FIDELITY = "FIDELITY"
    CONTENT = "CONTENT"
    RAINBOW = "RAINBOW"
    FRUIT_SALAD = "FRUITSALAD"


#: Variant used by Material 3 when none is specified.
DEFAULT_VARIANT = SchemeVariant.TONAL_SPOT

#: Contrast level used by Material 3 when none is specified.
DEFAULT_CONTRAST_LEVEL = 0.0

#: Bounds accepted for a contrast level.
MIN_CONTRAST_LEVEL = -1.0
MAX_CONTRAST_LEVEL = 1.0


__all__ = [
    "SchemeVariant",
    "DEFAULT_VARIANT",
    "DEFAULT_CONTRAST_LEVEL",
    "MIN_CONTRAST_LEVEL",
    "MAX_CONTRAST_LEVEL",
]
