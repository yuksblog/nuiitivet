"""Tests for BottomSheet widget and MaterialOverlay.bottom_sheet()."""

import pytest

from nuiitivet.material.sheet import BottomSheet
from nuiitivet.material.styles.sheet_style import BottomSheetStyle
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.material.transition_spec import MaterialBottomSheetTransitionSpec, MaterialTransitions
from nuiitivet.theme.manager import manager
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.widgets.box import Box


@pytest.fixture(autouse=True)
def material_theme():
    manager.set_theme(MaterialTheme.light("#6750A4"))


# ---------------------------------------------------------------------------
# BottomSheetStyle tests
# ---------------------------------------------------------------------------


def test_bottom_sheet_style_defaults():
    style = BottomSheetStyle()
    assert style.width == "100%"
    assert style.height is None
    assert style.corner_radius == 28.0
    assert style.background_color == ColorRole.SURFACE_CONTAINER_LOW


def test_bottom_sheet_style_copy_with():
    style = BottomSheetStyle().copy_with(height=480, corner_radius=20.0)
    assert style.width == "100%"
    assert style.height == 480
    assert style.corner_radius == 20.0


def test_bottom_sheet_style_is_immutable():
    style = BottomSheetStyle()
    with pytest.raises((AttributeError, TypeError)):
        style.height = 200  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MaterialBottomSheetTransitionSpec tests
# ---------------------------------------------------------------------------


def test_bottom_sheet_transition_spec_defaults():
    spec = MaterialBottomSheetTransitionSpec()
    assert spec.enter is not None
    assert spec.exit is not None


def test_material_transitions_bottom_sheet():
    spec = MaterialTransitions.bottom_sheet()
    assert isinstance(spec, MaterialBottomSheetTransitionSpec)
    # Enter pattern should slide from positive y fraction (bottom)
    visuals = spec.enter.pattern.resolve(0.0)
    assert visuals.translate_y_fraction is not None
    assert visuals.translate_y_fraction > 0


def test_material_transitions_bottom_sheet_exit_direction():
    spec = MaterialTransitions.bottom_sheet()
    # Exit pattern should slide to positive y fraction (back down)
    visuals_start = spec.exit.pattern.resolve(0.0)
    visuals_end = spec.exit.pattern.resolve(1.0)
    assert visuals_start.translate_y_fraction == pytest.approx(0.0)
    assert visuals_end.translate_y_fraction == pytest.approx(1.0)


def test_material_transitions_bottom_sheet_custom_exit():
    from nuiitivet.animation.transition_definition import TransitionDefinition
    from nuiitivet.animation.transition_pattern import FadePattern
    from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS

    custom_exit = TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=1.0, end_alpha=0.0),
    )
    spec = MaterialTransitions.bottom_sheet(exit=custom_exit)
    assert spec.exit is custom_exit


# ---------------------------------------------------------------------------
# MaterialOverlay.bottom_sheet() API tests
# ---------------------------------------------------------------------------


def test_bottom_sheet_defaults():
    """BottomSheet stores headline and defaults correctly."""
    content = Box(width=200, height=100)
    sheet = BottomSheet(content, headline="Filters")
    assert sheet._headline == "Filters"
    assert sheet._on_close is None


def test_bottom_sheet_style_property_default():
    """BottomSheet.style returns BottomSheetStyle() when no style given."""
    sheet = BottomSheet(Box(), headline="Filters")
    assert sheet.style == BottomSheetStyle()


def test_bottom_sheet_style_property_custom():
    """BottomSheet.style returns user-provided style."""
    custom = BottomSheetStyle(height=400)
    sheet = BottomSheet(Box(), headline="Filters", style=custom)
    assert sheet.style is custom


def test_bottom_sheet_build_returns_box():
    """BottomSheet.build() returns a Box as the outer container."""
    sheet = BottomSheet(Box(), headline="Filters")
    built = sheet.build()
    assert isinstance(built, Box)


def test_bottom_sheet_top_corner_radius():
    """BottomSheet.build() rounds only the top corners."""
    sheet = BottomSheet(Box(), headline="Filters", style=BottomSheetStyle(corner_radius=28.0))
    built = sheet.build()
    assert isinstance(built, Box)
    cr = 28.0
    assert built.corner_radius == (cr, cr, 0.0, 0.0)


def test_bottom_sheet_build_width():
    """BottomSheet.build() outer Box has full width from style."""
    sheet = BottomSheet(Box(), headline="Filters", style=BottomSheetStyle(width="100%"))
    built = sheet.build()
    assert isinstance(built, Box)


def test_bottom_sheet_transition_auto_uses_height():
    """Default transition slides by exactly the sheet's own height (fraction = 1.0)."""
    spec = MaterialTransitions.bottom_sheet()
    visuals_start = spec.enter.pattern.resolve(0.0)
    assert visuals_start.translate_y_fraction == pytest.approx(1.0)


def test_bottom_sheet_transition_fallback_for_none_height():
    """Fractional slide is dimension-independent: works regardless of height value."""
    spec = MaterialTransitions.bottom_sheet()
    visuals_end = spec.exit.pattern.resolve(1.0)
    assert visuals_end.translate_y_fraction == pytest.approx(1.0)


def test_bottom_sheet_transition_fallback_for_string_height():
    """Fractional slide works even when height is '50%' or content-driven."""
    spec = MaterialTransitions.bottom_sheet()
    visuals_mid = spec.enter.pattern.resolve(0.5)
    assert visuals_mid.translate_y_fraction == pytest.approx(0.5)


def test_bottom_sheet_resolve_on_close_uses_explicit_callback():
    """Explicit on_close takes precedence over the injected overlay handle."""
    calls = []
    sheet = BottomSheet(Box(), headline="Filters", on_close=lambda: calls.append("explicit"))

    class _FakeHandle:
        def close(self, value=None) -> None:
            calls.append("handle")

        def done(self) -> bool:
            return False

    sheet._set_overlay_handle(_FakeHandle())  # type: ignore[arg-type]
    handler = sheet._resolve_on_close()
    assert handler is not None
    handler()
    assert calls == ["explicit"]


def test_bottom_sheet_resolve_on_close_uses_overlay_handle():
    """Without explicit on_close, falls back to overlay_handle.close(None)."""
    closed = []

    class _FakeHandle:
        def close(self, value=None) -> None:
            closed.append(value)

        def done(self) -> bool:
            return False

    sheet = BottomSheet(Box(), headline="Filters")
    sheet._set_overlay_handle(_FakeHandle())  # type: ignore[arg-type]
    handler = sheet._resolve_on_close()
    assert handler is not None
    handler()
    assert closed == [None]


def test_bottom_sheet_resolve_on_close_returns_none_when_standalone():
    """No on_close, no overlay handle → close button stays inert."""
    sheet = BottomSheet(Box(), headline="Filters")
    assert sheet._resolve_on_close() is None
