"""Frames that start late: how many of them paint a subtree that was on screen as nothing.

A panel of cells sits beside a ``RasterSurface`` whose draw function takes
``--draw-ms``. The panel's width changes on every frame, so the surface's size
changes too and its draw function runs at the start of the next frame, before
layout.

The run drives a window without a loop, one frame after another: the frame
clock begins, the frame-start queue is flushed, the tree is laid out and
painted into a raster canvas. Each frame begins with the next one already due,
as while an animation runs, so no idle time falls between them. After the last
change of width the frames go on, with idle time between them, until no
subtree is pending.

The run reports the frames in which the panel was not painted, the time of a
frame and of its parts, and the frames the window needed to be whole again.

Run::

    uv run python scripts/investigation/bench_late_frame_start.py
    uv run python scripts/investigation/bench_late_frame_start.py --draw-ms 4 --frames 240
"""

from __future__ import annotations

import argparse
import statistics
import time
from time import perf_counter
from typing import Dict, List

import nuiitivet.material as nv
from nuiitivet.layout.layout_utils import has_pending_layout
from nuiitivet.rendering.skia import make_raster_surface
from nuiitivet.widgeting.frame_clock import begin_frame, end_frame, set_frame_interval
from nuiitivet.widgeting.idle_work import run_idle_work

FRAME_SECONDS = 1.0 / 60.0
IDLE_SLICE_SECONDS = 0.008
WIDTH, HEIGHT = 1100, 720
SETTLE_LIMIT = 200


class _Panel(nv.Column):
    """A column that counts its paints."""

    painted = 0

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1
        super().paint(canvas, x, y, width, height)


def run(frames: int, draw_ms: float, rows: int) -> None:
    set_frame_interval(FRAME_SECONDS)
    panel_width = nv.State(320)
    tick = nv.State(0)
    panels: List[_Panel] = []

    def slow_draw(_value: int, width_px: int, height_px: int) -> bytes:
        time.sleep(draw_ms / 1000.0)
        return bytes(width_px * height_px * 4)

    def build_root() -> nv.Widget:
        cells = [
            nv.Row([nv.Text(f"cell {row}-{column}", width="wt") for column in range(4)], width="wt")
            for row in range(rows)
        ]
        panel = _Panel(cells, width=panel_width, height="wt")
        panels.append(panel)
        return nv.Row(
            [panel, nv.RasterSurface.draw(tick, slow_draw, width="wt", height="wt")],
            width="wt",
            height="wt",
        )

    app = nv.App(nv.Window(content=build_root, width=WIDTH, height=HEIGHT))
    window = app.main_window
    panel = panels[0]
    canvas = make_raster_surface(WIDTH, HEIGHT).getCanvas()

    root = window.root
    paint_root = root.paint
    paint_began = [0.0]

    def timed_paint(*args, **kwargs) -> None:
        paint_began[0] = perf_counter()
        paint_root(*args, **kwargs)

    root.paint = timed_paint  # type: ignore[method-assign]

    def frame() -> Dict[str, float]:
        """One frame; the milliseconds of its parts."""
        start = perf_counter()
        begin_frame(start)
        try:
            window._flush_frame_queues()
            queue_done = perf_counter()
            window._mount_paint_unmount(canvas, 0, 0, WIDTH, HEIGHT)
        finally:
            end_frame()
        done = perf_counter()
        return {
            "frame": (done - start) * 1000.0,
            "frame-start queue": (queue_done - start) * 1000.0,
            "layout": (paint_began[0] - queue_done) * 1000.0,
            "paint": (done - paint_began[0]) * 1000.0,
        }

    def settle() -> int:
        """Frames, with idle time between them, until no subtree is pending and the panel was painted."""
        for count in range(1, SETTLE_LIMIT + 1):
            before = panel.painted
            frame()
            run_idle_work(IDLE_SLICE_SECONDS)
            if not has_pending_layout() and panel.painted > before:
                return count
        return SETTLE_LIMIT

    # The fonts and the theme load on the first frames; they are not counted.
    settle()
    settle()

    blank = 0
    timings: List[Dict[str, float]] = []
    for index in range(frames):
        panel_width.value = 320 + 40 * (index % 2) + index % 7
        before = panel.painted
        timings.append(frame())
        if panel.painted == before:
            blank += 1
    whole_after = settle()

    print(f"draw function {draw_ms:.0f} ms, {rows} rows of cells, frame {FRAME_SECONDS * 1000:.1f} ms")
    print(f"frames while the width changes   {frames}")
    print(f"  the panel painted as nothing   {blank}")
    for part in ("frame", "frame-start queue", "layout", "paint"):
        ordered = sorted(timing[part] for timing in timings)
        print(
            f"  {part + ', ms':31}median {statistics.median(ordered):.1f}, "
            f"p95 {ordered[int(len(ordered) * 0.95)]:.1f}, max {ordered[-1]:.1f}"
        )
    print(f"frames until whole afterwards    {whole_after}")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--frames", type=int, default=120, help="frames in which the width changes")
    parser.add_argument("--draw-ms", type=float, default=9.0, help="the time the draw function takes")
    parser.add_argument("--rows", type=int, default=30, help="rows of cells in the panel")
    args = parser.parse_args()
    run(args.frames, args.draw_ms, args.rows)


if __name__ == "__main__":
    main()
