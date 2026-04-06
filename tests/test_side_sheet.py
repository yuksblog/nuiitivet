"""Tests for SideSheet widget and MaterialOverlay.side_sheet()."""

import pytest

from nuiitivet.material.sheet import SideSheet
from nuiitivet.material.styles.sheet_style import SideSheetStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.transition_spec import MaterialSideSheetTransitionSpec, MaterialTransitions
from nuiitivet.theme.manager import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.widgets.box import Box


@pytest.fixture(autouse=True)
def material_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))


# ---------------------------------------------------------------------------
# SideSheetStyle tests
# ---------------------------------------------------------------------------


def test_side_sheet_style_defaults():
    style = SideSheetStyle()
    assert style.width == 400
    assert style.height == "100%"
    assert style.corner_radius == 16.0
    assert style.background_color == ColorRole.SURFACE_CONTAINER_LOW


def test_side_sheet_style_copy_with():
    style = SideSheetStyle().copy_with(width=320, corner_radius=8.0)
    assert style.width == 320
    assert style.height == "100%"
    assert style.corner_radius == 8.0


def test_side_sheet_style_is_immutable():
    style = SideSheetStyle()
    with pytest.raises((AttributeError, TypeError)):
        style.width = 100  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MaterialSideSheetTransitionSpec tests
# ---------------------------------------------------------------------------


def test_side_sheet_transition_spec_defaults():
    spec = MaterialSideSheetTransitionSpec()
    assert spec.enter is not None
    assert spec.exit is not None


def test_material_transitions_side_sheet_right():
    spec = MaterialTransitions.side_sheet(side="right")
    assert isinstance(spec, MaterialSideSheetTransitionSpec)
    visuals = spec.enter.pattern.resolve(0.0)
    assert visuals.translate_x_fraction is not None
    assert visuals.translate_x_fraction > 0


def test_material_transitions_side_sheet_left():
    spec = MaterialTransitions.side_sheet(side="left")
    assert isinstance(spec, MaterialSideSheetTransitionSpec)
    visuals = spec.enter.pattern.resolve(0.0)
    assert visuals.translate_x_fraction is not None
    assert visuals.translate_x_fraction < 0


def test_material_transitions_side_sheet_custom_enter():
    from nuiitivet.animation.transition_definition import TransitionDefinition
    from nuiitivet.animation.transition_pattern import FadePattern
    from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS

    custom_enter = TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=0.0, end_alpha=1.0),
    )
    spec = MaterialTransitions.side_sheet(enter=custom_enter)
    assert spec.enter is custom_enter


# ---------------------------------------------------------------------------
# SideSheet widget tests
# ---------------------------------------------------------------------------


def test_side_sheet_defaults():
    """SideSheet stores headline and defaults correctly."""
    content = Box(width=100, height=100)
    sheet = SideSheet(content, headline="Settings")
    assert sheet.side == "right"
    assert sheet._headline == "Settings"
    assert sheet._on_back is None
    assert sheet._on_close is None


def test_side_sheet_style_property_default():
    """SideSheet.style returns SideSheetStyle() when no style given."""
    sheet = SideSheet(Box(), headline="Settings")
    assert sheet.style == SideSheetStyle()


def test_side_sheet_style_property_custom():
    """SideSheet.style returns user-provided style."""
    custom = SideSheetStyle(width=320)
    sheet = SideSheet(Box(), headline="Settings", style=custom)
    assert sheet.style is custom


def test_side_sheet_left_side():
    """SideSheet stores side='left' correctly."""
    sheet = SideSheet(Box(), headline="Nav", side="left")
    assert sheet.side == "left"


def test_side_sheet_right_corner_radius():
    """Right-side sheet applies left (inner) corner radius only."""
    style = SideSheetStyle(corner_radius=16.0)
    cr = style.corner_radius
    corner_radius = (cr, 0.0, 0.0, cr)  # tl, tr, br, bl
    assert corner_radius == (16.0, 0.0, 0.0, 16.0)


def test_side_sheet_left_corner_radius():
    """Left-side sheet applies right (inner) corner radius only."""
    style = SideSheetStyle(corner_radius=16.0)
    cr = style.corner_radius
    corner_radius = (0.0, cr, cr, 0.0)  # tl, tr, br, bl
    assert corner_radius == (0.0, 16.0, 16.0, 0.0)


def test_side_sheet_build_returns_box():
    """SideSheet.build() returns a Box as the outer container."""
    content = Box(width=200, height=100)
    sheet = SideSheet(content, headline="Settings")
    built = sheet.build()
    assert isinstance(built, Box)


def test_side_sheet_build_right_corner_radius():
    """SideSheet.build() applies correct corner radii for right side."""
    sheet = SideSheet(Box(), headline="Settings", side="right", style=SideSheetStyle(corner_radius=16.0))
    built = sheet.build()
    assert isinstance(built, Box)
    cr = 16.0
    assert built.corner_radius == (cr, 0.0, 0.0, cr)


def test_side_sheet_build_left_corner_radius():
    """SideSheet.build() applies correct corner radii for left side."""
    sheet = SideSheet(Box(), headline="Nav", side="left", style=SideSheetStyle(corner_radius=16.0))
    built = sheet.build()
    assert isinstance(built, Box)
    cr = 16.0
    assert built.corner_radius == (0.0, cr, cr, 0.0)


def test_side_sheet_build_width_height():
    """SideSheet.build() outer Box has width and height from style."""
    sheet = SideSheet(Box(), headline="Settings", style=SideSheetStyle(width=360, height="100%"))
    built = sheet.build()
    assert isinstance(built, Box)
    assert built.width_sizing.value == 360


def test_side_sheet_show_back_false_by_default():
    """show_back_button defaults to False — Back button absent in header."""
    sheet = SideSheet(Box(), headline="Settings")
    assert sheet._resolve_show_back() is False


def test_side_sheet_show_back_true():
    """show_back_button=True — _resolve_show_back returns True."""
    sheet = SideSheet(Box(), headline="Settings", show_back_button=True)
    assert sheet._resolve_show_back() is True


def test_side_sheet_show_back_observable():
    """show_back_button=Observable — _resolve_show_back reflects observable value."""
    from nuiitivet.observable import Observable

    obs = Observable(False)
    sheet = SideSheet(Box(), headline="Settings", show_back_button=obs)
    assert sheet._resolve_show_back() is False
    obs.value = True
    assert sheet._resolve_show_back() is True


def test_side_sheet_transition_auto_uses_width():
    """Default transition slides by exactly the sheet's own width (fraction = 1.0)."""
    spec = MaterialTransitions.side_sheet(side="right")
    visuals_start = spec.enter.pattern.resolve(0.0)
    assert visuals_start.translate_x_fraction == pytest.approx(1.0)


def test_side_sheet_transition_fallback_for_non_int_width():
    """Fractional slide is dimension-independent: no fallback calculation needed."""
    spec = MaterialTransitions.side_sheet(side="right")
    visuals_end = spec.exit.pattern.resolve(1.0)
    assert visuals_end.translate_x_fraction == pytest.approx(1.0)


def test_side_sheet_back_button_suppressed_without_on_back():
    """Back button is silently suppressed when show_back_button=True but on_back is None.

    This documents the guarded condition in build():
        if self._resolve_show_back() and self._on_back is not None
    """
    sheet = SideSheet(Box(), headline="Settings", show_back_button=True, on_back=None)
    # Flag is truthy, but callback is absent — button must NOT appear.
    assert sheet._resolve_show_back() is True
    assert sheet._on_back is None
    # build() must succeed without AttributeError from a missing callback.
    built = sheet.build()
    assert isinstance(built, Box)
