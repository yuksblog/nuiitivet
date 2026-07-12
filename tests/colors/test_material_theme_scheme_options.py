"""MaterialThemeFactory must forward variant/contrast_level to palette generation."""

from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.theme.material_theme import MaterialThemeFactory
from nuiitivet.material.theme.scheme_variant import SchemeVariant
from nuiitivet.material.theme.theme_data import MaterialThemeData

SEED = "#6750A4"


def _primary(theme) -> str:
    material = theme.extension(MaterialThemeData)
    assert material is not None
    primary = material.roles.get(ColorRole.PRIMARY)
    assert isinstance(primary, str)
    return primary.lower()


def test_factory_defaults_to_m3_reference() -> None:
    assert _primary(MaterialThemeFactory.light(SEED)) == "#65558f"


def test_light_and_dark_honor_variant() -> None:
    assert _primary(MaterialThemeFactory.light(SEED, variant=SchemeVariant.VIBRANT)) == "#6f19ff"
    assert _primary(MaterialThemeFactory.dark(SEED, variant=SchemeVariant.VIBRANT)) != "#cfbdfe"


def test_from_seed_pair_honors_contrast_level() -> None:
    default_light, _ = MaterialThemeFactory.from_seed_pair(SEED)
    high_light, _ = MaterialThemeFactory.from_seed_pair(SEED, contrast_level=1.0)
    assert _primary(default_light) != _primary(high_light)
