"""Material loading indicator (M3 Expressive).

This is a Skia-based implementation that morphs between a sequence of shapes.
"""

from __future__ import annotations

import logging
from math import cos, pi, sin
from typing import Any, List, Optional, Sequence, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia import get_skia, make_paint, make_path, rgba_to_skia_color
from nuiitivet.theme.manager import manager as theme_manager
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.widget_animation import AnimationHandleLike

from .shapes import (
    MaterialShapeId,
    Point,
    lerp_points,
    sample_shape_points,
)
from .styles.loading_indicator_style import LoadingIndicatorStyle


logger = logging.getLogger(__name__)

# Implementation detail: number of points to sample per shape
_SAMPLE_POINTS = 96


def _ease_in_out_sine(t: float) -> float:
    tt = max(0.0, min(1.0, float(t)))
    return 0.5 - 0.5 * cos(pi * tt)


class ShapeMorphSequence:
    """A looping shape morph sequence."""

    def __init__(
        self,
        shape_ids: Sequence[MaterialShapeId],
    ) -> None:
        if len(shape_ids) < 2:
            raise ValueError("shape_ids must have at least two items")
        self._shape_ids = tuple(shape_ids)
        self._cache: dict[MaterialShapeId, List[Point]] = {}

    @property
    def shape_ids(self) -> Tuple[MaterialShapeId, ...]:
        return self._shape_ids

    def _points_for(self, shape_id: MaterialShapeId) -> List[Point]:
        pts = self._cache.get(shape_id)
        if pts is not None:
            return pts
        pts = sample_shape_points(shape_id, n_points=_SAMPLE_POINTS)
        self._cache[shape_id] = pts
        return pts

    def points_at(self, phase: float) -> List[Point]:
        """Return interpolated points for phase in [0,1)."""

        p = float(phase)
        p = p % 1.0
        count = len(self._shape_ids)
        seg_f = p * count
        seg = int(seg_f) % count
        t = seg_f - int(seg_f)

        a_id = self._shape_ids[seg]
        b_id = self._shape_ids[(seg + 1) % count]

        # A slight easing makes the morph feel less robotic.
        eased_t = _ease_in_out_sine(t)
        return lerp_points(self._points_for(a_id), self._points_for(b_id), eased_t)


class LoadingIndicator(Widget):
    """M3 Expressive loading indicator.

    This widget is intended for short, indeterminate waits.

    Args:
        size: Outer size of the indicator (default 48). Sets both width and height.
        style: Style configuration for appearance and animation.
        padding: Padding around the indicator.
    """

    def __init__(
        self,
        *,
        size: int = 48,
        padding: Optional[Tuple[int, int, int, int] | Tuple[int, int] | int] = 0,
        style: Optional[LoadingIndicatorStyle] = None,
    ) -> None:
        """Initialize the LoadingIndicator.

        Args:
            size: Outer size of the indicator (default 48).
            padding: Padding around the indicator.
            style: Style configuration for appearance and animation.
        """
        super().__init__(width=int(size), height=int(size), padding=padding)
        self._size = int(size)
        self._user_style = style

        self._phase = 0.0
        self._loop_anim: AnimationHandleLike | None = None
        self._path: Any = None

    @property
    def style(self) -> LoadingIndicatorStyle:
        """Get effective style (user style or theme default)."""
        if self._user_style is not None:
            return self._user_style

        return LoadingIndicatorStyle.from_theme(theme_manager.current, "default")

    def _get_model(self) -> ShapeMorphSequence:
        """Get shape morph sequence from current style."""
        shapes = self.style.shapes
        if not shapes:
            from .shapes import DEFAULT_LOADING_INDICATOR_SEQUENCE

            shapes = DEFAULT_LOADING_INDICATOR_SEQUENCE
        return ShapeMorphSequence(shapes)

    def preferred_size(self, max_width: int | None = None, max_height: int | None = None) -> tuple[int, int]:
        size = int(self._size)
        if max_width is not None:
            size = min(size, int(max_width))
        if max_height is not None:
            size = min(size, int(max_height))
        return (size, size)

    def on_mount(self) -> None:
        super().on_mount()
        self._start_loop()

    def on_unmount(self) -> None:
        try:
            if self._loop_anim is not None:
                self._loop_anim.cancel()
        except Exception:
            exception_once(logger, "loading_indicator_cancel_exc", "LoadingIndicator animation cancel raised")
        self._loop_anim = None
        super().on_unmount()

    def _start_loop(self) -> None:
        if self._loop_anim is not None and getattr(self._loop_anim, "is_running", False):
            return

        cycle_duration = self.style.cycle_duration

        def _apply(progress: float) -> None:
            self._phase = float(progress)
            self.invalidate()

        def _restart() -> None:
            self._loop_anim = None
            # Restart if still mounted.
            if getattr(self, "_app", None) is not None:
                self._start_loop()

        try:
            self._loop_anim = self.animate(
                duration=max(0.1, cycle_duration),
                on_update=_apply,
                easing=lambda t: t,
                on_complete=_restart,
            )
        except Exception:
            exception_once(logger, "loading_indicator_start_anim_exc", "LoadingIndicator animation start raised")
            self._loop_anim = None

    def _resolve_indicator_color(self) -> int | Any:
        """Resolve indicator foreground color to skia color or RGBA tuple."""
        try:
            theme = theme_manager.current
            from nuiitivet.theme.resolver import resolve_color_to_rgba

            foreground = self.style.foreground
            rgba = resolve_color_to_rgba(foreground, theme=theme)
            return rgba_to_skia_color(rgba)
        except Exception:
            exception_once(logger, "loading_indicator_resolve_color_exc", "LoadingIndicator color resolution failed")
            return rgba_to_skia_color((0, 0, 0, 255))

    def _reset_path(self) -> Any | None:
        if self._path is None:
            self._path = make_path()
        path = self._path
        if path is None:
            return None
        reset = getattr(path, "reset", None) or getattr(path, "rewind", None)
        if callable(reset):
            try:
                reset()
            except Exception:
                pass
        else:
            # Fallback: create a new Path if we can't reset.
            self._path = make_path()
        return self._path

    def paint(self, canvas: Any, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        if canvas is None:
            return

        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return

        path = self._reset_path()
        if path is None:
            return

        # Layout: 48dp container with a 38dp active indicator (M3 spec). We keep
        # the ratio and allow scaling with the widget size.
        size = min(int(width), int(height))
        if size <= 0:
            return

        active_ratio = self.style.active_size_ratio
        active = size * float(active_ratio)

        cx = float(x) + float(width) / 2.0
        cy = float(y) + float(height) / 2.0
        radius = float(active) / 2.0

        model = self._get_model()
        points = model.points_at(self._phase)

        # Rotation: clockwise, with a quarter-turn offset to feel less static.
        ang = (self._phase * 2.0 * pi) + (pi / 2.0)
        ca = cos(ang)
        sa = sin(ang)

        transformed: List[Tuple[float, float]] = []
        for px, py in points:
            rx = (px * ca - py * sa) * radius + cx
            ry = (px * sa + py * ca) * radius + cy
            transformed.append((rx, ry))

        if not transformed:
            return

        _path_add_smooth_closed(path, transformed)

        try:
            color = self._resolve_indicator_color()
            paint = make_paint(color=color, style="fill", aa=True)
        except Exception:
            exception_once(logger, "loading_indicator_make_paint_exc", "LoadingIndicator make_paint raised")
            return

        if paint is None:
            return

        try:
            canvas.drawPath(path, paint)
        except Exception:
            exception_once(logger, "loading_indicator_draw_path_exc", "LoadingIndicator drawPath raised")


def _path_add_smooth_closed(path, points: Sequence[Tuple[float, float]]) -> None:
    """Draw a smooth closed curve through points.

    Uses cubic Beziers when available, otherwise falls back to straight lines.
    """

    move_to = getattr(path, "moveTo", None)
    line_to = getattr(path, "lineTo", None)
    cubic_to = getattr(path, "cubicTo", None)
    close = getattr(path, "close", None)

    if not callable(move_to) or not callable(line_to):
        return

    n = len(points)
    if n < 3:
        return

    # Catmull-Rom to Bezier conversion.
    if callable(cubic_to):
        tension = 0.5

        def p(i: int) -> Tuple[float, float]:
            return points[i % n]

        x0, y0 = p(0)
        move_to(float(x0), float(y0))

        for i in range(n):
            x1, y1 = p(i)
            x2, y2 = p(i + 1)
            x0, y0 = p(i - 1)
            x3, y3 = p(i + 2)

            c1x = x1 + (x2 - x0) * tension / 6.0
            c1y = y1 + (y2 - y0) * tension / 6.0
            c2x = x2 - (x3 - x1) * tension / 6.0
            c2y = y2 - (y3 - y1) * tension / 6.0

            cubic_to(float(c1x), float(c1y), float(c2x), float(c2y), float(x2), float(y2))

        if callable(close):
            close()
        return

    # Fallback: polygon.
    x0, y0 = points[0]
    move_to(float(x0), float(y0))
    for x, y in points[1:]:
        line_to(float(x), float(y))
    if callable(close):
        close()
