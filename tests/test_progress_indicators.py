"""Tests for progress indicator widgets."""

from dataclasses import replace
import math
from typing import Any

from nuiitivet.observable import Observable
from nuiitivet.material import (
    CircularProgressIndicator,
    IndeterminateCircularProgressIndicator,
    IndeterminateLinearProgressIndicator,
    LinearProgressIndicator,
)
from nuiitivet.material.styles import CircularProgressIndicatorStyle, LinearProgressIndicatorStyle
from nuiitivet.material.theme.material_theme import MaterialTheme
from nuiitivet.material.theme.theme_data import MaterialThemeData
from nuiitivet.theme import manager


def test_linear_progress_value_clamped():
    p = LinearProgressIndicator(value=2.5)
    assert p.value == 1.0

    p.value = -1.0
    assert p.value == 0.0


def test_circular_progress_value_clamped():
    p = CircularProgressIndicator(value=-2.0)
    assert p.value == 0.0

    p.value = 3.0
    assert p.value == 1.0


def test_determinate_progress_supports_observable_value():
    value = Observable(0.1)
    linear = LinearProgressIndicator(value=value)
    circular = CircularProgressIndicator(value=value)

    linear.on_mount()
    circular.on_mount()
    try:
        assert linear.value == 0.1
        assert circular.value == 0.1

        value.value = 0.8

        assert linear.value == 0.8
        assert circular.value == 0.8
    finally:
        linear.on_unmount()
        circular.on_unmount()


def test_progress_supports_observable_disabled():
    disabled = Observable(False)
    p = LinearProgressIndicator(value=0.5, disabled=disabled)

    p.on_mount()
    try:
        assert p.disabled is False
        disabled.value = True
        assert p.disabled is True
    finally:
        p.on_unmount()


def test_indeterminate_api_has_no_value_parameter():
    linear = IndeterminateLinearProgressIndicator()
    circular = IndeterminateCircularProgressIndicator()

    assert not hasattr(linear, "value")
    assert not hasattr(circular, "value")


def test_progress_widgets_resolve_theme_styles():
    light, _ = MaterialTheme.from_seed_pair("#6750A4")
    mat = light.extension(MaterialThemeData)
    assert mat is not None

    custom_linear = LinearProgressIndicatorStyle.default().copy_with(track_thickness=7.0)
    custom_circular = CircularProgressIndicatorStyle.default().copy_with(track_thickness=6.0)

    custom_theme = replace(
        light,
        extensions=[
            mat.copy_with(
                _linear_progress_indicator_style=custom_linear,
                _circular_progress_indicator_style=custom_circular,
            )
        ],
    )

    old_theme = manager.current
    try:
        manager.set_theme(custom_theme)

        linear = LinearProgressIndicator(value=0.5)
        circular = CircularProgressIndicator(value=0.5)

        assert linear.style.track_thickness == 7.0
        assert circular.style.track_thickness == 6.0
    finally:
        manager.set_theme(old_theme)


def test_circular_progress_uses_style_size_when_size_is_omitted():
    style = CircularProgressIndicatorStyle.default().copy_with(size=52.0)

    determinate = CircularProgressIndicator(value=0.5, style=style)
    indeterminate = IndeterminateCircularProgressIndicator(style=style)

    assert determinate.preferred_size() == (52, 52)
    assert indeterminate.preferred_size() == (52, 52)


def test_circular_progress_explicit_size_overrides_style_size():
    style = CircularProgressIndicatorStyle.default().copy_with(size=52.0)

    determinate = CircularProgressIndicator(value=0.5, size=40, style=style)
    indeterminate = IndeterminateCircularProgressIndicator(size=40, style=style)

    assert determinate.preferred_size() == (40, 40)
    assert indeterminate.preferred_size() == (40, 40)


class _CanvasCapture:
    def __init__(self) -> None:
        self.arcs: list[tuple[float, float]] = []

    def drawArc(self, _rect: Any, start: float, sweep: float, _use_center: bool, _paint: Any) -> None:
        self.arcs.append((start, sweep))


def test_linear_determinate_track_active_space_keeps_100_percent_full_width(monkeypatch):
    from nuiitivet.material import progress_indicators as mod

    draws: list[tuple[float, float, float, float]] = []

    monkeypatch.setattr(mod, "make_paint", lambda **_kwargs: object())
    monkeypatch.setattr(mod, "make_rect", lambda x, y, w, h: (x, y, w, h))
    monkeypatch.setattr(mod, "draw_round_rect", lambda _c, rect, _r, _p: draws.append(rect))

    style = LinearProgressIndicatorStyle.default().copy_with(track_active_space=4.0)
    widget = LinearProgressIndicator(value=1.0, width=100, style=style)
    widget.paint(canvas=object(), x=0, y=0, width=100, height=4)

    # At 100%, only active segment is rendered and must span full width.
    assert len(draws) == 1
    assert draws[0][2] == 100.0


def test_circular_determinate_track_active_space_keeps_100_percent_full_sweep(monkeypatch):
    from nuiitivet.material import progress_indicators as mod

    monkeypatch.setattr(mod, "make_paint", lambda **_kwargs: object())
    monkeypatch.setattr(mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    canvas = _CanvasCapture()
    style = CircularProgressIndicatorStyle.default().copy_with(track_active_space=4.0)
    widget = CircularProgressIndicator(value=1.0, size=40, style=style)
    widget.paint(canvas=canvas, x=0, y=0, width=40, height=40)

    assert canvas.arcs
    # Determinate progress at 100% should render a full circle.
    assert canvas.arcs[-1][1] == 360.0


def test_linear_determinate_track_active_space_creates_boundary_gap(monkeypatch):
    from nuiitivet.material import progress_indicators as mod

    draws: list[tuple[float, float, float, float]] = []

    monkeypatch.setattr(mod, "make_paint", lambda **_kwargs: object())
    monkeypatch.setattr(mod, "make_rect", lambda x, y, w, h: (x, y, w, h))
    monkeypatch.setattr(mod, "draw_round_rect", lambda _c, rect, _r, _p: draws.append(rect))

    style = LinearProgressIndicatorStyle.default().copy_with(track_active_space=4.0)
    widget = LinearProgressIndicator(value=0.5, width=100, style=style)
    widget.paint(canvas=object(), x=0, y=0, width=100, height=4)

    # Active and remaining track are rendered as separate segments with a gap.
    assert len(draws) >= 2
    active = draws[0]
    remaining = draws[1]
    active_end = active[0] + active[2]
    remaining_start = remaining[0]
    assert (remaining_start - active_end) == 4.0


def test_circular_determinate_track_active_space_creates_boundary_gap(monkeypatch):
    from nuiitivet.material import progress_indicators as mod

    monkeypatch.setattr(mod, "make_paint", lambda **_kwargs: object())
    monkeypatch.setattr(mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    canvas = _CanvasCapture()
    style = CircularProgressIndicatorStyle.default().copy_with(track_active_space=4.0)
    widget = CircularProgressIndicator(value=0.5, size=40, style=style)
    widget.paint(canvas=canvas, x=0, y=0, width=40, height=40)

    # Active and remaining track are split into two arcs.
    assert len(canvas.arcs) == 2
    active_sweep = canvas.arcs[0][1]
    track_sweep = canvas.arcs[1][1]
    assert active_sweep < 180.0
    assert track_sweep < 180.0


def test_circular_determinate_gap_compensates_round_stroke_caps(monkeypatch):
    from nuiitivet.material import progress_indicators as mod

    monkeypatch.setattr(mod, "make_paint", lambda **_kwargs: object())
    monkeypatch.setattr(mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    canvas = _CanvasCapture()
    style = CircularProgressIndicatorStyle.default().copy_with(track_active_space=4.0, track_thickness=4.0)
    widget = CircularProgressIndicator(value=0.5, size=40, style=style)
    widget.paint(canvas=canvas, x=0, y=0, width=40, height=40)

    assert len(canvas.arcs) == 2
    active_sweep = canvas.arcs[0][1]
    track_sweep = canvas.arcs[1][1]
    actual_gap_deg = 360.0 - (active_sweep + track_sweep)

    radius = (40.0 - 4.0) / 2.0
    circumference = 2.0 * math.pi * radius
    expected_gap_deg = ((4.0 + 4.0) / circumference) * 360.0

    # Determinate circular now keeps one gap at each boundary (2 total).
    assert math.isclose(actual_gap_deg, expected_gap_deg * 2.0, rel_tol=0.0, abs_tol=1e-6)


def test_circular_determinate_keeps_gap_at_start_point(monkeypatch):
    from nuiitivet.material import progress_indicators as mod

    monkeypatch.setattr(mod, "make_paint", lambda **_kwargs: object())
    monkeypatch.setattr(mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    canvas = _CanvasCapture()
    style = CircularProgressIndicatorStyle.default().copy_with(track_active_space=4.0, track_thickness=4.0)
    widget = CircularProgressIndicator(value=0.5, size=40, style=style)
    widget.paint(canvas=canvas, x=0, y=0, width=40, height=40)

    assert len(canvas.arcs) == 2
    active_start, active_sweep = canvas.arcs[0]
    track_start, track_sweep = canvas.arcs[1]

    radius = (40.0 - 4.0) / 2.0
    circumference = 2.0 * math.pi * radius
    expected_gap_deg = ((4.0 + 4.0) / circumference) * 360.0

    # Gap at active->track boundary.
    active_end = active_start + active_sweep
    gap_boundary = (track_start - active_end) % 360.0
    # Gap at start point (track end -> active start).
    track_end = track_start + track_sweep
    gap_at_start = (active_start - track_end) % 360.0

    assert math.isclose(gap_boundary, expected_gap_deg, rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(gap_at_start, expected_gap_deg, rel_tol=0.0, abs_tol=1e-6)


def test_circular_determinate_uses_round_stroke_caps(monkeypatch):
    from nuiitivet.material import progress_indicators as mod

    paint_calls: list[dict[str, Any]] = []

    def _capture_make_paint(**kwargs: Any) -> object:
        paint_calls.append(kwargs)
        return object()

    monkeypatch.setattr(mod, "make_paint", _capture_make_paint)
    monkeypatch.setattr(mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    canvas = _CanvasCapture()
    widget = CircularProgressIndicator(value=0.5, size=40)
    widget.paint(canvas=canvas, x=0, y=0, width=40, height=40)

    stroke_calls = [call for call in paint_calls if call.get("style") == "stroke"]
    assert len(stroke_calls) == 2
    assert all(call.get("stroke_cap") == "round" for call in stroke_calls)


def test_indeterminate_circular_uses_round_stroke_caps(monkeypatch):
    from nuiitivet.material import progress_indicators as mod

    paint_calls: list[dict[str, Any]] = []

    def _capture_make_paint(**kwargs: Any) -> object:
        paint_calls.append(kwargs)
        return object()

    monkeypatch.setattr(mod, "make_paint", _capture_make_paint)
    monkeypatch.setattr(mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    canvas = _CanvasCapture()
    widget = IndeterminateCircularProgressIndicator(size=40)
    widget.paint(canvas=canvas, x=0, y=0, width=40, height=40)

    stroke_calls = [call for call in paint_calls if call.get("style") == "stroke"]
    assert len(stroke_calls) == 2
    assert all(call.get("stroke_cap") == "round" for call in stroke_calls)


def test_indeterminate_linear_uses_jetpack_cycle_duration():
    widget = IndeterminateLinearProgressIndicator()
    assert widget._animation_motion_duration() == 1.75


def test_indeterminate_linear_head_tail_match_jetpack_reference_over_full_cycle():
    from nuiitivet.material import progress_indicators as mod

    duration = int(mod._LINEAR_ANIMATION_DURATION_MS)

    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _cubic_bezier_transform(t: float, x1: float, y1: float, x2: float, y2: float) -> float:
        t = _clamp01(t)
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0

        def sample_x(u: float) -> float:
            return ((3.0 * x1 - 3.0 * x2 + 1.0) * u * u * u) + ((3.0 * x2 - 6.0 * x1) * u * u) + ((3.0 * x1) * u)

        def sample_y(u: float) -> float:
            return ((3.0 * y1 - 3.0 * y2 + 1.0) * u * u * u) + ((3.0 * y2 - 6.0 * y1) * u * u) + ((3.0 * y1) * u)

        def sample_dx(u: float) -> float:
            return ((9.0 * x1 - 9.0 * x2 + 3.0) * u * u) + ((6.0 * x2 - 12.0 * x1) * u) + (3.0 * x1)

        u = t
        for _ in range(8):
            x = sample_x(u) - t
            dx = sample_dx(u)
            if abs(dx) < 1e-6:
                break
            u = _clamp01(u - (x / dx))

        if abs(sample_x(u) - t) > 1e-5:
            low = 0.0
            high = 1.0
            u = t
            for _ in range(12):
                x = sample_x(u)
                if x < t:
                    low = u
                else:
                    high = u
                u = (low + high) * 0.5

        return sample_y(u)

    def _keyframe_fraction(time_ms: float, *, delay_ms: float, duration_ms: float) -> float:
        if time_ms <= delay_ms:
            return 0.0
        end_ms = delay_ms + duration_ms
        if time_ms >= end_ms:
            return 1.0
        local = _clamp01((time_ms - delay_ms) / max(duration_ms, 1e-9))
        return _cubic_bezier_transform(local, 0.3, 0.0, 0.8, 0.15)

    def _expected(time_ms: float) -> tuple[float, float, float, float]:
        t = float(time_ms) % mod._LINEAR_ANIMATION_DURATION_MS
        first_head = _keyframe_fraction(
            t,
            delay_ms=mod._LINEAR_FIRST_HEAD_DELAY_MS,
            duration_ms=mod._LINEAR_FIRST_HEAD_DURATION_MS,
        )
        first_tail = _keyframe_fraction(
            t,
            delay_ms=mod._LINEAR_FIRST_TAIL_DELAY_MS,
            duration_ms=mod._LINEAR_FIRST_TAIL_DURATION_MS,
        )
        second_head = _keyframe_fraction(
            t,
            delay_ms=mod._LINEAR_SECOND_HEAD_DELAY_MS,
            duration_ms=mod._LINEAR_SECOND_HEAD_DURATION_MS,
        )
        second_tail = _keyframe_fraction(
            t,
            delay_ms=mod._LINEAR_SECOND_TAIL_DELAY_MS,
            duration_ms=mod._LINEAR_SECOND_TAIL_DURATION_MS,
        )
        return (first_head, first_tail, second_head, second_tail)

    # Check all integer ms in a full cycle to ensure shape and timing match Jetpack reference.
    for t in range(duration):
        actual = mod._linear_indeterminate_segment_fractions(float(t))
        expected = _expected(float(t))
        assert math.isclose(actual[0], expected[0], rel_tol=0.0, abs_tol=1e-6)
        assert math.isclose(actual[1], expected[1], rel_tol=0.0, abs_tol=1e-6)
        assert math.isclose(actual[2], expected[2], rel_tol=0.0, abs_tol=1e-6)
        assert math.isclose(actual[3], expected[3], rel_tol=0.0, abs_tol=1e-6)


def test_indeterminate_circular_uses_jetpack_cycle_duration():
    widget = IndeterminateCircularProgressIndicator()
    assert widget._animation_motion_duration() == 6.0


def test_indeterminate_circular_head_angle_does_not_reverse_within_cycle():
    from nuiitivet.material import progress_indicators as mod

    duration = int(mod._CIRCULAR_ANIMATION_DURATION_MS)

    def _head_degrees(time_ms: float) -> float:
        rotation = (time_ms / mod._CIRCULAR_ANIMATION_DURATION_MS) * mod._CIRCULAR_GLOBAL_ROTATION_DEGREES_TARGET
        rotation += mod._circular_additional_rotation_degrees(time_ms)
        return rotation + (mod._circular_progress_fraction(time_ms) * 360.0)

    # Exclude the cycle wrap frame and verify forward motion within one cycle.
    for t in range(duration - 1):
        assert _head_degrees(float(t + 1)) >= _head_degrees(float(t))


def test_indeterminate_circular_head_tail_match_jetpack_reference_over_full_cycle():
    from nuiitivet.material import progress_indicators as mod

    duration = int(mod._CIRCULAR_ANIMATION_DURATION_MS)

    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _cubic_bezier_transform(t: float, x1: float, y1: float, x2: float, y2: float) -> float:
        t = _clamp01(t)
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0

        def sample_x(u: float) -> float:
            return ((3.0 * x1 - 3.0 * x2 + 1.0) * u * u * u) + ((3.0 * x2 - 6.0 * x1) * u * u) + ((3.0 * x1) * u)

        def sample_y(u: float) -> float:
            return ((3.0 * y1 - 3.0 * y2 + 1.0) * u * u * u) + ((3.0 * y2 - 6.0 * y1) * u * u) + ((3.0 * y1) * u)

        def sample_dx(u: float) -> float:
            return ((9.0 * x1 - 9.0 * x2 + 3.0) * u * u) + ((6.0 * x2 - 12.0 * x1) * u) + (3.0 * x1)

        u = t
        for _ in range(8):
            x = sample_x(u) - t
            dx = sample_dx(u)
            if abs(dx) < 1e-6:
                break
            u = _clamp01(u - (x / dx))

        if abs(sample_x(u) - t) > 1e-5:
            low = 0.0
            high = 1.0
            u = t
            for _ in range(12):
                x = sample_x(u)
                if x < t:
                    low = u
                else:
                    high = u
                u = (low + high) * 0.5

        return sample_y(u)

    def _jetpack_additional_rotation_degrees(time_ms: float) -> float:
        t = float(time_ms) % mod._CIRCULAR_ANIMATION_DURATION_MS

        def decelerate(v: float) -> float:
            return _cubic_bezier_transform(v, 0.05, 0.7, 0.1, 1.0)

        # Mirrors ProgressIndicator.kt keyframes (material3).
        points = (
            (0.0, 0.0, "hold"),
            (300.0, 90.0, "decelerate"),
            (1500.0, 90.0, "hold"),
            (1800.0, 180.0, "linear"),
            (3000.0, 180.0, "hold"),
            (3300.0, 270.0, "linear"),
            (4500.0, 270.0, "hold"),
            (4800.0, 360.0, "linear"),
            (6000.0, 360.0, "hold"),
        )

        for i in range(len(points) - 1):
            start_t, start_v, _ = points[i]
            end_t, end_v, mode = points[i + 1]
            if t <= end_t:
                if mode == "hold" or end_t <= start_t:
                    return start_v
                local = _clamp01((t - start_t) / (end_t - start_t))
                if mode == "decelerate":
                    local = decelerate(local)
                return start_v + ((end_v - start_v) * local)
        return 360.0

    def _jetpack_progress_fraction(time_ms: float) -> float:
        t = float(time_ms) % mod._CIRCULAR_ANIMATION_DURATION_MS
        half = mod._CIRCULAR_ANIMATION_DURATION_MS / 2.0

        def standard(v: float) -> float:
            return _cubic_bezier_transform(v, 0.2, 0.0, 0.0, 1.0)

        if t <= half:
            local = _clamp01(t / max(half, 1e-9))
            return mod._CIRCULAR_INDETERMINATE_MIN_PROGRESS + (
                (mod._CIRCULAR_INDETERMINATE_MAX_PROGRESS - mod._CIRCULAR_INDETERMINATE_MIN_PROGRESS) * standard(local)
            )

        # Return leg is linear in Jetpack keyframes.
        local = _clamp01((t - half) / max(half, 1e-9))
        return mod._CIRCULAR_INDETERMINATE_MAX_PROGRESS + (
            (mod._CIRCULAR_INDETERMINATE_MIN_PROGRESS - mod._CIRCULAR_INDETERMINATE_MAX_PROGRESS) * local
        )

    def _actual_tail(time_ms: float) -> float:
        rotation = (float(time_ms) / mod._CIRCULAR_ANIMATION_DURATION_MS) * mod._CIRCULAR_GLOBAL_ROTATION_DEGREES_TARGET
        return rotation + mod._circular_additional_rotation_degrees(float(time_ms))

    def _actual_head(time_ms: float) -> float:
        return _actual_tail(float(time_ms)) + (mod._circular_progress_fraction(float(time_ms)) * 360.0)

    def _expected_tail(time_ms: float) -> float:
        rotation = (float(time_ms) / mod._CIRCULAR_ANIMATION_DURATION_MS) * mod._CIRCULAR_GLOBAL_ROTATION_DEGREES_TARGET
        return rotation + _jetpack_additional_rotation_degrees(float(time_ms))

    def _expected_head(time_ms: float) -> float:
        return _expected_tail(float(time_ms)) + (_jetpack_progress_fraction(float(time_ms)) * 360.0)

    # Check all integer ms in a full cycle to ensure shape and timing match Jetpack reference.
    for t in range(duration):
        assert math.isclose(_actual_tail(float(t)), _expected_tail(float(t)), rel_tol=0.0, abs_tol=1e-4)
        assert math.isclose(_actual_head(float(t)), _expected_head(float(t)), rel_tol=0.0, abs_tol=1e-4)
