"""Tests for wiring TypeScaleToken weight/tracking into the Skia text path.

These exercise the font helpers directly (measurement, typeface weight
resolution, positioned blob) and the Text widget's paint cache key.
"""

import pytest

from nuiitivet.rendering.skia import (
    get_typeface,
    make_font,
    make_text_blob,
    measure_text_ink_bounds,
    measure_text_width,
)
from nuiitivet.rendering.skia.font import _clear_typeface_caches_for_tests
from nuiitivet.rendering.skia.skia_module import get_skia

skia = get_skia(raise_if_missing=False)
pytestmark = pytest.mark.skipif(skia is None, reason="skia backend not available")


def _typeface(weight: int = 400):
    return get_typeface(
        family_candidates=("DejaVu Sans", "Arial", "Helvetica", "Liberation Sans"),
        fallback_to_default=True,
        weight=weight,
    )


class TestTrackingMeasurement:
    def test_positive_tracking_widens_measured_width(self) -> None:
        tf = _typeface()
        text = "Hello"
        base = measure_text_width(tf, 16.0, text, 0.0)
        tracked = measure_text_width(tf, 16.0, text, 2.0)
        assert tracked > base

    def test_negative_tracking_narrows_measured_width(self) -> None:
        tf = _typeface()
        text = "Hello"
        base = measure_text_width(tf, 16.0, text, 0.0)
        tracked = measure_text_width(tf, 16.0, text, -1.0)
        assert tracked < base

    def test_tracking_added_once_per_glyph(self) -> None:
        tf = _typeface()
        text = "Hello"  # 5 glyphs for a Latin font
        base = measure_text_width(tf, 16.0, text, 0.0)
        tracking = 3.0
        tracked = measure_text_width(tf, 16.0, text, tracking)
        assert tracked == pytest.approx(base + tracking * len(text))

    def test_ink_bounds_right_edge_grows_with_tracking(self) -> None:
        tf = _typeface()
        text = "Hello"
        _, _, base_right, _ = measure_text_ink_bounds(tf, 16.0, text, 0.0)
        _, _, tracked_right, _ = measure_text_ink_bounds(tf, 16.0, text, 2.0)
        assert tracked_right > base_right


class TestWeightResolution:
    def setup_method(self) -> None:
        _clear_typeface_caches_for_tests()

    def test_weight_is_part_of_typeface_cache_key(self) -> None:
        from nuiitivet.rendering.skia.font import _TYPEFACE_CACHE

        _TYPEFACE_CACHE.clear()
        _typeface(weight=400)
        _typeface(weight=700)
        weights = {key[-1] for key in _TYPEFACE_CACHE if isinstance(key, tuple)}
        assert {400, 700} <= weights

    def test_requested_weight_reflected_when_available(self) -> None:
        # System font managers pick the nearest available weight; assert the
        # bold request lands at least as heavy as the regular one.
        tf_regular = _typeface(weight=400)
        tf_bold = _typeface(weight=900)
        if tf_regular is None or tf_bold is None:
            pytest.skip("no system typeface resolved")
        w_regular = tf_regular.fontStyle().weight()
        w_bold = tf_bold.fontStyle().weight()
        assert w_bold >= w_regular


class TestTrackedBlob:
    def test_tracked_blob_is_built(self) -> None:
        tf = _typeface()
        font = make_font(tf, 16.0)
        assert font is not None
        blob = make_text_blob("Hello", font, tracking=2.0)
        assert blob is not None

    def test_zero_tracking_still_builds_blob(self) -> None:
        tf = _typeface()
        font = make_font(tf, 16.0)
        assert font is not None
        blob = make_text_blob("Hello", font, tracking=0.0)
        assert blob is not None


class TestPaintCacheKey:
    def test_tracking_changes_preferred_width(self) -> None:
        from nuiitivet.widgets.text import TextBase
        from nuiitivet.theme.type_scale import TypeScaleToken

        base_token = TypeScaleToken(font_size=16, line_height=24, weight=400, tracking=0.0)
        tracked_token = base_token.copy_with(tracking=4.0)

        w_base = TextBase("Hello world", type_scale=base_token).preferred_size()[0]
        w_tracked = TextBase("Hello world", type_scale=tracked_token).preferred_size()[0]
        assert w_tracked > w_base
