"""Seed-based Material 3 palette generation.

Palettes are produced by `materialyoucolor`, a pure-Python implementation of the
HCT color space and the Material 3 dynamic color algorithm. It is a required
dependency, so it is the only generation path.

`materialyoucolor` defaults to the Material 3 **2025** color spec, which retones
roughly 39% of the roles. nuiitivet targets the 2021 spec, so both the scheme and
the role definitions are pinned to it explicitly; see `SPEC_VERSION`. Variant and
contrast level are likewise always passed explicitly, so a generated scheme
matches the M3 spec unless a caller deliberately asks for something else.
"""

from __future__ import annotations

from typing import Dict

from materialyoucolor.dynamiccolor.dynamic_scheme import DynamicScheme, SpecVersion
from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors
from materialyoucolor.dynamiccolor.variant import Variant
from materialyoucolor.hct.hct import Hct

from ...colors.utils import hex_to_rgb, normalize_literal_color
from .color_role import ColorRole
from .scheme_variant import (
    DEFAULT_CONTRAST_LEVEL,
    DEFAULT_VARIANT,
    MAX_CONTRAST_LEVEL,
    MIN_CONTRAST_LEVEL,
    SchemeVariant,
)

RoleMap = Dict[ColorRole, str]

#: Material 3 color spec the palettes are generated against. `materialyoucolor`
#: defaults to "2025"; adopting that spec is a deliberate, separate decision.
SPEC_VERSION: SpecVersion = "2021"

# Every M3 role is a `MaterialDynamicColors` attribute named exactly like the
# `ColorRole` value, so roles need no key translation. Building the spec walks
# all 56 role definitions, so it is built once.
_DYNAMIC_COLORS = MaterialDynamicColors(SPEC_VERSION)


def _normalize_seed(seed: str) -> str:
    """Validate a seed color and return it as an "#RRGGBB" string.

    Accepts hex (short or long form, with or without '#') and CSS color names.
    """
    normalized = normalize_literal_color(seed)
    if not isinstance(normalized, str):
        raise ValueError(f"Invalid seed color: {seed!r}")
    r, g, b = hex_to_rgb(normalized)
    return "#{:02X}{:02X}{:02X}".format(r, g, b)


def _validate_contrast_level(contrast_level: float) -> float:
    value = float(contrast_level)
    if not MIN_CONTRAST_LEVEL <= value <= MAX_CONTRAST_LEVEL:
        raise ValueError(
            f"contrast_level must be within [{MIN_CONTRAST_LEVEL}, {MAX_CONTRAST_LEVEL}], got {contrast_level!r}"
        )
    return value


def _seed_hct(seed_hex: str) -> Hct:
    r, g, b = hex_to_rgb(seed_hex)
    return Hct.from_int((0xFF << 24) | (r << 16) | (g << 8) | b)


def _build_scheme(seed: Hct, variant: SchemeVariant, dark: bool, contrast_level: float) -> DynamicScheme:
    return DynamicScheme(
        source_color_hct=seed,
        variant=Variant[variant.value],
        contrast_level=contrast_level,
        is_dark=dark,
        spec_version=SPEC_VERSION,
    )


def _roles_from_scheme(scheme: DynamicScheme) -> RoleMap:
    """Resolve every `ColorRole` against one scheme."""
    roles: RoleMap = {}
    for role in ColorRole:
        argb = getattr(_DYNAMIC_COLORS, role.value).get_argb(scheme)
        roles[role] = "#{:06x}".format(argb & 0xFFFFFF)
    return roles


def from_seed(
    seed_color: str,
    *,
    dark: bool = False,
    variant: SchemeVariant = DEFAULT_VARIANT,
    contrast_level: float = DEFAULT_CONTRAST_LEVEL,
) -> RoleMap:
    """Generate the color roles of a single scheme from a seed color.

    Args:
        seed_color: Source color as hex or CSS color name.
        dark: Generate the dark scheme instead of the light one.
        variant: Palette derivation algorithm. Defaults to the M3 default,
            `SchemeVariant.TONAL_SPOT`.
        contrast_level: Contrast adjustment in [-1.0, 1.0]. Defaults to the M3
            default of 0.0; higher values darken/lighten roles for more contrast.

    Raises:
        ValueError: If `seed_color` is not a valid color or `contrast_level` is
            out of range.
    """
    seed = _seed_hct(_normalize_seed(seed_color))
    level = _validate_contrast_level(contrast_level)
    return _roles_from_scheme(_build_scheme(seed, variant, dark, level))


__all__ = ["from_seed", "RoleMap", "SPEC_VERSION"]
