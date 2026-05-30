import pytest

from nuiitivet.material import Fab, Button
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.theme.elevation import md3_elevation_to_shadow


def test_resolve_overlay_defaults():
    b = Button(label="lbl", style=ButtonStyle.filled())
    # Default filled style has overlay_alpha=0.08 (from ButtonStyle.filled)
    # resolve_button_style_params sets:
    # pressed_opacity = base_alpha (0.08)
    # hover_opacity = base_alpha * 0.5 (0.04)

    # FilledButton resolves the default filled style at initialization time.
    assert abs(b._PRESS_OPACITY - 0.08) < 1e-6
    assert abs(b._HOVER_OPACITY - 0.04) < 1e-6


@pytest.mark.parametrize(
    ("factory", "expected_pressed", "expected_hover"),
    [
        (lambda: Button(label="lbl", style=ButtonStyle.filled()), 0.08, 0.04),
        (lambda: Button(label="lbl", style=ButtonStyle.outlined()), 0.08, 0.04),
        (lambda: Button(label="lbl", style=ButtonStyle.tonal()), 0.08, 0.04),
        (lambda: Fab(icon="add"), 0.1, 0.08),
        (lambda: Button(label="lbl", style=ButtonStyle.text()), 0.08, 0.04),
        (lambda: Button(label="lbl", style=ButtonStyle.elevated()), 0.08, 0.04),
    ],
)
def test_resolve_overlay_defaults_for_variants(factory, expected_pressed: float, expected_hover: float):
    b = factory()
    assert abs(b._PRESS_OPACITY - expected_pressed) < 1e-6
    assert abs(b._HOVER_OPACITY - expected_hover) < 1e-6


def test_fab_focus_opacity_matches_md3_spec() -> None:
    fab = Fab(icon="add")

    fab.state.focused = True

    assert abs(fab._get_state_layer_target_opacity() - 0.1) < 1e-6


def test_fab_hover_elevation_matches_md3_spec() -> None:
    fab = Fab(icon="add")
    enabled = md3_elevation_to_shadow(3)
    hovered = md3_elevation_to_shadow(4)

    assert fab.shadow_color == enabled.color
    assert fab.shadow_offset == enabled.offset
    assert fab.shadow_blur == enabled.sigma

    fab.state.hovered = True
    fab._sync_state_tokens()

    assert fab.shadow_color == hovered.color
    assert fab.shadow_offset == hovered.offset
    assert fab.shadow_blur == hovered.sigma

    fab.state.hovered = False
    fab.state.focused = True
    fab._sync_state_tokens()

    assert fab.shadow_color == enabled.color
    assert fab.shadow_offset == enabled.offset
    assert fab.shadow_blur == enabled.sigma


def test_resolve_overlay_with_style_alpha_scaled():
    style = ButtonStyle(
        background="#ffffff",
        foreground="#000000",
        elevation=0,
        border_color=None,
        border_width=0.0,
        corner_radius=8,
        padding=(4, 4, 4, 4),
        min_width=0,
        min_height=0,
        overlay_color="#112233",
        overlay_alpha=0.2,
    )
    b = Button(label="lbl", style=style)

    # Check that params were correctly passed to ButtonBase
    assert b.state_layer_color == "#112233"
    assert abs(b._PRESS_OPACITY - 0.2) < 1e-06
    assert abs(b._HOVER_OPACITY - 0.1) < 1e-06
