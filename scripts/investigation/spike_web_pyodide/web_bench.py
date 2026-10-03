"""The Pyodide side of the spike: ``bench_paint_walk.measure`` over the CanvasKit shim.

Started by ``run.mjs``; it does not run on its own.
"""

from __future__ import annotations

import cProfile
import logging
import pstats
import time

import js

# The framework logs a Skia call that failed and carries on, so a gap in the
# shim shows up here and nowhere else.
logging.basicConfig(level=logging.WARNING)

import_start = time.perf_counter()
import bench_paint_walk  # noqa: E402
import nuiitivet.material  # noqa: E402,F401
import skia  # noqa: E402

import_ms = (time.perf_counter() - import_start) * 1000.0

rows = int(js.SPIKE.rows)
frames = int(js.SPIKE.frames)

result = bench_paint_walk.measure(skia, rows, frames)
result["import_ms"] = import_ms
print(bench_paint_walk.report(result))

if js.SPIKE.profile:
    profile = cProfile.Profile()
    profile.enable()
    bench_paint_walk.measure(skia, rows, 5)
    profile.disable()
    pstats.Stats(profile).sort_stats("tottime").print_stats(20)
