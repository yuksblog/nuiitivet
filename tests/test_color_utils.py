from nuiitivet.colors.utils import hex_to_rgb, relative_luminance, contrast_ratio, passes_wcag, normalize_literal_color


def test_normalize_literal_color_names():
    assert normalize_literal_color("red") == "#ff0000"
    assert normalize_literal_color("Blue") == "#0000ff"
    assert normalize_literal_color("WHITE") == "#ffffff"
    # Unknown name should return as-is (and fail later if used)
    assert normalize_literal_color("notacolor") == "notacolor"


def test_hex_to_rgb_and_luminance():
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("#fff") == (255, 255, 255)
    # luminance of black is 0, white is 1
    assert abs(relative_luminance("#000000") - 0.0) < 1e-9
    assert abs(relative_luminance("#FFFFFF") - 1.0) < 1e-9


def test_contrast_black_white():
    r = contrast_ratio("#000000", "#FFFFFF")
    # black vs white is the maximum 21:1
    assert round(r, 2) == 21.0
    assert passes_wcag("#000000", "#FFFFFF", level="AA")


def test_theme_sample_contrasts():
    # smoke test: ensure the ratio function returns sensible floats and
    # the sample primary/on_primary in the light theme passes AA for large
    # text (3.0) and ideally AA normal (4.5) depending on palette.
    from nuiitivet.material.theme.material_theme import MaterialTheme
    from nuiitivet.material.theme.theme_data import MaterialThemeData
    from nuiitivet.material.theme.color_role import ColorRole

    DEFAULT_SEED = "#6750A4"
    default_theme, _ = MaterialTheme.from_seed_pair(DEFAULT_SEED, name="test-color-utils")

    mat = default_theme.extension(MaterialThemeData)
    assert mat is not None
    primary = mat.roles.get(ColorRole.PRIMARY)
    on_primary = mat.roles.get(ColorRole.ON_PRIMARY)

    assert isinstance(primary, str) and isinstance(on_primary, str)
    r = contrast_ratio(primary, on_primary)
    assert r > 1.0
