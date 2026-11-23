"""A widget that shows pixels the app produces at the widget's own device size."""

from __future__ import annotations

import asyncio
import inspect
import logging
import threading
from functools import partial
from typing import Any, Awaitable, Callable, Optional, Tuple, TypeVar

from nuiitivet.common.call_probe import call_probe, probed_steps
from nuiitivet.common.logging_once import exception_once, warning_once
from nuiitivet.observable import runtime
from nuiitivet.observable.protocols import StateBase
from nuiitivet.rendering.padding import PaddingLike
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import make_raster_image, make_rect
from nuiitivet.rendering.skia.skia_module import get_skia
from nuiitivet.widgeting.callbacks import PendingTask, spawn_task
from nuiitivet.widgeting.context_lookup import find_window
from nuiitivet.widgeting.paint_replay import replay_safe
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.widget_size_change import queue_deferred_publish

logger = logging.getLogger(__name__)

T = TypeVar("T")

# What a run that failed hands back: the surface keeps the raster it had.
_KEEP: Any = object()


class RasterSurface(Widget):
    """Pixels the app draws itself, shown crisp at the widget's device size.

    The surface measures its content rect in device pixels (the logical size
    times the window's :attr:`~nuiitivet.runtime.window.Window.pixel_ratio`)
    and asks for a buffer of exactly that size, so a 200x100 widget on a 2x
    display asks for 400x200. It asks again when that size changes. Until the
    new pixels arrive the last ones are stretched over the new rect.

    The pixels are tightly packed RGBA 8-bit with straight alpha, rows top to
    bottom, in any object exposing the buffer protocol: Pillow, OpenCV, a
    hand-made ``bytearray``. ``None`` empties the surface. A buffer of another
    length shows nothing new, and the log says why.

    From a data source: :meth:`draw`, or :meth:`draw_in_thread` when the
    drawing takes long. A subclass that draws itself overrides
    :meth:`draw_pixels`; made directly, the surface shows nothing.
    """

    def __init__(
        self,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ) -> None:
        """Initialize a RasterSurface.

        Args:
            width: Width sizing.
            height: Height sizing.
            padding: Insets from the allocated rect to the pixels.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(width=width, height=height, padding=padding, key=key)
        self._source: Optional[tuple[StateBase[Any], Callable[[Any, int, int], Any]]] = None
        self._in_thread: bool = False
        self._running: bool = False
        self._again: bool = False
        self._task: "asyncio.Task[Any] | PendingTask | None" = None
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
        data: StateBase[T],
        draw: Callable[[T, int, int], Any],
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ) -> "RasterSurface":
        """Create a RasterSurface redrawn from *data* on every change.

        Args:
            data: The State the pixels are made from.
            draw: Called as ``draw(value, width_px, height_px)`` with the
                current value whenever it changes or the device size does;
                returns the pixels. It runs on the UI thread at the start of a
                frame, and the frame waits for it. A coroutine function, such
                as a worker function, is awaited as a task: no frame waits,
                and a change made meanwhile is drawn when the task ends.
            width: Width sizing.
            height: Height sizing.
            padding: Insets from the allocated rect to the pixels.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        surface = cls(width=width, height=height, padding=padding, key=key)
        surface._source = (data, draw)
        surface.observe(data, lambda _value: surface.request_render())
        return surface

    @classmethod
    def draw_in_thread(
        cls,
        data: StateBase[T],
        draw: Callable[[T, int, int], Any],
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ) -> "RasterSurface":
        """Create a RasterSurface redrawn from *data* on a thread, for a drawing that takes long.

        No frame waits for ``draw``. One call runs at a time. Changes made
        during a call are drawn once, by the next call, with the newest value
        and size. The surface is empty until the first call returns.

        The UI thread keeps running during the parts of ``draw`` that release
        the GIL: OpenCV, numpy, file and network I/O. Pure Python takes turns
        with it. A browser has no thread to give, and the surface stays empty
        there; pass a worker function to :meth:`draw`.

        Args:
            data: The State the pixels are made from. Its value is read on the
                UI thread and handed to ``draw``.
            draw: Called on a thread as ``draw(value, width_px, height_px)``;
                returns the pixels. It must not read widgets or other States.
            width: Width sizing.
            height: Height sizing.
            padding: Insets from the allocated rect to the pixels.
            key: Stable widget identity for dev-bridge targeting and hot reload.

        Raises:
            TypeError: ``draw`` is a coroutine function.
        """
        if inspect.iscoroutinefunction(draw) or inspect.iscoroutinefunction(getattr(draw, "__call__", None)):
            raise TypeError("draw_in_thread runs a plain function on a thread; pass a coroutine function to draw")
        surface = cls(width=width, height=height, padding=padding, key=key)
        surface._source = (data, draw)
        surface._in_thread = True
        surface.observe(data, lambda _value: surface.request_render())
        return surface

    @property
    def pixel_ratio(self) -> float:
        """Device pixels per logical pixel at the last layout; ``1.0`` before it."""
        return self._pixel_ratio

    def draw_pixels(self, width_px: int, height_px: int) -> Any:
        """Return the pixels for the given device size; a subclass that draws itself overrides this.

        Called on the UI thread at the start of a frame, after
        :meth:`request_render` or a change of the device size. An awaitable is
        awaited as a task, and no frame waits for it.

        Args:
            width_px: The width of the content rect in device pixels.
            height_px: The height of the content rect in device pixels.
        """
        return None

    def request_render(self) -> None:
        """Ask for the pixels again at the current device size, at the next frame.

        Several requests in one frame produce one render. While the surface
        has no size, the request waits for the layout that gives it one.
        """
        if self._wanted_px == (0, 0):
            self._requested_px = None
            return
        self._requested_px = self._wanted_px
        queue_deferred_publish(self, self._render, widget=self)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return the fixed width and height; an axis that is not fixed has no intrinsic size beyond the padding."""
        left, top, right, bottom = self.padding
        w_dim = self.width_sizing
        h_dim = self.height_sizing
        width = int(w_dim.value) if w_dim.kind == "fixed" else int(left) + int(right)
        height = int(h_dim.value) if h_dim.kind == "fixed" else int(top) + int(bottom)
        return (width, height)

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

    def on_unmount(self) -> None:
        """Stop following the data; a call still awaited is cancelled, and one on a thread is not shown."""
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            self._running = False
        self._again = False
        super().on_unmount()

    def _render(self) -> None:
        size = self._wanted_px
        if size == (0, 0) or self._unmounted:
            return
        if self._running:
            self._again = True
            return
        try:
            job = self._job(*size)
        except Exception:
            exception_once(logger, "raster_surface_draw_exc", "RasterSurface draw function raised")
            return
        if self._in_thread:
            self._start_thread(job, size)
            return
        probe = call_probe()
        pixels = _call(job if probe is None else partial(probe.call, "draw function", job))
        if inspect.isawaitable(pixels):
            self._start_task(job, pixels, size)
            return
        self._show(_raster(pixels, size), size)

    def _job(self, width_px: int, height_px: int) -> Callable[[], Any]:
        """The call that makes the pixels, the data's value read now, on the UI thread."""
        if self._source is None:
            return partial(self.draw_pixels, width_px, height_px)
        data, draw = self._source
        return partial(draw, data.value, width_px, height_px)

    def _start_thread(self, job: Callable[[], Any], size: tuple[int, int]) -> None:
        def run() -> None:
            raster: Any = _KEEP
            try:
                raster = _raster(_not_awaitable(_call(job)), size)
            finally:
                # Whatever happened above, the surface must hear that the run is over.
                try:
                    runtime.clock.schedule_once(lambda _dt: self._land(raster, size), 0)
                except Exception:
                    self._running = False
                    exception_once(logger, "raster_surface_land_exc", "RasterSurface could not hand its raster over")

        self._running = True
        try:
            threading.Thread(target=run, name="RasterSurface.draw_in_thread", daemon=True).start()
        except RuntimeError:
            self._running = False
            exception_once(
                logger,
                "raster_surface_no_thread_exc",
                "RasterSurface.draw_in_thread could not start a thread; pass a worker function to draw",
            )

    def _start_task(self, job: Callable[[], Any], pixels: Awaitable[Any], size: tuple[int, int]) -> None:
        self._running = True
        awaited = probed_steps("draw function", job, pixels)
        try:
            self._task = spawn_task(self._await(awaited, size), owner_name=type(self).__name__)
        except BaseException:
            # spawn_task closed the wrapper; the coroutine inside it never started.
            self._running = False
            if inspect.iscoroutine(pixels):
                pixels.close()
            raise

    async def _await(self, pixels: Awaitable[Any], size: tuple[int, int]) -> None:
        try:
            result = await pixels
        except asyncio.CancelledError:
            self._running = False
            raise
        except Exception:
            exception_once(logger, "raster_surface_draw_exc", "RasterSurface draw function raised")
            result = _KEEP
        self._task = None
        self._land(_raster(result, size), size)

    def _land(self, raster: Any, size: tuple[int, int]) -> None:
        """Show what a background run made, and start the next when a request waited for it."""
        self._running = False
        if self._unmounted:
            return
        self._show(raster, size)
        if self._again:
            self._again = False
            self.request_render()

    def _show(self, raster: Any, size: tuple[int, int]) -> None:
        if raster is _KEEP:
            return
        self._image = raster
        self._image_px = size if raster is not None else (0, 0)
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


def _call(job: Callable[[], Any]) -> Any:
    """What ``job`` returns; ``_KEEP`` when it raises."""
    try:
        return job()
    except Exception:
        exception_once(logger, "raster_surface_draw_exc", "RasterSurface draw function raised")
        return _KEEP


def _not_awaitable(pixels: Any) -> Any:
    """``pixels``, or ``_KEEP`` for an awaitable: a thread has no loop to await it on."""
    if not inspect.isawaitable(pixels):
        return pixels
    if inspect.iscoroutine(pixels):
        pixels.close()
    warning_once(
        logger,
        "raster_surface_thread_awaitable",
        "RasterSurface.draw_in_thread got an awaitable from its function; pass that function to draw",
    )
    return _KEEP


def _raster(pixels: Any, size: tuple[int, int]) -> Any:
    """The image of ``pixels`` at ``size``; ``None`` and ``_KEEP`` pass through, a wrong buffer is ``_KEEP``."""
    if pixels is None or pixels is _KEEP:
        return pixels
    try:
        return make_raster_image(pixels, size[0], size[1])
    except Exception:
        exception_once(logger, "raster_surface_image_exc", "RasterSurface could not build an image")
        return _KEEP


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


__all__ = ["RasterSurface"]
