import pytest

from nuiitivet.material import (
    ElevatedButton,
    FilledButton,
    FilledTonalButton,
    FloatingActionButton,
    OutlinedButton,
    TextButton,
)
from nuiitivet.material.styles.button_style import ButtonStyle


def test_resolve_overlay_defaults():
    b = FilledButton(label="lbl")
    # Default filled style has overlay_alpha=0.08 (from ButtonStyle.filled)
    # resolve_button_style_params sets:
    # pressed_opacity = base_alpha (0.08)
    # hover_opacity = base_alpha * 0.5 (0.04)

    # FilledButton resolves the default filled style at initialization time.
    assert abs(b.pressed_opacity - 0.08) < 1e-6
    assert abs(b.hover_opacity - 0.04) < 1e-6


@pytest.mark.parametrize(
    ("factory", "expected_pressed", "expected_hover"),
    [
        (lambda: FilledButton(label="lbl"), 0.08, 0.04),
        (lambda: OutlinedButton(label="lbl"), 0.08, 0.04),
        (lambda: FilledTonalButton(label="lbl"), 0.08, 0.04),
        (lambda: FloatingActionButton(icon="add"), 0.08, 0.04),
        (lambda: TextButton(label="lbl"), 0.12, 0.06),
        (lambda: ElevatedButton(label="lbl"), 0.06, 0.03),
    ],
)
def test_resolve_overlay_defaults_for_variants(factory, expected_pressed: float, expected_hover: float):
    b = factory()
    assert abs(b.pressed_opacity - expected_pressed) < 1e-6
    assert abs(b.hover_opacity - expected_hover) < 1e-6


def test_resolve_overlay_with_style_alpha_scaled():
    style = ButtonStyle(
        background="#ffffff",
        foreground="#000000",
        elevation=0.0,
        border_color=None,
        border_width=0.0,
        corner_radius=8,
        padding=(4, 4, 4, 4),
        min_width=0,
        min_height=0,
        overlay_color="#112233",
        overlay_alpha=0.2,
    )
    b = FilledButton(label="lbl", style=style)

    # Check that params were correctly passed to ButtonBase
    assert b.overlay_color == "#112233"
    assert abs(b.pressed_opacity - 0.2) < 1e-06
    assert abs(b.hover_opacity - 0.1) < 1e-06
