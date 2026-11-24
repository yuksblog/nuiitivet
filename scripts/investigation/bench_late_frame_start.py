"""Frames whose work does not fit: how many of them show a subtree that was on screen as nothing.

A panel of cells sits beside a page: rows of cells over a ``RasterSurface``.
The panel's width changes on every frame, so the page's size changes too. Two
things make such a frame late:

* The draw function of the surface takes ``--draw-ms``. It runs at the start
  of the next frame, before layout.
* The panel holds ``--rows`` rows. From about 200 rows its layout alone takes
  longer than the layout's share of a frame, and the layout reaches the page
  past its deadline.

The run drives a window without a loop, one frame after another: the frame
clock begins, the frame-start queue is flushed, the tree is laid out and
painted into a raster canvas cleared before the frame. Each frame begins with
the next one already due, as while an animation runs, so no idle time falls
between them. After the last change of width the frames go on, with idle time
between them, until no subtree is pending.

The panel and the page each begin with a green square. A frame shows one of
them as nothing when the pixel in the middle of its square is not green. A
count of ``paint`` calls would miss a subtree drawn from a recording.

The run reports those frames, the time of a frame and of its parts, the time
a pending child took to paint from its last layout, and the frames the window
needed to be whole again.

Run::

    uv run python scripts/investigation/bench_late_frame_start.py
    uv run python scripts/investigation/bench_late_frame_start.py --draw-ms 4 --frames 240
    uv run python scripts/investigation/bench_late_frame_start.py --draw-ms 0 --rows 400 --page-rows 30
"""

from __future__ import annotations

import argparse
import statistics
import time
from time import perf_counter
from typing import Any, Dict, List

import skia

import nuiitivet.material as nv
from nuiitivet.layout import layout_utils
from nuiitivet.layout.layout_utils import has_pending_layout
from nuiitivet.rendering.skia import make_raster_surface
from nuiitivet.widgeting.frame_clock import begin_frame, end_frame, set_frame_interval
from nuiitivet.widgeting.idle_work import run_idle_work

FRAME_SECONDS = 1.0 / 60.0
IDLE_SLICE_SECONDS = 0.008
WIDTH, HEIGHT = 1100, 720
SETTLE_LIMIT = 200
MARK_SIZE = 16
MARK_COLOR = (0, 255, 0, 255)


def _mark() -> nv.Widget:
    return nv.Box(width=MARK_SIZE, height=MARK_SIZE, background_color=MARK_COLOR)


def _cells(rows: int) -> List[nv.Widget]:
    return [
        nv.Row([nv.Text(f"cell {row}-{column}", width="wt") for column in range(4)], width="wt") for row in range(rows)
    ]


def run(frames: int, draw_ms: float, rows: int, page_rows: int) -> None:
    set_frame_interval(FRAME_SECONDS)
    panel_width = nv.State(320)
    tick = nv.State(0)

    def slow_draw(_value: int, width_px: int, height_px: int) -> bytes:
        time.sleep(draw_ms / 1000.0)
        return bytes(width_px * height_px * 4)

    def build_root() -> nv.Widget:
        panel = nv.Column([_mark(), *_cells(rows)], width=panel_width, height="wt")
        page = nv.Column(
            [_mark(), *_cells(page_rows), nv.RasterSurface.draw(tick, slow_draw, width="wt", height="wt")],
            width="wt",
            height="wt",
        )
        return nv.Row([panel, page], width="wt", height="wt")

    app = nv.App(nv.Window(content=build_root, width=WIDTH, height=HEIGHT))
    window = app.main_window
    surface = make_raster_surface(WIDTH, HEIGHT)
    canvas = surface.getCanvas()

    root = window.root
    paint_root = root.paint
    paint_began = [0.0]

    def timed_paint(*args, **kwargs) -> None:
        paint_began[0] = perf_counter()
        paint_root(*args, **kwargs)

    root.paint = timed_paint  # type: ignore[method-assign]

    pending_ms: List[float] = []
    paint_pending = layout_utils.paint_pending_child

    def timed_pending(*args: Any) -> None:
        began = perf_counter()
        paint_pending(*args)
        pending_ms.append((perf_counter() - began) * 1000.0)

    layout_utils.paint_pending_child = timed_pending

    def frame() -> Dict[str, float]:
        """One frame; the milliseconds of its parts."""
        canvas.clear(0)
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

    def shown(left: int) -> bool:
        """Whether the last frame painted the square of the subtree whose left edge is ``left``."""
        at = skia.IRect.MakeXYWH(left + MARK_SIZE // 2, MARK_SIZE // 2, 1, 1)
        # The surface's own channel order differs between platforms.
        pixel = surface.makeImageSnapshot(at).toarray(colorType=skia.kRGBA_8888_ColorType)[0, 0]
        return tuple(int(value) for value in pixel) == MARK_COLOR

    def settle() -> int:
        """Frames, with idle time between them, until no subtree is pending and both subtrees show."""
        for count in range(1, SETTLE_LIMIT + 1):
            frame()
            run_idle_work(IDLE_SLICE_SECONDS)
            if not has_pending_layout() and shown(0) and shown(panel_width.value):
                return count
        return SETTLE_LIMIT

    # The fonts and the theme load on the first frames; they are not counted.
    settle()
    settle()

    panel_blank = 0
    page_blank = 0
    timings: List[Dict[str, float]] = []
    for index in range(frames):
        panel_width.value = 320 + 40 * (index % 2) + index % 7
        timings.append(frame())
        if not shown(0):
            panel_blank += 1
        if not shown(panel_width.value):
            page_blank += 1
    pending_ms_while_changing = sorted(pending_ms)
    whole_after = settle()

    print(
        f"draw function {draw_ms:.0f} ms, {rows} rows of cells in the panel, {page_rows} in the page, "
        f"frame {FRAME_SECONDS * 1000:.1f} ms"
    )
    print(f"frames while the width changes   {frames}")
    print(f"  the panel painted as nothing   {panel_blank}")
    print(f"  the page painted as nothing    {page_blank}")
    for part in ("frame", "frame-start queue", "layout", "paint"):
        ordered = sorted(timing[part] for timing in timings)
        print(
            f"  {part + ', ms':31}median {statistics.median(ordered):.1f}, "
            f"p95 {ordered[int(len(ordered) * 0.95)]:.1f}, max {ordered[-1]:.1f}"
        )
    if pending_ms_while_changing:
        ordered = pending_ms_while_changing
        print(
            f"  {'a pending child painted, ms':31}median {statistics.median(ordered):.2f}, "
            f"p95 {ordered[int(len(ordered) * 0.95)]:.2f}, max {ordered[-1]:.2f}, {len(ordered)} times"
        )
    print(f"frames until whole afterwards    {whole_after}")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--frames", type=int, default=120, help="frames in which the width changes")
    parser.add_argument("--draw-ms", type=float, default=9.0, help="the time the draw function takes")
    parser.add_argument("--rows", type=int, default=30, help="rows of cells in the panel")
    parser.add_argument("--page-rows", type=int, default=0, help="rows of cells in the page, over the surface")
    args = parser.parse_args()
    run(args.frames, args.draw_ms, args.rows, args.page_rows)


if __name__ == "__main__":
    main()
