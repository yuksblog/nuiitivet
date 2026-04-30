"""Material Design 3 progress indicators."""

from __future__ import annotations

import math
from typing import Any, Callable, Tuple, TypeGuard, cast

from nuiitivet.animation import Animatable, LinearMotion
from nuiitivet.observable import ObservableProtocol, runtime
from nuiitivet.rendering.padding import parse_padding
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import draw_round_rect, make_paint, make_rect
from nuiitivet.theme.manager import manager as theme_manager
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.widgeting.widget import Widget

from .styles.progress_indicator_style import (
    CircularProgressIndicatorStyle,
    LinearProgressIndicatorStyle,
)

PaddingArg = Tuple[int, int] | Tuple[int, int, int, int] | int

# Jetpack Compose Material3 indeterminate linear timing specs.
_LINEAR_ANIMATION_DURATION_MS = 1750.0
_LINEAR_FIRST_HEAD_DURATION_MS = 1000.0
_LINEAR_FIRST_TAIL_DURATION_MS = 1000.0
_LINEAR_SECOND_HEAD_DURATION_MS = 850.0
_LINEAR_SECOND_TAIL_DURATION_MS = 850.0
_LINEAR_FIRST_HEAD_DELAY_MS = 0.0
_LINEAR_FIRST_TAIL_DELAY_MS = 250.0
_LINEAR_SECOND_HEAD_DELAY_MS = 650.0
_LINEAR_SECOND_TAIL_DELAY_MS = 900.0

# Jetpack Compose Material3 indeterminate circular timing specs.
_CIRCULAR_ANIMATION_DURATION_MS = 6000.0
_CIRCULAR_ADDITIONAL_ROTATION_DELAY_MS = 1500.0
_CIRCULAR_ADDITIONAL_ROTATION_DURATION_MS = 300.0
_CIRCULAR_ADDITIONAL_ROTATION_DEGREES_TARGET = 360.0
_CIRCULAR_GLOBAL_ROTATION_DEGREES_TARGET = 1080.0
_CIRCULAR_INDETERMINATE_MIN_PROGRESS = 0.1
_CIRCULAR_INDETERMINATE_MAX_PROGRESS = 0.87

# MotionTokens from androidx.compose.material3.tokens.MotionTokens
_EASING_EMPHASIZED_ACCELERATE = (0.3, 0.0, 0.8, 0.15)
_EASING_EMPHASIZED_DECELERATE = (0.05, 0.7, 0.1, 1.0)
_EASING_STANDARD = (0.2, 0.0, 0.0, 1.0)


def _is_observable(value: object) -> TypeGuard[ObservableProtocol[Any]]:
    return hasattr(value, "subscribe") and hasattr(value, "value")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _apply_alpha(rgba: tuple[int, int, int, int], alpha: float) -> tuple[int, int, int, int]:
    r, g, b, a = rgba
    clamped = max(0.0, min(1.0, float(alpha)))
    return (int(r), int(g), int(b), int(round(a * clamped)))


def _resolve_active_track_colors(
    *,
    style: LinearProgressIndicatorStyle | CircularProgressIndicatorStyle,
    disabled: bool,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    """Resolve active/track colors with disabled alpha handling."""
    theme = theme_manager.current

    active = resolve_color_to_rgba(style.active_indicator_color, theme=theme) or (0, 0, 0, 255)
    track = resolve_color_to_rgba(style.track_color, theme=theme) or (0, 0, 0, 255)

    if disabled:
        active = _apply_alpha(active, style.disabled_active_alpha)
        track = _apply_alpha(track, style.disabled_track_alpha)

    return active, track


def _circular_geometry(
    *,
    content_x: int,
    content_y: int,
    content_w: int,
    content_h: int,
    track_thickness: float,
) -> tuple[float, float, float, float]:
    """Return circular indicator center and radius from content bounds."""
    side = float(min(content_w, content_h))
    stroke_w = max(1.0, float(track_thickness))
    radius = max(0.0, (side - stroke_w) / 2.0)
    cx = float(content_x) + (float(content_w) / 2.0)
    cy = float(content_y) + (float(content_h) / 2.0)
    return stroke_w, radius, cx, cy


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
        u -= x / dx
        u = _clamp01(u)

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


def _easing_transform(t: float, cubic: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = cubic
    return _cubic_bezier_transform(t, x1, y1, x2, y2)


def _keyframe_fraction(
    time_ms: float,
    *,
    delay_ms: float,
    duration_ms: float,
    easing: Callable[[float], float],
) -> float:
    if time_ms <= delay_ms:
        return 0.0
    end_ms = delay_ms + duration_ms
    if time_ms >= end_ms:
        return 1.0
    normalized = (time_ms - delay_ms) / max(duration_ms, 1e-9)
    return _clamp01(easing(_clamp01(normalized)))


def _linear_indeterminate_segment_fractions(time_ms: float) -> tuple[float, float, float, float]:
    """Return Jetpack-compatible head/tail fractions for indeterminate linear segments."""
    t = float(time_ms) % _LINEAR_ANIMATION_DURATION_MS

    def easing(value: float) -> float:
        return _easing_transform(value, _EASING_EMPHASIZED_ACCELERATE)

    first_head = _keyframe_fraction(
        t,
        delay_ms=_LINEAR_FIRST_HEAD_DELAY_MS,
        duration_ms=_LINEAR_FIRST_HEAD_DURATION_MS,
        easing=easing,
    )
    first_tail = _keyframe_fraction(
        t,
        delay_ms=_LINEAR_FIRST_TAIL_DELAY_MS,
        duration_ms=_LINEAR_FIRST_TAIL_DURATION_MS,
        easing=easing,
    )
    second_head = _keyframe_fraction(
        t,
        delay_ms=_LINEAR_SECOND_HEAD_DELAY_MS,
        duration_ms=_LINEAR_SECOND_HEAD_DURATION_MS,
        easing=easing,
    )
    second_tail = _keyframe_fraction(
        t,
        delay_ms=_LINEAR_SECOND_TAIL_DELAY_MS,
        duration_ms=_LINEAR_SECOND_TAIL_DURATION_MS,
        easing=easing,
    )
    return (first_head, first_tail, second_head, second_tail)


def _circular_additional_rotation_degrees(time_ms: float) -> float:
    t = time_ms % _CIRCULAR_ANIMATION_DURATION_MS

    def emphasized_decelerate(v: float) -> float:
        return _easing_transform(v, _EASING_EMPHASIZED_DECELERATE)

    points = (
        # Match Jetpack keyframes semantics:
        # - only the first animated leg uses emphasized decelerate easing
        # - remaining animated legs are linear
        # - plateaus are holds
        (0.0, 0.0, "hold"),
        (_CIRCULAR_ADDITIONAL_ROTATION_DURATION_MS, 90.0, "decelerate"),
        (_CIRCULAR_ADDITIONAL_ROTATION_DELAY_MS, 90.0, "hold"),
        (_CIRCULAR_ADDITIONAL_ROTATION_DURATION_MS + _CIRCULAR_ADDITIONAL_ROTATION_DELAY_MS, 180.0, "linear"),
        (_CIRCULAR_ADDITIONAL_ROTATION_DELAY_MS * 2.0, 180.0, "hold"),
        (
            _CIRCULAR_ADDITIONAL_ROTATION_DURATION_MS + (_CIRCULAR_ADDITIONAL_ROTATION_DELAY_MS * 2.0),
            270.0,
            "linear",
        ),
        (_CIRCULAR_ADDITIONAL_ROTATION_DELAY_MS * 3.0, 270.0, "hold"),
        (
            _CIRCULAR_ADDITIONAL_ROTATION_DURATION_MS + (_CIRCULAR_ADDITIONAL_ROTATION_DELAY_MS * 3.0),
            _CIRCULAR_ADDITIONAL_ROTATION_DEGREES_TARGET,
            "linear",
        ),
        (_CIRCULAR_ANIMATION_DURATION_MS, _CIRCULAR_ADDITIONAL_ROTATION_DEGREES_TARGET, "hold"),
    )

    for i in range(len(points) - 1):
        start_t, start_v, _ = points[i]
        end_t, end_v, mode = points[i + 1]
        if t <= end_t:
            if mode == "hold" or end_t <= start_t:
                return start_v
            local = (t - start_t) / (end_t - start_t)
            if mode == "decelerate":
                local = emphasized_decelerate(_clamp01(local))
            else:
                local = _clamp01(local)
            return start_v + (end_v - start_v) * local
    return _CIRCULAR_ADDITIONAL_ROTATION_DEGREES_TARGET


def _circular_progress_fraction(time_ms: float) -> float:
    t = time_ms % _CIRCULAR_ANIMATION_DURATION_MS
    half = _CIRCULAR_ANIMATION_DURATION_MS / 2.0

    def easing(v: float) -> float:
        return _easing_transform(v, _EASING_STANDARD)

    if t <= half:
        local = _clamp01(t / max(half, 1e-9))
        return _CIRCULAR_INDETERMINATE_MIN_PROGRESS + (
            (_CIRCULAR_INDETERMINATE_MAX_PROGRESS - _CIRCULAR_INDETERMINATE_MIN_PROGRESS) * easing(local)
        )

    local = _clamp01((t - half) / max(half, 1e-9))
    # Jetpack keyframes omit easing for the return leg, so keep this linear.
    return _CIRCULAR_INDETERMINATE_MAX_PROGRESS + (
        (_CIRCULAR_INDETERMINATE_MIN_PROGRESS - _CIRCULAR_INDETERMINATE_MAX_PROGRESS) * local
    )


class _ProgressIndicatorBase(Widget):
    """Shared behavior for progress indicator widgets."""

    def __init__(
        self,
        *,
        disabled: bool | ObservableProtocol[bool],
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingArg = 0,
    ) -> None:
        """Initialize shared progress indicator base state.

        Args:
            disabled: Disabled state or observable disabled state.
            width: Width sizing.
            height: Height sizing.
            padding: Padding around the indicator.
        """
        self._disabled_external: ObservableProtocol[bool] | None = None
        if _is_observable(disabled):
            self._disabled_external = cast(ObservableProtocol[bool], disabled)
            self._disabled = bool(self._disabled_external.value)
        else:
            self._disabled = bool(disabled)

        super().__init__(width=width, height=height, padding=padding)

    @property
    def disabled(self) -> bool:
        """Return whether the indicator is disabled."""
        return bool(self._disabled)

    def _sync_disabled_from_external(self) -> None:
        if self._disabled_external is None:
            return
        next_disabled = bool(self._disabled_external.value)
        if next_disabled == self._disabled:
            return
        self._disabled = next_disabled
        self.invalidate()

    def on_mount(self) -> None:
        super().on_mount()
        if self._disabled_external is not None:
            self.observe(self._disabled_external, lambda _v: self._sync_disabled_from_external())
        self._sync_disabled_from_external()


class _DeterminateProgressBase(_ProgressIndicatorBase):
    """Shared behavior for determinate indicators with value state."""

    def __init__(
        self,
        value: float | ObservableProtocol[float],
        *,
        disabled: bool | ObservableProtocol[bool],
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingArg = 0,
    ) -> None:
        """Initialize shared determinate progress indicator state.

        Args:
            value: Progress value or observable progress value.
            disabled: Disabled state or observable disabled state.
            width: Width sizing.
            height: Height sizing.
            padding: Padding around the indicator.
        """
        self._value_external: ObservableProtocol[float] | None = None
        if _is_observable(value):
            self._value_external = cast(ObservableProtocol[float], value)
            self._value = _clamp01(float(self._value_external.value))
        else:
            self._value = _clamp01(float(cast(float, value)))

        super().__init__(
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
        )

    @property
    def value(self) -> float:
        """Return determinate progress value in range [0.0, 1.0]."""
        return float(self._value)

    @value.setter
    def value(self, value: float) -> None:
        next_value = _clamp01(value)
        if abs(next_value - self._value) < 1e-8:
            return
        self._value = next_value
        if self._value_external is not None:
            try:
                self._value_external.value = next_value
            except Exception:
                pass
        self.invalidate()

    def _sync_value_from_external(self) -> None:
        if self._value_external is None:
            return
        next_value = _clamp01(float(self._value_external.value))
        if abs(next_value - self._value) < 1e-8:
            return
        self._value = next_value
        self.invalidate()

    def on_mount(self) -> None:
        super().on_mount()
        if self._value_external is not None:
            self.observe(self._value_external, lambda _v: self._sync_value_from_external())
        self._sync_value_from_external()


class _IndeterminateProgressBase(_ProgressIndicatorBase):
    """Shared behavior for indeterminate indicators with animated phase."""

    def __init__(
        self,
        *,
        disabled: bool | ObservableProtocol[bool],
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingArg = 0,
    ) -> None:
        """Initialize shared indeterminate progress indicator state.

        Args:
            disabled: Disabled state or observable disabled state.
            width: Width sizing.
            height: Height sizing.
            padding: Padding around the indicator.
        """
        super().__init__(disabled=disabled, width=width, height=height, padding=padding)
        if not hasattr(self, "_animation_motion"):
            self._animation_motion = LinearMotion(1.0)
        self._phase_anim: Animatable[float] | None = None
        self._phase_sub: Any = None
        self._phase_timer: Any = None

    @property
    def phase(self) -> float:
        """Return current indeterminate phase."""
        if self._phase_anim is None:
            return 0.0
        return float(self._phase_anim.value)

    def _animation_motion_duration(self) -> float:
        return 0.2

    def _start_phase_loop(self) -> None:
        duration = max(0.01, float(self._animation_motion_duration()))

        if self._phase_anim is None:
            self._phase_anim = Animatable(0.0, motion=self._animation_motion)
            self._phase_anim.target = 1.0

        if self._phase_sub is not None:
            self._phase_sub.dispose()
        self._phase_sub = self._phase_anim.subscribe(lambda _v: self.invalidate())

        if self._phase_timer is not None:
            runtime.clock.unschedule(self._phase_timer)

        def _advance(_dt: float) -> None:
            if not getattr(self, "_app", None):
                self._phase_timer = None
                return
            if self._phase_anim is not None:
                self._phase_anim.target = self._phase_anim.target + 1.0
            runtime.clock.schedule_once(_advance, duration)

        self._phase_timer = _advance
        runtime.clock.schedule_once(_advance, duration)

    def on_mount(self) -> None:
        super().on_mount()
        self._start_phase_loop()

    def on_unmount(self) -> None:
        if self._phase_sub is not None:
            self._phase_sub.dispose()
            self._phase_sub = None
        if self._phase_timer is not None:
            runtime.clock.unschedule(self._phase_timer)
            self._phase_timer = None
        if self._phase_anim is not None:
            self._phase_anim.stop()
            self._phase_anim = None
        super().on_unmount()


class LinearProgressIndicator(_DeterminateProgressBase):
    """Material Design 3 determinate linear progress indicator."""

    def __init__(
        self,
        value: float | ObservableProtocol[float] = 0.0,
        *,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = "1%",
        padding: PaddingArg = 0,
        style: LinearProgressIndicatorStyle | None = None,
    ) -> None:
        """Initialize LinearProgressIndicator.

        Args:
            value: Progress value in range ``[0.0, 1.0]``. Values are clamped.
            disabled: Disabled state.
            width: Width sizing.
            padding: Padding around the indicator.
            style: Optional style override.
        """
        self._style = style
        style_for_layout = style or LinearProgressIndicatorStyle.default()
        track_h = max(1, int(round(style_for_layout.track_thickness)))
        pad_l, pad_t, pad_r, pad_b = parse_padding(padding)
        super().__init__(
            value=value,
            disabled=disabled,
            width=width,
            height=track_h + pad_t + pad_b,
            padding=(pad_l, pad_t, pad_r, pad_b),
        )

    @property
    def style(self) -> LinearProgressIndicatorStyle:
        """Return effective linear progress indicator style."""
        if self._style is not None:
            return self._style
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        mat = theme_manager.current.extension(MaterialThemeData)
        if mat is not None:
            return mat.linear_progress_indicator_style
        return LinearProgressIndicatorStyle.default()

    def preferred_size(self, max_width: int | None = None, max_height: int | None = None) -> tuple[int, int]:
        w_dim = self.width_sizing
        pad_l, pad_t, pad_r, pad_b = self.padding
        track_h = max(1, int(round(self.style.track_thickness)))
        if w_dim.kind == "fixed":
            pref_w = int(w_dim.value)
        else:
            pref_w = int(max_width) if max_width is not None else 0
        pref_h = track_h + pad_t + pad_b
        if max_width is not None:
            pref_w = min(pref_w, int(max_width))
        if max_height is not None:
            pref_h = min(pref_h, int(max_height))
        return (pref_w, pref_h)

    def _resolve_colors(self) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int], tuple[int, int, int, int]]:
        style = self.style
        theme = theme_manager.current

        active = resolve_color_to_rgba(style.active_indicator_color, theme=theme) or (0, 0, 0, 255)
        track = resolve_color_to_rgba(style.track_color, theme=theme) or (0, 0, 0, 255)
        stop = resolve_color_to_rgba(style.stop_indicator_color, theme=theme) or active

        if self.disabled:
            active = _apply_alpha(active, style.disabled_active_alpha)
            track = _apply_alpha(track, style.disabled_track_alpha)
            stop = _apply_alpha(active, style.disabled_active_alpha)

        return active, track, stop

    def paint(self, canvas: Any, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        if canvas is None:
            return

        content_x, content_y, content_w, content_h = self.content_rect(x, y, width, height)
        if content_w <= 0 or content_h <= 0:
            return

        style = self.style
        thickness = max(1.0, float(style.track_thickness))
        track_active_space = max(0.0, float(style.track_active_space))
        track_y = float(content_y) + (float(content_h) - thickness) / 2.0
        radius = thickness / 2.0

        rect_track = make_rect(float(content_x), track_y, float(content_w), thickness)
        if rect_track is None:
            return

        active_rgba, track_rgba, stop_rgba = self._resolve_colors()
        active_paint = make_paint(color=active_rgba, style="fill", aa=True)
        track_paint = make_paint(color=track_rgba, style="fill", aa=True)

        progress_x = float(content_x) + (float(content_w) * self.value)
        gap = 0.0
        if 0.0 < self.value < 1.0:
            gap = min(track_active_space, float(content_w))

        active_end = max(float(content_x), progress_x - (gap / 2.0))
        track_start = min(float(content_x) + float(content_w), progress_x + (gap / 2.0))

        active_w = max(0.0, active_end - float(content_x))
        remaining_w = max(0.0, (float(content_x) + float(content_w)) - track_start)

        if active_w > 0.0 and active_paint is not None:
            rect_active = make_rect(float(content_x), track_y, active_w, thickness)
            if rect_active is not None:
                draw_round_rect(canvas, rect_active, radius, active_paint)

        if remaining_w > 0.0 and track_paint is not None:
            rect_remaining = make_rect(track_start, track_y, remaining_w, thickness)
            if rect_remaining is not None:
                draw_round_rect(canvas, rect_remaining, radius, track_paint)

        stop_size = max(0.0, float(style.stop_indicator_size))
        if stop_size <= 0.0:
            return

        # Stop indicator is anchored to the track's trailing edge.
        stop_x = float(content_x) + float(content_w) - float(style.stop_indicator_trailing_space) - (stop_size / 2.0)
        stop_x = min(
            float(content_x) + float(content_w) - (stop_size / 2.0),
            max(float(content_x) + (stop_size / 2.0), stop_x),
        )
        stop_y = track_y + (thickness / 2.0)

        stop_paint = make_paint(color=stop_rgba, style="fill", aa=True)
        if stop_paint is None:
            return

        if hasattr(canvas, "drawCircle"):
            canvas.drawCircle(float(stop_x), float(stop_y), stop_size / 2.0, stop_paint)
            return

        oval_rect = make_rect(
            float(stop_x) - (stop_size / 2.0),
            float(stop_y) - (stop_size / 2.0),
            stop_size,
            stop_size,
        )
        if oval_rect is not None and hasattr(canvas, "drawOval"):
            canvas.drawOval(oval_rect, stop_paint)


class IndeterminateLinearProgressIndicator(_IndeterminateProgressBase):
    """Material Design 3 indeterminate linear progress indicator."""

    def __init__(
        self,
        *,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = "1%",
        padding: PaddingArg = 0,
        style: LinearProgressIndicatorStyle | None = None,
    ) -> None:
        """Initialize IndeterminateLinearProgressIndicator.

        Args:
            disabled: Disabled state.
            width: Width sizing.
            padding: Padding around the indicator.
            style: Optional style override.
        """
        self._style = style
        style_for_layout = style or LinearProgressIndicatorStyle.default()
        self._animation_motion = LinearMotion(self._animation_motion_duration())
        track_h = max(1, int(round(style_for_layout.track_thickness)))
        pad_l, pad_t, pad_r, pad_b = parse_padding(padding)
        super().__init__(
            disabled=disabled,
            width=width,
            height=track_h + pad_t + pad_b,
            padding=(pad_l, pad_t, pad_r, pad_b),
        )

    @property
    def style(self) -> LinearProgressIndicatorStyle:
        """Return effective linear progress indicator style."""
        if self._style is not None:
            return self._style
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        mat = theme_manager.current.extension(MaterialThemeData)
        if mat is not None:
            return mat.linear_progress_indicator_style
        return LinearProgressIndicatorStyle.default()

    def preferred_size(self, max_width: int | None = None, max_height: int | None = None) -> tuple[int, int]:
        w_dim = self.width_sizing
        pad_l, pad_t, pad_r, pad_b = self.padding
        track_h = max(1, int(round(self.style.track_thickness)))
        if w_dim.kind == "fixed":
            pref_w = int(w_dim.value)
        else:
            pref_w = int(max_width) if max_width is not None else 0
        pref_h = track_h + pad_t + pad_b
        if max_width is not None:
            pref_w = min(pref_w, int(max_width))
        if max_height is not None:
            pref_h = min(pref_h, int(max_height))
        return (pref_w, pref_h)

    def _animation_motion_duration(self) -> float:
        return _LINEAR_ANIMATION_DURATION_MS / 1000.0

    def _resolve_colors(self) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
        return _resolve_active_track_colors(style=self.style, disabled=self.disabled)

    def paint(self, canvas: Any, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        if canvas is None:
            return

        content_x, content_y, content_w, content_h = self.content_rect(x, y, width, height)
        if content_w <= 0 or content_h <= 0:
            return

        style = self.style
        thickness = max(1.0, float(style.track_thickness))
        track_active_space = max(0.0, float(style.track_active_space))
        track_y = float(content_y) + (float(content_h) - thickness) / 2.0
        radius = thickness / 2.0

        rect_track = make_rect(float(content_x), track_y, float(content_w), thickness)
        if rect_track is None:
            return

        active_rgba, track_rgba = self._resolve_colors()

        track_paint = make_paint(color=track_rgba, style="fill", aa=True)
        if track_paint is not None:
            draw_round_rect(canvas, rect_track, radius, track_paint)

        active_min_x = float(content_x) + (track_active_space / 2.0)
        active_w = max(0.0, float(content_w) - track_active_space)
        if active_w <= 0.0:
            return

        phase = self.phase % 1.0
        time_ms = phase * _LINEAR_ANIMATION_DURATION_MS
        first_head, first_tail, second_head, second_tail = _linear_indeterminate_segment_fractions(time_ms)

        active_paint = make_paint(color=active_rgba, style="fill", aa=True)
        if active_paint is None:
            return

        def draw_segment(start_fraction: float, end_fraction: float) -> None:
            start = _clamp01(start_fraction)
            end = _clamp01(end_fraction)
            if end <= start:
                return

            start_x = active_min_x + (active_w * start)
            end_x = active_min_x + (active_w * end)
            rect_active = make_rect(start_x, track_y, end_x - start_x, thickness)
            if rect_active is not None:
                draw_round_rect(canvas, rect_active, radius, active_paint)

        draw_segment(first_tail, first_head)
        draw_segment(second_tail, second_head)


class CircularProgressIndicator(_DeterminateProgressBase):
    """Material Design 3 determinate circular progress indicator."""

    def __init__(
        self,
        value: float | ObservableProtocol[float] = 0.0,
        *,
        disabled: bool | ObservableProtocol[bool] = False,
        size: int | None = None,
        padding: PaddingArg = 0,
        style: CircularProgressIndicatorStyle | None = None,
    ) -> None:
        """Initialize CircularProgressIndicator.

        Args:
            value: Progress value in range ``[0.0, 1.0]``. Values are clamped.
            disabled: Disabled state.
            size: Outer indicator size in dp. Uses style default when omitted.
            padding: Padding around the indicator.
            style: Optional style override.
        """
        self._style = style
        style_for_layout = style or CircularProgressIndicatorStyle.default()
        self._size = int(size) if size is not None else max(1, int(round(style_for_layout.size)))
        pad_l, pad_t, pad_r, pad_b = parse_padding(padding)
        super().__init__(
            value=value,
            disabled=disabled,
            width=self._size + pad_l + pad_r,
            height=self._size + pad_t + pad_b,
            padding=(pad_l, pad_t, pad_r, pad_b),
        )

    @property
    def style(self) -> CircularProgressIndicatorStyle:
        """Return effective circular progress indicator style."""
        if self._style is not None:
            return self._style
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        mat = theme_manager.current.extension(MaterialThemeData)
        if mat is not None:
            return mat.circular_progress_indicator_style
        return CircularProgressIndicatorStyle.default()

    def _resolve_colors(self) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
        return _resolve_active_track_colors(style=self.style, disabled=self.disabled)

    def preferred_size(self, max_width: int | None = None, max_height: int | None = None) -> tuple[int, int]:
        pad_l, pad_t, pad_r, pad_b = self.padding
        w = self._size + pad_l + pad_r
        h = self._size + pad_t + pad_b
        if max_width is not None:
            w = min(w, int(max_width))
        if max_height is not None:
            h = min(h, int(max_height))
        return (w, h)

    def paint(self, canvas: Any, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        if canvas is None:
            return

        content_x, content_y, content_w, content_h = self.content_rect(x, y, width, height)
        if content_w <= 0 or content_h <= 0:
            return

        style = self.style
        stroke_w, radius, cx, cy = _circular_geometry(
            content_x=content_x,
            content_y=content_y,
            content_w=content_w,
            content_h=content_h,
            track_thickness=float(style.track_thickness),
        )
        track_active_space = max(0.0, float(style.track_active_space))

        active_rgba, track_rgba = self._resolve_colors()
        active_paint = make_paint(color=active_rgba, style="stroke", stroke_width=stroke_w, aa=True, stroke_cap="round")
        track_paint = make_paint(color=track_rgba, style="stroke", stroke_width=stroke_w, aa=True, stroke_cap="round")
        if active_paint is None and track_paint is None:
            return

        progress_sweep = max(0.0, min(360.0, 360.0 * self.value))
        gap_deg = 0.0
        if 0.0 < self.value < 1.0 and radius > 0.0 and track_active_space > 0.0:
            # Round stroke caps consume approximately one stroke width at the
            # active/track boundary. Compensate so the visible gap remains close
            # to the MD3 track_active_space token.
            adjusted_gap = track_active_space + stroke_w
            circumference = 2.0 * math.pi * radius
            if circumference > 0.0:
                gap_deg = min(360.0, (adjusted_gap / circumference) * 360.0)

        active_start = -90.0
        active_sweep = progress_sweep
        track_start = -90.0 + progress_sweep
        track_sweep = max(0.0, 360.0 - progress_sweep)
        if 0.0 < self.value < 1.0 and gap_deg > 0.0:
            # Keep an explicit gap at both active/track boundaries.
            active_start += gap_deg / 2.0
            active_sweep = max(0.0, progress_sweep - gap_deg)
            track_start += gap_deg / 2.0
            track_sweep = max(0.0, 360.0 - progress_sweep - gap_deg)

        arc_rect = make_rect(
            cx - radius,
            cy - radius,
            radius * 2.0,
            radius * 2.0,
        )
        if arc_rect is None:
            return

        if hasattr(canvas, "drawArc"):
            if active_paint is not None and active_sweep > 0.0:
                canvas.drawArc(arc_rect, active_start, active_sweep, False, active_paint)
            if track_paint is not None and track_sweep > 0.0:
                canvas.drawArc(arc_rect, track_start, track_sweep, False, track_paint)
            return

        # Fallback: draw full circle only when complete if arc API is unavailable.
        if self.value >= 1.0 and active_paint is not None and hasattr(canvas, "drawCircle"):
            canvas.drawCircle(cx, cy, radius, active_paint)
        elif track_paint is not None and hasattr(canvas, "drawCircle"):
            canvas.drawCircle(cx, cy, radius, track_paint)


class IndeterminateCircularProgressIndicator(_IndeterminateProgressBase):
    """Material Design 3 indeterminate circular progress indicator."""

    def __init__(
        self,
        *,
        disabled: bool | ObservableProtocol[bool] = False,
        size: int | None = None,
        padding: PaddingArg = 0,
        style: CircularProgressIndicatorStyle | None = None,
    ) -> None:
        """Initialize IndeterminateCircularProgressIndicator.

        Args:
            disabled: Disabled state.
            size: Outer indicator size in dp. Uses style default when omitted.
            padding: Padding around the indicator.
            style: Optional style override.
        """
        self._style = style
        style_for_motion = style or CircularProgressIndicatorStyle.default()
        self._size = int(size) if size is not None else max(1, int(round(style_for_motion.size)))
        self._animation_motion = LinearMotion(self._animation_motion_duration())
        pad_l, pad_t, pad_r, pad_b = parse_padding(padding)
        super().__init__(
            disabled=disabled,
            width=self._size + pad_l + pad_r,
            height=self._size + pad_t + pad_b,
            padding=(pad_l, pad_t, pad_r, pad_b),
        )

    @property
    def style(self) -> CircularProgressIndicatorStyle:
        """Return effective circular progress indicator style."""
        if self._style is not None:
            return self._style
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        mat = theme_manager.current.extension(MaterialThemeData)
        if mat is not None:
            return mat.circular_progress_indicator_style
        return CircularProgressIndicatorStyle.default()

    def _animation_motion_duration(self) -> float:
        return _CIRCULAR_ANIMATION_DURATION_MS / 1000.0

    def preferred_size(self, max_width: int | None = None, max_height: int | None = None) -> tuple[int, int]:
        pad_l, pad_t, pad_r, pad_b = self.padding
        w = self._size + pad_l + pad_r
        h = self._size + pad_t + pad_b
        if max_width is not None:
            w = min(w, int(max_width))
        if max_height is not None:
            h = min(h, int(max_height))
        return (w, h)

    def _resolve_colors(self) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
        return _resolve_active_track_colors(style=self.style, disabled=self.disabled)

    def paint(self, canvas: Any, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        if canvas is None:
            return

        content_x, content_y, content_w, content_h = self.content_rect(x, y, width, height)
        if content_w <= 0 or content_h <= 0:
            return

        style = self.style
        stroke_w, radius, cx, cy = _circular_geometry(
            content_x=content_x,
            content_y=content_y,
            content_w=content_w,
            content_h=content_h,
            track_thickness=float(style.track_thickness),
        )
        track_active_space = max(0.0, float(style.track_active_space))

        active_rgba, track_rgba = self._resolve_colors()

        active_paint = make_paint(color=active_rgba, style="stroke", stroke_width=stroke_w, aa=True, stroke_cap="round")
        track_paint = make_paint(color=track_rgba, style="stroke", stroke_width=stroke_w, aa=True, stroke_cap="round")
        if active_paint is None and track_paint is None:
            return

        phase = self.phase % 1.0
        time_ms = phase * _CIRCULAR_ANIMATION_DURATION_MS
        global_rotation = (time_ms / _CIRCULAR_ANIMATION_DURATION_MS) * _CIRCULAR_GLOBAL_ROTATION_DEGREES_TARGET
        additional_rotation = _circular_additional_rotation_degrees(time_ms)
        sweep = _circular_progress_fraction(time_ms) * 360.0
        gap_deg = 0.0
        if radius > 0.0 and track_active_space > 0.0:
            adjusted_gap = track_active_space + stroke_w
            gap_deg = min(360.0, (adjusted_gap / (2.0 * math.pi * radius)) * 360.0)

        gap_sweep = min(sweep, gap_deg)
        rotation = global_rotation + additional_rotation
        track_start = rotation + sweep + gap_sweep
        track_sweep = max(0.0, 360.0 - sweep - (gap_sweep * 2.0))

        arc_rect = make_rect(
            cx - radius,
            cy - radius,
            radius * 2.0,
            radius * 2.0,
        )
        if arc_rect is None:
            return

        if hasattr(canvas, "drawArc"):
            if track_paint is not None and track_sweep > 0.0:
                canvas.drawArc(arc_rect, track_start, track_sweep, False, track_paint)
            if active_paint is not None and sweep > 0.0:
                canvas.drawArc(arc_rect, rotation, sweep, False, active_paint)


__all__ = [
    "LinearProgressIndicator",
    "IndeterminateLinearProgressIndicator",
    "CircularProgressIndicator",
    "IndeterminateCircularProgressIndicator",
]
