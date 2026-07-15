"""Benchmark the GPU-path full-frame paint cache (issue #369, Part A).

The GPU renderer used to call ``root.paint(...)`` on every frame it produced,
walking the whole widget tree in Python even for redraws where the content had
not changed -- e.g. a surface-loss redraw after the window is shown or
re-activated. Part A adds a cached full-frame snapshot that such redraws can
re-blit instead of re-walking the tree.

This benchmark builds a large widget tree and compares, per frame:

* ``full-walk``: ``root.paint(...)`` over the whole tree (the old behaviour, and
  still what a genuine content change costs).
* ``reblit``:    ``canvas.drawImage(cached_snapshot, 0, 0)`` (Part A's fast path
  for content-unchanged redraws).

A real GL context is not needed: the Python tree walk dominates paint cost and
is identical whether the backing surface is GPU- or CPU-resident, so a Skia CPU
surface is a faithful stand-in for the measurement.

Run:  python scripts/investigation/bench_gpu_frame_cache.py [--tiles N] [--frames N]
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time


def _add_src_to_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def build_tree(tiles_per_side: int):
    import nuiitivet as n

    def leaf(i: int):
        return n.Container(
            width=30,
            height=18,
            child=n.Box(background_color=(200, 180, i % 255, 255), corner_radius=4),
        )

    rows = [
        n.Row(children=[leaf(r * tiles_per_side + c) for c in range(tiles_per_side)])
        for r in range(tiles_per_side)
    ]
    return n.Column(children=rows)


def _time_median(fn, frames: int) -> float:
    # One warm-up frame (first paint primes lazy caches/layout) then measure.
    fn()
    samples = []
    for _ in range(frames):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles", type=int, default=40, help="tiles per side (tree has tiles^2 leaves)")
    parser.add_argument("--frames", type=int, default=120, help="frames to time per scenario")
    args = parser.parse_args()

    _add_src_to_path()
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia()
    if skia is None:
        print("skia unavailable; cannot run benchmark", file=sys.stderr)
        return 1

    size = max(200, args.tiles * 34)
    root = build_tree(args.tiles)
    root.layout(size, size)

    surf = skia.Surface(size, size)
    canvas = surf.getCanvas()

    # Prime the cached snapshot the same way draw_gpu_frame does.
    root.paint(canvas, 0, 0, size, size)
    snapshot = surf.makeImageSnapshot()

    leaves = args.tiles * args.tiles

    def full_walk():
        canvas.clear(skia.ColorWHITE)
        root.paint(canvas, 0, 0, size, size)

    def reblit():
        canvas.clear(skia.Color(0, 0, 0, 0))
        canvas.drawImage(snapshot, 0.0, 0.0)

    full_ms = _time_median(full_walk, args.frames)
    reblit_ms = _time_median(reblit, args.frames)

    speedup = full_ms / reblit_ms if reblit_ms > 0 else float("inf")

    print(f"tree: {args.tiles}x{args.tiles} = {leaves} leaf tiles, surface {size}x{size}")
    print(f"frames timed: {args.frames} (median ms)")
    print(f"  full-walk (root.paint):  {full_ms:8.3f} ms   <- old surface-loss redraw cost")
    print(f"  reblit    (drawImage):   {reblit_ms:8.3f} ms   <- Part A cached redraw cost")
    print(f"  speedup:                 {speedup:8.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
