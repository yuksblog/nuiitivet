"""Material loading indicator (M3 Expressive).

This is a Skia-based implementation that morphs between a sequence of shapes.
"""

from __future__ import annotations

import logging
from math import cos, pi, sin
from typing import Any, List, Optional, Sequence, Tuple

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia import get_skia, make_paint, make_path, rgba_to_skia_color
from nuiitivet.animation import Animatable
from nuiitivet.observable import runtime
from nuiitivet.theme.manager import manager as theme_manager
from nuiitivet.widgeting.widget import Widget

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
        """Return interpolated points for phase in [0, inf).

        Each integer step in phase represents one full shape transition.
        """
        p = float(phase)
        count = len(self._shape_ids)

        # seg is the shape index (A->B, B->C, ...)
        seg = int(p) % count
        # t is the progress within the transition (0.0 to 1.0)
        t = p - int(p)

        a_id = self._shape_ids[seg]
        b_id = self._shape_ids[(seg + 1) % count]

        # Note: We rely on the driving animation to handle easing.
        # So here we use linear interpolation of points based on t.
        return lerp_points(self._points_for(a_id), self._points_for(b_id), t)


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

        self._phase_anim: Animatable[float] | None = None
        self._anim_sub: Any = None
        self._loop_timer: Any = None
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
        if self._anim_sub is not None:
            self._anim_sub.dispose()
            self._anim_sub = None
        if self._loop_timer is not None:
            runtime.clock.unschedule(self._loop_timer)
            self._loop_timer = None
        if self._phase_anim is not None:
            self._phase_anim.stop()
            self._phase_anim = None
        super().on_unmount()

    def _start_loop(self) -> None:
        motion = self.style.motion
        # Duration for one shape transition (A->B)
        duration = getattr(motion, "duration", 0.2)

        # Start from 0.0
        self._phase_anim = Animatable(0.0, motion=motion)
        self._phase_anim.target = 1.0

        if self._anim_sub is not None:
            self._anim_sub.dispose()
        self._anim_sub = self._phase_anim.subscribe(lambda _: self.invalidate())

        if self._loop_timer is not None:
            runtime.clock.unschedule(self._loop_timer)

        def _next_step(dt: float) -> None:
            if not getattr(self, "_app", None):
                self._loop_timer = None
                return

            if self._phase_anim:
                # Increment target by 1.0 for the next transition
                # Animatable handles retargeting from current value -> next integer
                next_target = self._phase_anim.target + 1.0
                self._phase_anim.target = next_target

                # Avoid floating point creep by resetting periodically?
                # For now let it run. Float precision 2^23 gives plenty of loops.

            # Schedule next update
            runtime.clock.schedule_once(_next_step, duration)

        self._loop_timer = _next_step
        runtime.clock.schedule_once(_next_step, duration)

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

        phase = self._phase_anim.value if self._phase_anim else 0.0
        model = self._get_model()
        points = model.points_at(phase)

        # Rotation: clockwise, with a quarter-turn offset to feel less static.
        ang = (phase * 2.0 * pi) + (pi / 2.0)
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
