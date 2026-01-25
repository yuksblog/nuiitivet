"""Simple seed-based palette generator (HSL fallback PoC).

This module provides a lightweight `from_seed` that produces two role maps
for light and dark modes from a single seed color. It is intentionally a
proof-of-concept using HSL; for production-quality M3 palettes consider
integrating `material-color-utilities`.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple, Optional

from nuiitivet.common.logging_once import debug_once, exception_once

from ...colors.utils import (
    hex_to_rgb,
    rgb_to_hsl,
    make_tone,
    pick_accessible_foreground,
    normalize_literal_color,
)
from .color_role import ColorRole


logger = logging.getLogger(__name__)


# Note: integer -> hex conversion is provided by colors.utils.int_to_hex_rgb


def _use_mcu_corepalette(seed_hex: str) -> Optional[Tuple[Dict[ColorRole, str], Dict[ColorRole, str]]]:
    """Try to generate light/dark roles using material-color-utilities.

    Returns (light_roles, dark_roles) or None if MCU is unavailable.
    """
    try:
        # Try common import paths/objects for the Python MCU package
        import material_color_utilities as mcu
    except Exception:
        debug_once(logger, "palette_mcu_import_exc", "material_color_utilities is not available")
        return None
    # Some MCU releases expose a higher-level theme API instead of CorePalette.
    # Try to use theme_from_color (preferred in newer wheels) which returns a
    # Theme object with light/dark schemes. This handles the installed
    # material_color_utilities variants that don't expose CorePalette.
    try:
        if hasattr(mcu, "theme_from_color"):
            # theme_from_color expects a hex string source (not ARGB int)
            theme = mcu.theme_from_color(seed_hex)
            try:
                td = theme.dict()
            except Exception:
                exception_once(logger, "palette_mcu_theme_dict_exc", "MCU theme.dict() failed")
                return None

            light = td.get("schemes", {}).get("light", {})
            dark = td.get("schemes", {}).get("dark", {})

            # Map theme keys to our ColorRole names (best-effort)
            key_map = {
                ColorRole.PRIMARY: "primary",
                ColorRole.ON_PRIMARY: "on_primary",
                ColorRole.PRIMARY_CONTAINER: "primary_container",
                ColorRole.ON_PRIMARY_CONTAINER: "on_primary_container",
                ColorRole.INVERSE_PRIMARY: "inverse_primary",
                ColorRole.SECONDARY: "secondary",
                ColorRole.ON_SECONDARY: "on_secondary",
                ColorRole.SECONDARY_CONTAINER: "secondary_container",
                ColorRole.ON_SECONDARY_CONTAINER: "on_secondary_container",
                ColorRole.TERTIARY: "tertiary",
                ColorRole.ON_TERTIARY: "on_tertiary",
                ColorRole.TERTIARY_CONTAINER: "tertiary_container",
                ColorRole.ON_TERTIARY_CONTAINER: "on_tertiary_container",
                ColorRole.BACKGROUND: "background",
                ColorRole.ON_BACKGROUND: "on_background",
                ColorRole.SURFACE: "surface",
                ColorRole.ON_SURFACE: "on_surface",
                ColorRole.SURFACE_VARIANT: "surface_variant",
                ColorRole.ON_SURFACE_VARIANT: "on_surface_variant",
                ColorRole.SURFACE_CONTAINER_HIGHEST: "surface_container_highest",
                ColorRole.OUTLINE: "outline",
                ColorRole.SHADOW: "shadow",
                ColorRole.SCRIM: "scrim",
                ColorRole.ERROR: "error",
                ColorRole.ON_ERROR: "on_error",
                ColorRole.ERROR_CONTAINER: "error_container",
                ColorRole.ON_ERROR_CONTAINER: "on_error_container",
            }

            light_roles = {}
            dark_roles = {}

            def _resolve_from_mapping(mapping: dict, role: ColorRole, key_name: str):
                # Try common key variants and return first present value
                candidates = [key_name, role.value, role.name.lower(), role.value.lower(), key_name.replace("_", "")]
                for k in candidates:
                    if k in mapping and mapping.get(k) is not None:
                        return mapping.get(k)
                return None

            for role, key in key_map.items():
                lv = _resolve_from_mapping(light, role, key)
                dv = _resolve_from_mapping(dark, role, key)
                # Normalize MCU-provided values (int, tuple, hex, etc.)
                nl = normalize_literal_color(lv)
                nd = normalize_literal_color(dv)
                if isinstance(nl, str):
                    light_roles[role] = nl
                elif isinstance(nl, tuple) and len(nl) == 4:
                    # 4-element sequence (ARGB or RGBA) — take last 3 elements as RGB
                    vals = tuple(int(x) for x in nl[-3:])
                    light_roles[role] = "#{:02X}{:02X}{:02X}".format(*vals)

                if isinstance(nd, str):
                    dark_roles[role] = nd
                elif isinstance(nd, tuple) and len(nd) == 4:
                    vals = tuple(int(x) for x in nd[-3:])
                    dark_roles[role] = "#{:02X}{:02X}{:02X}".format(*vals)

            # Fallback for missing roles
            if ColorRole.SURFACE_CONTAINER_HIGHEST not in light_roles:
                light_roles[ColorRole.SURFACE_CONTAINER_HIGHEST] = light_roles.get(ColorRole.SURFACE_VARIANT, "#E7E0EC")
            if ColorRole.SURFACE_CONTAINER_HIGHEST not in dark_roles:
                dark_roles[ColorRole.SURFACE_CONTAINER_HIGHEST] = dark_roles.get(ColorRole.SURFACE_VARIANT, "#49454F")

            return light_roles, dark_roles
    except Exception:
        # Fall through to CorePalette-style introspection below
        exception_once(logger, "palette_mcu_theme_from_color_exc", "MCU theme_from_color path failed")

    # Find CorePalette class in common locations
    CorePalette = None
    for candidate in (getattr(mcu, "core", None), getattr(mcu, "palettes", None), getattr(mcu, "palette", None)):
        if candidate is None:
            continue
        CorePalette = getattr(candidate, "CorePalette", None) or getattr(candidate, "core_palette", None)
        if CorePalette is not None:
            break
    if CorePalette is None:
        CorePalette = getattr(mcu, "CorePalette", None)
    if CorePalette is None:
        return None

    try:
        # convert seed hex to ARGB int (alpha=255)
        r, g, b = hex_to_rgb(seed_hex)
        argb = (255 << 24) | (r << 16) | (g << 8) | b

        # CorePalette.of / CorePalette.of_argb / CorePalette.of_int are possible names
        cp = None
        for fn in ("of", "fromArgb", "from_argb", "of_int", "ofArgb"):
            factory = getattr(CorePalette, fn, None)
            if factory is None:
                continue
            try:
                cp = factory(argb)
                break
            except Exception:
                exception_once(
                    logger,
                    "palette_mcu_corepalette_factory_exc",
                    "MCU CorePalette factory failed (fn=%s)",
                    fn,
                )
                cp = None

        if cp is None:
            # Try calling CorePalette(argb)
            try:
                cp = CorePalette(argb)
            except Exception:
                exception_once(logger, "palette_mcu_corepalette_ctor_exc", "MCU CorePalette(argb) failed")
                return None

        # helper: get hex for a tone from a CorePalette member
        def tone_hex(pal_member, tone_val: int) -> str:
            try:
                if hasattr(pal_member, "tone"):
                    val = pal_member.tone(int(tone_val))
                elif hasattr(pal_member, "get"):
                    val = pal_member.get(int(tone_val))
                else:
                    val = pal_member[int(tone_val)]

                # Normalize various return forms (int, tuple, hex, etc.)
                nval = normalize_literal_color(val)
                if isinstance(nval, str):
                    return nval
                if isinstance(nval, tuple) and len(nval) >= 3:
                    # tuple may be RGBA/ARGB; take last 3 elements as RGB
                    vals = tuple(int(x) for x in nval[-3:])
                    return "#{:02X}{:02X}{:02X}".format(*vals)
                return "#808080"
            except Exception:
                exception_once(logger, "palette_mcu_tone_hex_exc", "Failed to compute tone hex")
                return "#808080"

        # Map expected M3 roles to appropriate tonal values. Use M3 canonical tones
        # for primary/secondary/tertiary (40 for primary, 100 for onPrimary etc.)
        mapping = [
            (ColorRole.PRIMARY, (cp.primary, 40)),
            (ColorRole.ON_PRIMARY, (cp.primary, 100)),
            (ColorRole.PRIMARY_CONTAINER, (cp.primary, 90 if hasattr(cp, "primary") else 92)),
            (ColorRole.ON_PRIMARY_CONTAINER, (cp.primary, 10)),
            (ColorRole.SECONDARY, (cp.secondary, 40)),
            (ColorRole.ON_SECONDARY, (cp.secondary, 100)),
            (ColorRole.SECONDARY_CONTAINER, (cp.secondary, 90)),
            (ColorRole.ON_SECONDARY_CONTAINER, (cp.secondary, 10)),
            (ColorRole.TERTIARY, (cp.tertiary, 40)),
            (ColorRole.ON_TERTIARY, (cp.tertiary, 100)),
            (ColorRole.TERTIARY_CONTAINER, (cp.tertiary, 90)),
            (ColorRole.ON_TERTIARY_CONTAINER, (cp.tertiary, 10)),
            (ColorRole.BACKGROUND, (cp.neutral, 99)),
            (ColorRole.ON_BACKGROUND, (cp.neutral, 10)),
            (ColorRole.SURFACE, (cp.neutral, 99)),
            (ColorRole.ON_SURFACE, (cp.neutral, 10)),
            (ColorRole.SURFACE_VARIANT, (cp.neutral_variant if hasattr(cp, "neutral_variant") else cp.neutral, 94)),
            (ColorRole.ON_SURFACE_VARIANT, (cp.neutral_variant if hasattr(cp, "neutral_variant") else cp.neutral, 30)),
            (ColorRole.SURFACE_CONTAINER_HIGHEST, (cp.neutral, 90)),
            (ColorRole.OUTLINE, (cp.neutral_variant if hasattr(cp, "neutral_variant") else cp.neutral, 60)),
            (ColorRole.ERROR, (cp.error if hasattr(cp, "error") else cp.primary, 40)),
            (ColorRole.ON_ERROR, (cp.error if hasattr(cp, "error") else cp.primary, 100)),
        ]

        light_roles = {}
        dark_roles = {}
        for role, (pal, tonev) in mapping:
            try:
                light_roles[role] = tone_hex(pal, tonev)
            except Exception:
                light_roles[role] = "#808080"

        # For dark: pick inverse-like tones (M3 typically uses different tones)
        for role, (pal, tonev) in mapping:
            try:
                # map some tones differently for dark
                if role == ColorRole.SURFACE_CONTAINER_HIGHEST:
                    dark_tone = 22
                else:
                    dark_tone = 80 if tonev == 40 else (12 if tonev == 100 else tonev)
                dark_roles[role] = tone_hex(pal, dark_tone)
            except Exception:
                dark_roles[role] = "#202020"

        # If primary unexpectedly equals between light/dark, nudge dark primary
        try:
            lp = light_roles.get(ColorRole.PRIMARY)
            dp = dark_roles.get(ColorRole.PRIMARY)
            if lp is not None and dp is not None and lp == dp:
                # try alternate dark tones until different
                for alt in (20, 80, 60, 30):
                    try:
                        nd = tone_hex(cp.primary, alt)
                        if nd != lp:
                            dark_roles[ColorRole.PRIMARY] = nd
                            break
                    except Exception:
                        exception_once(logger, "palette_mcu_primary_nudge_alt_exc", "Failed to compute alternate tone")
                        continue
        except Exception:
            exception_once(logger, "palette_mcu_primary_nudge_exc", "Failed to adjust dark primary tone")

        return light_roles, dark_roles
    except Exception:
        exception_once(logger, "palette_mcu_corepalette_exc", "MCU core palette generation failed")
        return None


def from_seed(seed_hex: str) -> Tuple[Dict[ColorRole, str], Dict[ColorRole, str]]:
    """Generate (light_roles, dark_roles) maps from a seed hex color.

    This is a PoC HSL approach. Returned dicts map ColorRole -> hex string.
    """
    # First try the material-color-utilities CorePalette path (optional)
    mcu_res = _use_mcu_corepalette(seed_hex)
    if mcu_res is not None:
        return mcu_res

    # Fallback: simple, deterministic HSL-based builder extracted to a helper
    return _hsl_roles_from_seed(seed_hex)


def _hsl_roles_from_seed(seed_hex: str) -> Tuple[Dict[ColorRole, str], Dict[ColorRole, str]]:
    """Simple, deterministic HSL-based palette builder used as a reliable fallback.

    This function intentionally keeps the algorithm straightforward: convert
    seed -> HSL, enforce a minimum saturation, and map fixed tone/lightness
    values to M3-like semantic roles. It's designed to be auditable and stable
    for unit testing.
    """
    try:
        r, g, b = hex_to_rgb(seed_hex)
    except Exception:
        r, g, b = (120, 120, 120)

    h, s, lightness = rgb_to_hsl(r, g, b)
    # clamp saturation so neutral seeds still produce colored primaries
    s = max(float(s or 0.0), 0.28)

    # fixed tone/lightness map — compact and explicit
    light_tone_map = {
        ColorRole.PRIMARY: 0.40,
        ColorRole.ON_PRIMARY: 0.98,
        ColorRole.PRIMARY_CONTAINER: 0.92,
        ColorRole.ON_PRIMARY_CONTAINER: 0.10,
        ColorRole.SECONDARY: 0.40,
        ColorRole.ON_SECONDARY: 0.98,
        ColorRole.SECONDARY_CONTAINER: 0.92,
        ColorRole.ON_SECONDARY_CONTAINER: 0.10,
        ColorRole.TERTIARY: 0.40,
        ColorRole.ON_TERTIARY: 0.98,
        ColorRole.TERTIARY_CONTAINER: 0.92,
        ColorRole.ON_TERTIARY_CONTAINER: 0.10,
        ColorRole.BACKGROUND: 0.99,
        ColorRole.ON_BACKGROUND: 0.10,
        ColorRole.SURFACE: 0.99,
        ColorRole.ON_SURFACE: 0.10,
        ColorRole.SURFACE_VARIANT: 0.94,
        ColorRole.ON_SURFACE_VARIANT: 0.30,
        ColorRole.SURFACE_CONTAINER_HIGHEST: 0.90,
        ColorRole.OUTLINE: 0.60,
        ColorRole.ERROR: 0.50,
        ColorRole.ON_ERROR: 0.98,
        ColorRole.ERROR_CONTAINER: 0.90,
        ColorRole.ON_ERROR_CONTAINER: 0.10,
    }

    dark_tone_map = {
        ColorRole.PRIMARY: 0.80,
        ColorRole.ON_PRIMARY: 0.12,
        ColorRole.PRIMARY_CONTAINER: 0.30,
        ColorRole.ON_PRIMARY_CONTAINER: 0.92,
        ColorRole.SECONDARY: 0.80,
        ColorRole.ON_SECONDARY: 0.12,
        ColorRole.SECONDARY_CONTAINER: 0.30,
        ColorRole.ON_SECONDARY_CONTAINER: 0.92,
        ColorRole.TERTIARY: 0.80,
        ColorRole.ON_TERTIARY: 0.12,
        ColorRole.TERTIARY_CONTAINER: 0.30,
        ColorRole.ON_TERTIARY_CONTAINER: 0.92,
        ColorRole.BACKGROUND: 0.06,
        ColorRole.ON_BACKGROUND: 0.94,
        ColorRole.SURFACE: 0.06,
        ColorRole.ON_SURFACE: 0.94,
        ColorRole.SURFACE_VARIANT: 0.24,
        ColorRole.ON_SURFACE_VARIANT: 0.88,
        ColorRole.SURFACE_CONTAINER_HIGHEST: 0.22,
        ColorRole.OUTLINE: 0.72,
        ColorRole.ERROR: 0.80,
        ColorRole.ON_ERROR: 0.12,
        ColorRole.ERROR_CONTAINER: 0.90,
        ColorRole.ON_ERROR_CONTAINER: 0.92,
    }

    light_roles: Dict[ColorRole, str] = {}
    dark_roles: Dict[ColorRole, str] = {}

    # helper to compute tone; containers use slightly reduced saturation
    def tone_for(role: ColorRole, tone_val: float, is_container: bool) -> str:
        sat_mult = 0.6 if is_container else 1.0
        # outline/scrim/shadow in this simplified builder are desaturated
        if role in (ColorRole.OUTLINE,):
            return make_tone(h, 0.0, tone_val)
        return make_tone(h, s, tone_val, sat_mult)

    for role, tonev in light_tone_map.items():
        is_container = "CONTAINER" in role.name
        light_roles[role] = tone_for(role, tonev, is_container)

    for role, tonev in dark_tone_map.items():
        is_container = "CONTAINER" in role.name
        dark_roles[role] = tone_for(role, tonev, is_container)

    # conservative contrast adjustments for key pairs — delegate to colors.utils
    if ColorRole.ON_PRIMARY in light_roles and ColorRole.PRIMARY in light_roles:
        light_roles[ColorRole.ON_PRIMARY] = pick_accessible_foreground(
            light_roles[ColorRole.ON_PRIMARY], light_roles[ColorRole.PRIMARY]
        )
    if ColorRole.ON_SURFACE in light_roles and ColorRole.SURFACE in light_roles:
        light_roles[ColorRole.ON_SURFACE] = pick_accessible_foreground(
            light_roles[ColorRole.ON_SURFACE], light_roles[ColorRole.SURFACE]
        )
    if ColorRole.ON_PRIMARY in dark_roles and ColorRole.PRIMARY in dark_roles:
        dark_roles[ColorRole.ON_PRIMARY] = pick_accessible_foreground(
            dark_roles[ColorRole.ON_PRIMARY], dark_roles[ColorRole.PRIMARY]
        )
    if ColorRole.ON_SURFACE in dark_roles and ColorRole.SURFACE in dark_roles:
        dark_roles[ColorRole.ON_SURFACE] = pick_accessible_foreground(
            dark_roles[ColorRole.ON_SURFACE], dark_roles[ColorRole.SURFACE]
        )

    # If primary is identical between light/dark, pick complement for dark
    lp = light_roles.get(ColorRole.PRIMARY)
    dp = dark_roles.get(ColorRole.PRIMARY)
    if lp and dp and lp == dp:
        try:
            rr, gg, bb = hex_to_rgb(lp)
            comp = "#{:02X}{:02X}{:02X}".format(255 - rr, 255 - gg, 255 - bb)
            if comp != lp:
                dark_roles[ColorRole.PRIMARY] = comp
        except Exception:
            exception_once(logger, "palette_complement_primary_exc", "Failed to compute complementary primary color")

    return light_roles, dark_roles


# Contrast picking is now delegated to colors.utils.pick_accessible_foreground


__all__ = ["from_seed"]
