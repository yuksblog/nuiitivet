"""Measure the dev-profiling overhead on a heavy scrolling app.

A VerticalScrollable holds 1000 rows; the whole content repaints every frame
while an auto-scroll runs, so every row's ``paint`` fires each painted frame —
the worst case for the per-widget paint counter. An Observable ticking every
frame drives one Text so the recomposition probe fires too.

The script times ``root.paint`` (the full tree walk) per painted frame and
prints mean/median/p95/max after a warmup. Run both modes and compare::

    python scripts/investigation/bench_profiling_overhead.py            # baseline
    python scripts/investigation/bench_profiling_overhead.py --profile  # instrumented
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from typing import Any, List, Optional

import pyglet

import nuiitivet.material as nv
from nuiitivet.scrolling.controller import ScrollController
from nuiitivet.scrolling.types import ScrollDirection

N_ROWS = 1000
WARMUP_FRAMES = 100
SAMPLE_FRAMES = 600
SCROLL_STEP = 6.0

_COLORS = ("#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#F44336")


def build_root(counter: nv.Observable, controller: ScrollController) -> nv.Widget:
    rows: List[nv.Widget] = [nv.Text(counter.map(lambda n: f"tick {n}"))]
    for i in range(N_ROWS):
        box = nv.Container(width=24, height=24).modifier(nv.background(_COLORS[i % len(_COLORS)]))
        rows.append(nv.Row(gap=8, padding=2, children=[box, nv.Text(f"Row {i}")]))
    return nv.VerticalScrollable(
        nv.Column(children=rows),
        controller=controller,
        scrollbar_visible=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="store_true", help="install dev profiling hooks")
    args = parser.parse_args()

    counter = nv.Observable(0)
    controller = ScrollController(axes=(ScrollDirection.VERTICAL,), primary_axis=ScrollDirection.VERTICAL)

    app = nv.App(
        nv.Window(
            content=lambda: build_root(counter, controller),
            title="profiling overhead bench",
            width=480,
            height=800,
        )
    )

    session = None
    if args.profile:
        from nuiitivet.dev import profiling

        session = profiling.start()

    samples: List[float] = []
    state = {"installed": False, "down": True, "done": False}

    def install_paint_timer(win: Any) -> None:
        orig = win.root.paint

        def timed(canvas: Any, x: int, y: int, w: int, h: int) -> None:
            t0 = time.perf_counter()
            orig(canvas, x, y, w, h)
            samples.append(time.perf_counter() - t0)

        win.root.paint = timed

    def finish(win: Any) -> None:
        state["done"] = True
        data = samples[WARMUP_FRAMES : WARMUP_FRAMES + SAMPLE_FRAMES]
        data_ms = sorted(d * 1000.0 for d in data)
        result = {
            "mode": "profile" if args.profile else "baseline",
            "rows": N_ROWS,
            "painted_frames": len(samples),
            "sampled": len(data_ms),
            "mean_ms": round(statistics.fmean(data_ms), 3),
            "median_ms": round(statistics.median(data_ms), 3),
            "p95_ms": round(data_ms[int(len(data_ms) * 0.95) - 1], 3),
            "max_ms": round(data_ms[-1], 3),
        }
        if session is not None:
            result["profiler"] = {
                "paint_count_total": sum(session.paint_counts.values()),
                "widgets_counted": len(session.paint_counts),
                "rebuild_count_total": sum(session.rebuild_counts.values()),
                "frames_recorded": len(session.frame_durations),
            }
        print(json.dumps(result))
        win.close()

    def tick(dt: float) -> None:
        if state["done"]:
            return
        windows = app.windows
        if not windows:
            return
        win = windows[0]
        if getattr(win, "root", None) is None:
            return
        if not state["installed"]:
            install_paint_timer(win)
            state["installed"] = True
        counter.value += 1
        before = controller.get_offset()
        controller.scroll_by(SCROLL_STEP if state["down"] else -SCROLL_STEP)
        if controller.get_offset() == before:
            state["down"] = not state["down"]
        win.invalidate()
        if len(samples) >= WARMUP_FRAMES + SAMPLE_FRAMES:
            finish(win)

    pyglet.clock.schedule_interval(tick, 1 / 120)
    app.run()


if __name__ == "__main__":
    main()
