"""Seed-based Material 3 palette generation.

Palettes are produced by `material-color-utilities` (MCU), which implements the
HCT color space and the Material 3 dynamic color algorithm. MCU is a required
dependency, so it is the only generation path.

MCU's own `theme_from_color` defaults are *not* the Material 3 defaults (it
ships `Variant.VIBRANT` at contrast `0.25`). `from_seed` always passes variant
and contrast level explicitly so the generated scheme matches the M3 spec unless
a caller deliberately asks for something else.
"""

from __future__ import annotations

from typing import Dict, Mapping, Tuple

import material_color_utilities as mcu

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

# MCU exposes every M3 role as a snake_case key matching `ColorRole.name.lower()`.
# The exceptions below are roles M3 has since folded into another role, which MCU
# no longer emits under their own name.
_ROLE_KEY_OVERRIDES: Dict[ColorRole, str] = {
    # M3 deprecated `onBackground`; `background` now always pairs with `onSurface`.
    ColorRole.ON_BACKGROUND: "on_surface",
}


def _role_key(role: ColorRole) -> str:
    """Return the MCU scheme key that carries `role`."""
    return _ROLE_KEY_OVERRIDES.get(role, role.name.lower())


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


def _roles_from_scheme(scheme: Mapping[str, object]) -> RoleMap:
    """Extract a ColorRole -> hex map from one MCU scheme dict."""
    roles: RoleMap = {}
    for role in ColorRole:
        value = scheme.get(_role_key(role))
        if isinstance(value, str):
            roles[role] = value
    return roles


def from_seed(
    seed_color: str,
    *,
    variant: SchemeVariant = DEFAULT_VARIANT,
    contrast_level: float = DEFAULT_CONTRAST_LEVEL,
) -> Tuple[RoleMap, RoleMap]:
    """Generate (light_roles, dark_roles) from a seed color.

    Args:
        seed_color: Source color as hex or CSS color name.
        variant: Palette derivation algorithm. Defaults to the M3 default,
            `SchemeVariant.TONAL_SPOT`.
        contrast_level: Contrast adjustment in [-1.0, 1.0]. Defaults to the M3
            default of 0.0; higher values darken/lighten roles for more contrast.

    Raises:
        ValueError: If `seed_color` is not a valid color or `contrast_level` is
            out of range.
    """
    seed_hex = _normalize_seed(seed_color)
    level = _validate_contrast_level(contrast_level)

    theme = mcu.theme_from_color(
        seed_hex,
        contrast_level=level,
        variant=getattr(mcu.Variant, variant.value),
    )
    schemes = theme.dict()["schemes"]
    return _roles_from_scheme(schemes["light"]), _roles_from_scheme(schemes["dark"])


__all__ = ["from_seed", "RoleMap"]
