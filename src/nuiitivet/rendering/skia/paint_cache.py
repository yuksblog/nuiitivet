"""Paint cache helpers for Skia rendering."""

from __future__ import annotations

from contextlib import contextmanager
import logging
from typing import Any, Optional, Tuple, cast

from nuiitivet.common.logging_once import debug_once, exception_once
from .skia_module import get_skia


_logger = logging.getLogger(__name__)


_PAINT_CACHE_SKIP = object()


class CachedPaintMixin:
    """Reusable paint cache that records a widget's visuals into a Skia surface."""

    PAINT_CACHE_SKIP = _PAINT_CACHE_SKIP

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self._paint_cache_surface: Any = None
        self._paint_cache_surface_size: Optional[Tuple[int, int]] = None
        self._paint_cache_snapshot: Any = None
        self._paint_cache_snapshot_size: Optional[Tuple[int, int]] = None
        self._paint_cache_snapshot_outsets: Optional[Tuple[int, int, int, int]] = None
        super().__init__(*args, **kwargs)

    @contextmanager
    def paint_cache(self, canvas: Any, x: int, y: int, width: int, height: int):
        """Yield a canvas that records into an offscreen cache when possible."""

        w = max(0, int(width))
        h = max(0, int(height))
        if w == 0 or h == 0:
            yield canvas
            return

        origin_x, origin_y, extended_w, extended_h, outsets = self._resolve_paint_cache_bounds(x, y, w, h)
        if extended_w == 0 or extended_h == 0:
            yield canvas
            return

        if self._try_draw_paint_cache(canvas, origin_x, origin_y, extended_w, extended_h, outsets):
            yield self.PAINT_CACHE_SKIP
            return

        recorder = self._begin_paint_cache(canvas, extended_w, extended_h)
        if recorder is None:
            yield canvas
            return

        translated = self._apply_recording_transform(recorder, origin_x, origin_y)
        try:
            yield recorder
        finally:
            if translated:
                self._restore_recording_transform(recorder)
            self._finalize_paint_cache(canvas, origin_x, origin_y, extended_w, extended_h, outsets)

    def invalidate_paint_cache(self) -> None:
        """Explicitly clear cached visuals and request a repaint if mounted."""

        self._invalidate_paint_cache()
        invalidate = getattr(self, "invalidate", None)
        if callable(invalidate):
            try:
                invalidate()
            except Exception:
                exception_once(
                    _logger,
                    f"paint_cache_invalidate_exc:{type(self).__name__}",
                    "Exception in invalidate() after paint cache invalidation for widget=%s",
                    type(self).__name__,
                )

    def _invalidate_paint_cache(self) -> None:
        self._paint_cache_surface = None
        self._paint_cache_surface_size = None
        self._paint_cache_snapshot = None
        self._paint_cache_snapshot_size = None
        self._paint_cache_snapshot_outsets = None
        try:
            super()._invalidate_paint_cache()  # type: ignore[misc]
        except AttributeError:
            debug_once(
                _logger,
                f"paint_cache_super_invalidate_missing:{type(self).__name__}",
                "Base class has no _invalidate_paint_cache (widget=%s)",
                type(self).__name__,
            )

    def _begin_paint_cache(self, canvas: Any, width: int, height: int):
        if canvas is None:
            return None
        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return None
        target_size = (max(1, width), max(1, height))
        surface = self._paint_cache_surface
        if surface is None or self._paint_cache_surface_size != target_size:
            try:
                surface = skia.Surface(*target_size)
            except Exception:
                exception_once(
                    _logger,
                    "paint_cache_surface_create_exc",
                    "Failed to create Skia Surface for paint cache: size=%s",
                    target_size,
                )
                self._paint_cache_surface = None
                self._paint_cache_surface_size = None
                return None
            self._paint_cache_surface = surface
            self._paint_cache_surface_size = target_size
        try:
            surface_canvas = surface.getCanvas()
        except Exception:
            exception_once(
                _logger,
                "paint_cache_surface_get_canvas_exc",
                "Failed to get canvas from paint cache surface",
            )
            return None
        self._clear_surface_canvas(surface_canvas, skia)
        return surface_canvas

    def _clear_surface_canvas(self, recorder: Any, skia: Any) -> None:
        if recorder is None:
            return
        try:
            recorder.clear(skia.Color4f(0.0, 0.0, 0.0, 0.0))
            return
        except Exception:
            exception_once(
                _logger,
                "paint_cache_clear_color4f_exc",
                "Failed to clear cache canvas using skia.Color4f",
            )
        try:
            recorder.clear(0)
        except Exception:
            exception_once(
                _logger,
                "paint_cache_clear_int_exc",
                "Failed to clear cache canvas using integer clear",
            )

    def _apply_recording_transform(self, recorder: Any, x: int, y: int) -> bool:
        if recorder is None:
            return False
        try:
            recorder.save()
            recorder.translate(-float(x), -float(y))
            return True
        except Exception:
            exception_once(
                _logger,
                "paint_cache_apply_transform_exc",
                "Failed to apply paint cache recording transform",
            )
            return False

    def _restore_recording_transform(self, recorder: Any) -> None:
        try:
            recorder.restore()
        except Exception:
            exception_once(
                _logger,
                "paint_cache_restore_transform_exc",
                "Failed to restore paint cache recording transform",
            )

    def _finalize_paint_cache(
        self,
        canvas: Any,
        origin_x: int,
        origin_y: int,
        width: int,
        height: int,
        outsets: Tuple[int, int, int, int],
    ) -> None:
        surface = self._paint_cache_surface
        if surface is None:
            self._paint_cache_snapshot = None
            self._paint_cache_snapshot_size = None
            self._paint_cache_snapshot_outsets = None
            return
        try:
            snapshot = surface.makeImageSnapshot()
        except Exception:
            exception_once(
                _logger,
                "paint_cache_make_snapshot_exc",
                "Failed to make image snapshot for paint cache",
            )
            self._paint_cache_snapshot = None
            self._paint_cache_snapshot_size = None
            self._paint_cache_snapshot_outsets = None
            return
        self._paint_cache_snapshot = snapshot
        self._paint_cache_snapshot_size = (width, height)
        self._paint_cache_snapshot_outsets = outsets
        self._blit_cached_image(canvas, snapshot, origin_x, origin_y)

    def _try_draw_paint_cache(
        self,
        canvas: Any,
        origin_x: int,
        origin_y: int,
        width: int,
        height: int,
        outsets: Tuple[int, int, int, int],
    ) -> bool:
        if canvas is None:
            return False
        if self._paint_cache_snapshot is None:
            return False
        if self._paint_cache_snapshot_size != (width, height):
            return False
        if self._paint_cache_snapshot_outsets != outsets:
            return False
        return self._blit_cached_image(canvas, self._paint_cache_snapshot, origin_x, origin_y)

    def _blit_cached_image(self, canvas: Any, image: Any, x: int, y: int) -> bool:
        if canvas is None or image is None:
            return False
        draw = getattr(canvas, "drawImage", None)
        if callable(draw):
            try:
                draw(image, float(x), float(y))
                return True
            except Exception:
                exception_once(
                    _logger,
                    "paint_cache_draw_image_exc",
                    "Failed to draw cached image using drawImage; falling back",
                )
        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return False
        try:
            rect_src = skia.Rect.MakeXYWH(0, 0, image.width(), image.height())
            rect_dst = skia.Rect.MakeXYWH(float(x), float(y), float(image.width()), float(image.height()))
            canvas.drawImageRect(image, rect_src, rect_dst)
            return True
        except Exception:
            exception_once(
                _logger,
                "paint_cache_draw_image_rect_exc",
                "Failed to draw cached image using drawImageRect",
            )
            return False

    def paint_outsets(self) -> Tuple[int, int, int, int]:  # pragma: no cover - default passthrough
        parent = getattr(super(), "paint_outsets", None)
        if callable(parent):
            try:
                return parent()
            except Exception:
                exception_once(
                    _logger,
                    f"paint_cache_paint_outsets_exc:{type(self).__name__}",
                    "Exception in paint_outsets() for widget=%s",
                    type(self).__name__,
                )
                return (0, 0, 0, 0)
        return (0, 0, 0, 0)

    def _resolve_paint_cache_bounds(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Tuple[int, int, int, int, Tuple[int, int, int, int]]:
        outsets = self._coerce_paint_outsets(self.paint_outsets())
        left, top, right, bottom = outsets
        extended_w = max(0, width + left + right)
        extended_h = max(0, height + top + bottom)
        origin_x = x - left
        origin_y = y - top
        return origin_x, origin_y, extended_w, extended_h, outsets

    @staticmethod
    def _coerce_paint_outsets(value: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        try:
            left, top, right, bottom = value
        except Exception:
            exception_once(_logger, "paint_cache_outsets_unpack_exc", "Failed to unpack paint outsets")
            return (0, 0, 0, 0)

        def _coerce(component: object) -> int:
            try:
                coerced = int(cast(Any, component))
            except Exception:
                exception_once(_logger, "paint_cache_outsets_component_exc", "Failed to coerce paint outsets component")
                return 0
            return max(0, coerced)

        return (_coerce(left), _coerce(top), _coerce(right), _coerce(bottom))
