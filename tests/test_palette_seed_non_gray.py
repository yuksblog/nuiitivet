from nuiitivet.material.theme.palette import from_seed
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.colors.utils import hex_to_rgb


def _is_grayscale(hexv: str) -> bool:
    r, g, b = hex_to_rgb(hexv)
    return r == g == b


def test_seeds_produce_colored_primaries() -> None:
    """Representative seeds should produce non-grayscale primaries.

    This prevents regressions where the HSL fallback collapses to neutral
    outputs for many seeds.
    """
    seeds = ["#6750A4", "#00796B", "#FFC107"]  # purple, teal, amber
    primaries = []
    for seed in seeds:
        light, dark = from_seed(seed)
        primary = light.get(ColorRole.PRIMARY)
        assert primary is not None, f"no primary for seed {seed}"
        assert not _is_grayscale(primary), f"seed {seed} produced grayscale primary {primary}"
        primaries.append(primary)

    # Basic sanity: not all primaries are identical
    assert len(set(primaries)) >= 2
