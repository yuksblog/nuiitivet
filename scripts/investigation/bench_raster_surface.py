"""Benchmark what a new raster costs the UI thread, drawn in the frame and drawn on a thread.

The constructed case is a camera-sized frame (4000x3000 RGBA) scaled to a
1920x1080 surface each time a value changes. Two scaling functions stand in
for an app's draw function: numpy fancy indexing, and ``cv2.resize`` when
OpenCV is installed, which releases the GIL.

Per new raster it reports:

* ``UI thread``: the time the surface's own code takes on the UI thread. With
  ``draw`` this is the frame-start queue: the draw function and the copy into
  Skia. With ``draw_in_thread`` it is the frame-start queue, which starts the
  thread, plus the swap of the image when the thread hands it over.
* ``stalled``: the longest time the UI thread could not run while the thread
  drew and built the image. The UI thread spins meanwhile and records the
  longest gap between two of its own iterations.

``draw_in_thread, frombytes`` forces the copy into Skia that holds the GIL,
which is the one an app without numpy gets.

No window opens: the surface is laid out by hand and the frame-start queue is
flushed by hand, as the unit tests do.

Run:  python scripts/investigation/bench_raster_surface.py [--frames N]
"""

from __future__ import annotations

import argparse
import statistics
import threading
import time
from typing import Any, Callable

import numpy as np

import nuiitivet.rendering.skia.surface as surface_mod
from nuiitivet.observable import State, runtime
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks
from nuiitivet.widgets.raster_surface import RasterSurface

WIDTH, HEIGHT = 1920, 1080
SOURCE = np.random.default_rng(0).integers(0, 255, (3000, 4000, 4), dtype=np.uint8)

DrawFn = Callable[[int, int, int], Any]


def scale_numpy(_tick: int, width: int, height: int) -> Any:
    ys = np.linspace(0, SOURCE.shape[0] - 1, height).astype(np.intp)
    xs = np.linspace(0, SOURCE.shape[1] - 1, width).astype(np.intp)
    return np.ascontiguousarray(SOURCE[ys[:, None], xs[None, :]])


def scale_opencv(_tick: int, width: int, height: int) -> Any:
    import cv2

    return cv2.resize(SOURCE, (width, height), interpolation=cv2.INTER_AREA)


class _Clock:
    """Collects what the drawing thread hands to the UI thread."""

    def __init__(self) -> None:
        self._scheduled: list[Callable[[float], None]] = []
        self._lock = threading.Lock()

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        with self._lock:
            self._scheduled.append(fn)

    def schedule_interval(self, fn: Callable[[float], None], interval: float) -> None:
        raise NotImplementedError

    def unschedule(self, fn: Callable[[float], None]) -> None:
        with self._lock:
            self._scheduled = [each for each in self._scheduled if each != fn]

    def pending(self) -> bool:
        return bool(self._scheduled)

    def tick(self) -> None:
        with self._lock:
            due, self._scheduled = self._scheduled, []
        for fn in due:
            fn(0.0)


def _frame_start() -> float:
    start = time.perf_counter()
    flush_size_change_callbacks()
    return (time.perf_counter() - start) * 1000


def measure(mode: str, draw: DrawFn, frames: int, clock: _Clock) -> tuple[list[float], list[float]]:
    tick: State[int] = State(0)
    factory = RasterSurface.draw if mode == "draw" else RasterSurface.draw_in_thread
    surface = factory(tick, draw, width=WIDTH, height=HEIGHT)
    surface.layout(WIDTH, HEIGHT)

    frame_start: list[float] = []
    stalled: list[float] = []
    for index in range(frames + 1):
        if index:
            tick.value = index
        spent = _frame_start()
        if mode != "draw":
            longest = 0.0
            last = time.perf_counter()
            while not clock.pending():
                now = time.perf_counter()
                longest = max(longest, now - last)
                last = now
            # The gap the loop ended in: the thread built the image and handed it over inside it.
            longest = max(longest, time.perf_counter() - last)
            start = time.perf_counter()
            clock.tick()
            spent += (time.perf_counter() - start) * 1000
            stalled.append(longest * 1000)
        frame_start.append(spent)
    # The first raster pays for imports and first-touch memory.
    return frame_start[1:], stalled[1:]


def _row(label: str, frame_start: list[float], stalled: list[float]) -> str:
    def cell(values: list[float]) -> str:
        if not values:
            return f"{'-':>17}"
        return f"{statistics.median(values):7.2f} / {max(values):7.2f}"

    return f"  {label:28} {cell(frame_start)}   {cell(stalled)}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--frames", type=int, default=30)
    args = parser.parse_args()

    clock = _Clock()
    runtime.clock = clock  # type: ignore[assignment]

    draws: dict[str, DrawFn] = {"numpy fancy indexing": scale_numpy}
    try:
        import cv2  # noqa: F401

        draws["cv2.resize (releases the GIL)"] = scale_opencv
    except ImportError:
        print("OpenCV is not installed: the cv2.resize case is skipped")

    by_numpy = surface_mod._image_copied_by_numpy
    for name, draw in draws.items():
        took = statistics.median(_time(lambda: draw(0, WIDTH, HEIGHT)) for _ in range(5))
        print(f"{name}: 4000x3000 -> {WIDTH}x{HEIGHT}, {took:.1f} ms a call on one thread")
        print(f"  {'mode':28} {'UI thread, ms':>17}   {'stalled, ms':>17}")
        print(f"  {'':28} {'median / max':>17}   {'median / max':>17}")
        print(_row("draw", *measure("draw", draw, args.frames, clock)))
        print(_row("draw_in_thread", *measure("thread", draw, args.frames, clock)))
        surface_mod._image_copied_by_numpy = lambda *_args: None  # type: ignore[assignment]
        try:
            print(_row("draw_in_thread, frombytes", *measure("thread", draw, args.frames, clock)))
        finally:
            surface_mod._image_copied_by_numpy = by_numpy


def _time(fn: Callable[[], Any]) -> float:
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000


if __name__ == "__main__":
    main()
