"""A widget that shows pixels the app produces at the widget's own device size."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, TypeVar

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable.protocols import ObservableBase
from nuiitivet.rendering.padding import PaddingLike
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import make_raster_image, make_rect
from nuiitivet.rendering.skia.skia_module import get_skia
from nuiitivet.widgeting.context_lookup import find_window
from nuiitivet.widgeting.paint_replay import replay_safe
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.widget_size_change import queue_deferred_publish

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Produces the pixels for a surface of the given size in device pixels:
#: tightly packed RGBA 8-bit with straight alpha, rows top to bottom, any
#: object exposing the buffer protocol. ``None`` leaves the surface empty.
DrawFn = Callable[[int, int], Any]


class RasterSurface(Widget):
    """Pixels the app draws itself, shown crisp at the widget's device size.

    The surface measures its content rect in device pixels (the logical size
    times the window's :attr:`~nuiitivet.runtime.window.Window.pixel_ratio`)
    and asks ``draw`` for a buffer of exactly that size, so a 200x100 widget
    on a 2x display receives a 400x200 request. It asks again when that size
    changes. Any producer of RGBA bytes plugs in: Pillow, OpenCV, a hand-made
    ``bytearray``.

    The pixels are produced between frames, never during layout or paint.
    While a window is being resized the previous raster is stretched for one
    frame and the crisp one follows. From a data source: :meth:`draw`.
    """

    def __init__(
        self,
        draw: DrawFn,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ) -> None:
        """Initialize a RasterSurface.

        Args:
            draw: Called as ``draw(width_px, height_px)`` whenever the surface
                needs pixels for that device size; returns the RGBA buffer, or
                ``None`` for an empty surface.
            width: Width sizing.
            height: Height sizing.
            padding: Insets from the allocated rect to the pixels.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(width=width, height=height, padding=padding, key=key)
        self._draw: DrawFn = draw
        self._pixel_ratio: float = 1.0
        # The device size the next render is for, and the one last requested:
        # a layout that measures the same size again queues nothing.
        self._wanted_px: tuple[int, int] = (0, 0)
        self._requested_px: Optional[tuple[int, int]] = None
        self._image: Any | None = None
        self._image_px: tuple[int, int] = (0, 0)

    @classmethod
    def draw(
        cls,
        data: ObservableBase[T],
        draw: Callable[[T, int, int], Any],
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ) -> "RasterSurface":
        """Create a RasterSurface redrawn from *data* on every change.

        Args:
            data: The observable the pixels are made from.
            draw: Called as ``draw(value, width_px, height_px)`` with the
                current value whenever it changes or the device size does;
                returns the RGBA buffer, or ``None`` for an empty surface.
            width: Width sizing.
            height: Height sizing.
            padding: Insets from the allocated rect to the pixels.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        surface = cls(
            lambda w, h: draw(data.value, w, h),
            width=width,
            height=height,
            padding=padding,
            key=key,
        )
        surface.observe(data, lambda _value: surface.request_render())
        return surface

    @property
    def pixel_ratio(self) -> float:
        """Device pixels per logical pixel at the last layout; ``1.0`` before it."""
        return self._pixel_ratio

    def request_render(self) -> None:
        """Ask for the pixels again at the current device size, between frames.

        Several requests in one frame produce one render. Before the first
        layout there is no size to render at, and the request waits for it.
        """
        if self._wanted_px == (0, 0):
            return
        self._requested_px = self._wanted_px
        queue_deferred_publish(self, self._render, widget=self)

    def layout(self, width: int, height: int) -> None:
        """Measure the content rect in device pixels; queue a render when it changed."""
        super().layout(width, height)
        window = find_window(self)
        ratio = float(window.pixel_ratio) if window is not None else 1.0
        self._pixel_ratio = ratio if ratio > 0 else 1.0
        _cx, _cy, cw, ch = self.content_rect(0, 0, width, height)
        wanted = (int(round(cw * self._pixel_ratio)), int(round(ch * self._pixel_ratio)))
        self._wanted_px = wanted
        if wanted == (0, 0) or wanted == self._requested_px:
            return
        self.request_render()

    def _render(self) -> None:
        width_px, height_px = self._wanted_px
        if (width_px, height_px) == (0, 0):
            return
        try:
            pixels = self._draw(width_px, height_px)
        except Exception:
            exception_once(logger, "raster_surface_draw_exc", "RasterSurface draw function raised")
            return
        if pixels is None:
            self._image = None
            self._image_px = (0, 0)
            self.invalidate()
            return
        try:
            image = make_raster_image(pixels, width_px, height_px)
        except Exception:
            exception_once(logger, "raster_surface_image_exc", "RasterSurface could not build an image")
            return
        self._image = image
        self._image_px = (width_px, height_px)
        self.invalidate()

    @replay_safe
    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint the last raster into the content rect."""
        self.set_last_rect(x, y, width, height)
        if canvas is None or self._image is None:
            return
        cx, cy, cw, ch = self.content_rect(x, y, width, height)
        if cw <= 0 or ch <= 0:
            return
        img_w, img_h = self._image_px
        src = make_rect(0, 0, img_w, img_h)
        dst = make_rect(cx, cy, cw, ch)
        if src is None or dst is None:
            return
        try:
            canvas.drawImageRect(self._image, src, dst, *_linear_sampling())
        except Exception:
            exception_once(logger, "raster_surface_draw_rect_exc", "drawImageRect failed")


def _linear_sampling() -> tuple[Any, ...]:
    """Linear filtering, so a raster stretched for a frame blurs instead of blocking."""
    backend = get_skia(raise_if_missing=False)
    sampling = getattr(backend, "SamplingOptions", None) if backend is not None else None
    filter_mode = getattr(backend, "FilterMode", None) if backend is not None else None
    linear = getattr(filter_mode, "kLinear", None) if filter_mode is not None else None
    if sampling is None or linear is None:
        return ()
    try:
        return (sampling(linear),)
    except Exception:
        return ()


__all__ = ["DrawFn", "RasterSurface"]
