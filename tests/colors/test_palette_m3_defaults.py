"""Pin the generated palette to the Material 3 reference scheme.

Two defaults have to be held down. `materialyoucolor` generates against the M3
**2025** spec unless told otherwise, which retones most roles, and its schemes
carry their own variant/contrast defaults. These tests fail if palette generation
ever stops pinning the 2021 spec, the variant and the contrast level explicitly.
"""

import pytest

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.palette import from_seed
from nuiitivet.material.theme.scheme_variant import SchemeVariant

# Reference values published by Material 3 for the baseline seed.
BASELINE_SEED = "#6750A4"
BASELINE_LIGHT = {
    ColorRole.PRIMARY: "#65558f",
    ColorRole.ON_PRIMARY: "#ffffff",
    ColorRole.PRIMARY_CONTAINER: "#e9ddff",
    ColorRole.SECONDARY: "#625b71",
    ColorRole.TERTIARY: "#7e5260",
    ColorRole.SURFACE: "#fdf7ff",
    ColorRole.ON_SURFACE: "#1d1b20",
    ColorRole.ERROR: "#ba1a1a",
}
BASELINE_DARK = {
    ColorRole.PRIMARY: "#cfbdfe",
    ColorRole.ON_PRIMARY: "#36275d",
    ColorRole.PRIMARY_CONTAINER: "#4d3d75",
}


def test_default_scheme_matches_m3_reference() -> None:
    light = from_seed(BASELINE_SEED)
    dark = from_seed(BASELINE_SEED, dark=True)
    for role, expected in BASELINE_LIGHT.items():
        assert light[role].lower() == expected, f"light {role.name}"
    for role, expected in BASELINE_DARK.items():
        assert dark[role].lower() == expected, f"dark {role.name}"


def test_default_scheme_is_not_the_2025_spec() -> None:
    """Guard the spec pin: under the 2025 spec `onSurface` tones to #34313a."""
    light = from_seed(BASELINE_SEED)
    assert light[ColorRole.ON_SURFACE].lower() == "#1d1b20"


def test_every_color_role_is_populated() -> None:
    light = from_seed(BASELINE_SEED)
    dark = from_seed(BASELINE_SEED, dark=True)
    assert set(light) == set(ColorRole)
    assert set(dark) == set(ColorRole)


def test_on_background_matches_on_surface_at_default_contrast() -> None:
    """M3 pairs `background` with `onSurface`, and both sit at neutral tone 10/90.

    The two only part company away from the default contrast level, where
    `onBackground` follows a lower-emphasis contrast curve.
    """
    light = from_seed(BASELINE_SEED)
    assert light[ColorRole.ON_BACKGROUND] == light[ColorRole.ON_SURFACE]


def test_variant_is_honored() -> None:
    tonal = from_seed(BASELINE_SEED, variant=SchemeVariant.TONAL_SPOT)
    vibrant = from_seed(BASELINE_SEED, variant=SchemeVariant.VIBRANT)
    assert tonal[ColorRole.PRIMARY] != vibrant[ColorRole.PRIMARY]


def test_contrast_level_is_honored() -> None:
    """Raising contrast must darken primary against a light surface."""
    from nuiitivet.colors.utils import contrast_ratio

    low = from_seed(BASELINE_SEED, contrast_level=0.0)
    high = from_seed(BASELINE_SEED, contrast_level=1.0)

    low_ratio = contrast_ratio(low[ColorRole.PRIMARY], low[ColorRole.SURFACE])
    high_ratio = contrast_ratio(high[ColorRole.PRIMARY], high[ColorRole.SURFACE])
    assert high_ratio > low_ratio


def test_dark_scheme_differs_from_light() -> None:
    light = from_seed(BASELINE_SEED)
    dark = from_seed(BASELINE_SEED, dark=True)
    assert light[ColorRole.PRIMARY] != dark[ColorRole.PRIMARY]
    assert light[ColorRole.SURFACE] != dark[ColorRole.SURFACE]


def test_seed_accepts_css_name_and_short_hex() -> None:
    assert from_seed("#00F") == from_seed("#0000FF")
    assert from_seed("rebeccapurple")[ColorRole.PRIMARY].startswith("#")


@pytest.mark.parametrize("variant", list(SchemeVariant))
@pytest.mark.parametrize("seed", ["white", "black", "#010101"])
def test_achromatic_seeds_do_not_raise(seed: str, variant: SchemeVariant) -> None:
    """Tone-extreme seeds must generate a full palette without raising.

    These seeds once tripped a `ZeroDivisionError` in `materialyoucolor`'s
    `TemperatureCache` (a collapsed hue sweep); the fix landed upstream in
    3.0.3. This guards against a regression in the dependency.
    """
    roles = from_seed(seed, variant=variant)
    assert set(roles) == set(ColorRole)


@pytest.mark.parametrize("bad_seed", ["nonsense", "", "#12345"])
def test_invalid_seed_raises(bad_seed: str) -> None:
    with pytest.raises(ValueError):
        from_seed(bad_seed)


@pytest.mark.parametrize("bad_level", [-1.5, 1.5, 2.0])
def test_out_of_range_contrast_level_raises(bad_level: float) -> None:
    with pytest.raises(ValueError):
        from_seed(BASELINE_SEED, contrast_level=bad_level)
