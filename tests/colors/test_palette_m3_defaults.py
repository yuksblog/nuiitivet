"""Pin the generated palette to the Material 3 reference scheme.

MCU's `theme_from_color` defaults to `Variant.VIBRANT` at contrast 0.25, which is
not the M3 default. These tests fail if we ever stop passing variant/contrast
explicitly and silently inherit MCU's defaults again.
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
    light, dark = from_seed(BASELINE_SEED)
    for role, expected in BASELINE_LIGHT.items():
        assert light[role].lower() == expected, f"light {role.name}"
    for role, expected in BASELINE_DARK.items():
        assert dark[role].lower() == expected, f"dark {role.name}"


def test_default_scheme_is_not_mcu_vibrant_default() -> None:
    """Guard the specific regression: MCU's own default produced #5700d2."""
    light, _ = from_seed(BASELINE_SEED)
    assert light[ColorRole.PRIMARY].lower() != "#5700d2"


def test_every_color_role_is_populated() -> None:
    light, dark = from_seed(BASELINE_SEED)
    assert set(light) == set(ColorRole)
    assert set(dark) == set(ColorRole)


def test_on_background_falls_back_to_on_surface() -> None:
    """M3 folded `onBackground` into `onSurface`; MCU no longer emits it."""
    light, _ = from_seed(BASELINE_SEED)
    assert light[ColorRole.ON_BACKGROUND] == light[ColorRole.ON_SURFACE]


def test_variant_is_honored() -> None:
    tonal, _ = from_seed(BASELINE_SEED, variant=SchemeVariant.TONAL_SPOT)
    vibrant, _ = from_seed(BASELINE_SEED, variant=SchemeVariant.VIBRANT)
    assert tonal[ColorRole.PRIMARY] != vibrant[ColorRole.PRIMARY]


def test_contrast_level_is_honored() -> None:
    """Raising contrast must darken primary against a light surface."""
    from nuiitivet.colors.utils import contrast_ratio

    low, _ = from_seed(BASELINE_SEED, contrast_level=0.0)
    high, _ = from_seed(BASELINE_SEED, contrast_level=1.0)

    low_ratio = contrast_ratio(low[ColorRole.PRIMARY], low[ColorRole.SURFACE])
    high_ratio = contrast_ratio(high[ColorRole.PRIMARY], high[ColorRole.SURFACE])
    assert high_ratio > low_ratio


def test_seed_accepts_css_name_and_short_hex() -> None:
    from_short, _ = from_seed("#00F")
    from_long, _ = from_seed("#0000FF")
    assert from_short == from_long

    named, _ = from_seed("rebeccapurple")
    assert named[ColorRole.PRIMARY].startswith("#")


@pytest.mark.parametrize("bad_seed", ["nonsense", "", "#12345"])
def test_invalid_seed_raises(bad_seed: str) -> None:
    with pytest.raises(ValueError):
        from_seed(bad_seed)


@pytest.mark.parametrize("bad_level", [-1.5, 1.5, 2.0])
def test_out_of_range_contrast_level_raises(bad_level: float) -> None:
    with pytest.raises(ValueError):
        from_seed(BASELINE_SEED, contrast_level=bad_level)
