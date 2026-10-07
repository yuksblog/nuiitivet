"""The Pyodide side of the spike: ``bench_paint_walk`` over the CanvasKit shim.

Started by ``run.mjs`` under Node or by ``browser/page.mjs`` in a browser; it
does not run on its own. ``js.SPIKE`` carries the options.

With ``js.SPIKE.surface`` set, a frame is drawn onto that CanvasKit surface and
flushed, so the time includes rasterization. Without it a frame goes to a
picture recorder, which records the draw calls and rasterizes nothing.
"""

from __future__ import annotations

import cProfile
import logging
import pstats
import sys
import time
import types
from typing import Any

import js

# The framework logs a Skia call that failed and carries on, so a gap in the
# shim shows up here and nowhere else.
logging.basicConfig(level=logging.WARNING)

if "/deps" not in sys.path and getattr(js.SPIKE, "deps", True):
    sys.path.append("/deps")

import_start = time.perf_counter()
import bench_paint_walk  # noqa: E402
import nuiitivet.material  # noqa: E402,F401
import skia  # noqa: E402
from nuiitivet.layout import layout_utils  # noqa: E402

import_ms = (time.perf_counter() - import_start) * 1000.0

rows = int(js.SPIKE.rows)
frames = int(js.SPIKE.frames)
scroll = int(getattr(js.SPIKE, "scroll", 0) or 0)
layout_utils._ROW_REPLAY = bool(getattr(js.SPIKE, "replay", True))


class _SurfaceRecorder:
    """Stands in for ``skia.PictureRecorder``: draws each frame onto the surface and flushes it."""

    def beginRecording(self, bounds: Any) -> Any:
        canvas = surface.getCanvas()
        canvas.save()
        canvas.clear(0xFFFFFFFF)
        return canvas

    def finishRecordingAsPicture(self) -> None:
        surface.getCanvas().restore()
        if getattr(js.SPIKE, "flush", True):
            surface.flush()
        js.SPIKE.finish()


target: Any = skia
handle = getattr(js.SPIKE, "surface", None)
if handle is not None:
    surface = skia.Surface(int(js.SPIKE.width), int(js.SPIKE.height), handle)
    # Only the benchmark's own frame goes to the surface; the framework's row
    # recordings still use the real recorder through ``skia``.
    target = types.SimpleNamespace(PictureRecorder=_SurfaceRecorder, Rect=skia.Rect)

if scroll:
    result = bench_paint_walk.measure_scroll(target, rows, frames, scroll)
else:
    result = bench_paint_walk.measure(target, rows, frames)
result["import_ms"] = import_ms
print(bench_paint_walk.report(result))

if getattr(js.SPIKE, "profile", False):
    profile = cProfile.Profile()
    profile.enable()
    if scroll:
        bench_paint_walk.measure_scroll(target, rows, 5, scroll)
    else:
        bench_paint_walk.measure(target, rows, 5)
    profile.disable()
    pstats.Stats(profile).sort_stats("tottime").print_stats(20)
