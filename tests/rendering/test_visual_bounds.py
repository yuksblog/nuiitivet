from nuiitivet.rendering.visual_bounds import transformed_outsets


def test_identity_has_no_outsets() -> None:
    assert transformed_outsets(100, 50) == (0, 0, 0, 0)


def test_translation_moves_one_edge_per_axis() -> None:
    assert transformed_outsets(100, 50, translate=(30, -10)) == (0, 10, 30, 0)


def test_scale_grows_about_the_centre_by_default() -> None:
    assert transformed_outsets(100, 50, scale=(2, 2)) == (50, 25, 50, 25)


def test_scale_about_the_origin_grows_one_way() -> None:
    assert transformed_outsets(100, 50, scale=(2, 1), origin=(0, 0)) == (0, 0, 100, 0)


def test_rotation_rounds_outwards() -> None:
    # A 100px square turned 45 degrees spans 141px; the overhang per side is 20.7.
    assert transformed_outsets(100, 100, rotation=45) == (21, 21, 21, 21)


def test_shrinking_never_reports_negative_outsets() -> None:
    assert transformed_outsets(100, 50, scale=(0.5, 0.5)) == (0, 0, 0, 0)
