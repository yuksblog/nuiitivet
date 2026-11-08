"""Steady-state scroll passes over a ``Column.lazy`` table, under each collector policy.

One pass scrolls the lazy table by a number of rows and lays it out, which
builds the rows that came into view and drops the ones a view's length
behind. The passes run as frames of a scroll do: back to back, with the time
a frame leaves over given to idle work, which builds the rows ahead of the
view. ``--turn-every N`` reverses the scroll every N passes, so the rows kept
behind the view are scrolled back over.

Policies:

* ``default``: the collector as CPython ships it.
* ``disabled``: no collection at all during the passes; the floor.
* ``pacer``: :class:`GcPacer` as the frame loop drives it, one frame per
  pass, an idle call after each; the startup tree frozen, as by default.
* ``pacer-nofreeze``: the same without the freeze.

With ``--eager-alive`` an eager ``Column.builder`` table of the same rows is
built first and kept alive, so the heap holds about 1.3 M tracked objects
and a full collection shows its cost.

Run::

    uv run python scripts/investigation/lazy_scroll_passes.py --eager-alive
    uv run python scripts/investigation/lazy_scroll_passes.py --policy pacer --rows-per-pass 5
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import resource
import statistics
import subprocess
import sys
from pathlib import Path
from time import perf_counter
from typing import Callable, List, Optional

import nuiitivet.material as nv
from nuiitivet.runtime.gc_pacing import GcPacer
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgeting.idle_work import run_idle_work

_COMPARE = Path(__file__).resolve().parents[1] / "debug" / "lazy_table_compare.py"
_spec = importlib.util.spec_from_file_location("lazy_table_compare", _COMPARE)
assert _spec is not None and _spec.loader is not None
compare = importlib.util.module_from_spec(_spec)
sys.modules["lazy_table_compare"] = compare
_spec.loader.exec_module(compare)

FRAME_SECONDS = 1.0 / 60.0


class _App:
    def __init__(self) -> None:
        self._pointer_capture_manager = PointerCaptureManager()

    def invalidate(self, immediate: bool = False) -> None:
        pass


class _Collections:
    """Counts the collector's runs and the time inside them, per generation."""

    def __init__(self) -> None:
        self.count = [0, 0, 0]
        self.seconds = [0.0, 0.0, 0.0]
        self._started = 0.0

    def __call__(self, phase: str, info: dict) -> None:
        if phase == "start":
            self._started = perf_counter()
        else:
            generation = int(info["generation"])
            self.count[generation] += 1
            self.seconds[generation] += perf_counter() - self._started

    def summary(self) -> str:
        parts = [f"gen{g} {self.count[g]}x {self.seconds[g] * 1000:.1f} ms" for g in range(3) if self.count[g]]
        return ", ".join(parts) if parts else "none"


def _mounted_table(records: nv.Observable, builder: Callable, lazy: bool) -> nv.Widget:
    if lazy:
        column = nv.Column.lazy(records, builder, key_fn=compare._key, item_height=compare.ROW_HEIGHT)
    else:
        column = nv.Column.builder(records, builder, key_fn=compare._key)
    scroller = nv.VerticalScrollable(column, width=compare.TABLE_WIDTH, height=compare.TABLE_HEIGHT)
    scroller.mount(_App())
    scroller.layout(compare.TABLE_WIDTH, compare.TABLE_HEIGHT)
    return scroller


def _peak_rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024


def run(
    policy: str,
    *,
    rows: int,
    rows_per_pass: int,
    passes: int,
    eager_alive: bool,
    turn_every: int,
    middle_budget: Optional[int],
    old_budget: Optional[int],
) -> None:
    model = compare.Model(rows)
    stats = compare.SideStats()
    builder = compare._row_builder(stats)
    eager = _mounted_table(model.records, builder, lazy=False) if eager_alive else None
    scroller = _mounted_table(model.records, builder, lazy=True)
    controller = scroller._controller
    gc.collect()
    alive = len(gc.get_objects())
    rss_before = _peak_rss_mb()

    pacer: Optional[GcPacer] = None
    if policy == "disabled":
        gc.disable()
    elif policy.startswith("pacer"):
        knobs = {}
        if middle_budget is not None:
            knobs["middle_budget"] = middle_budget
        if old_budget is not None:
            knobs["old_budget"] = old_budget
        pacer = GcPacer(freeze=policy != "pacer-nofreeze", **knobs)
        pacer.install()
        pacer.after_frame(0.0)

    collections = _Collections()
    gc.callbacks.append(collections)
    step_px = rows_per_pass * compare.ROW_HEIGHT
    end_px = rows * compare.ROW_HEIGHT - compare.TABLE_HEIGHT
    offset = 0
    direction = 1
    times: List[float] = []
    allocated: List[int] = []
    built_in_passes = 0
    built_in_idle = 0
    now = 0.0
    try:
        for index in range(passes):
            if turn_every and index and index % turn_every == 0:
                direction = -direction
            offset += direction * step_px
            if offset > end_px:
                offset = 0
            offset = max(0, offset)
            now += FRAME_SECONDS
            started = perf_counter()
            before = gc.get_count()[0]
            built_before = stats.built
            if pacer is not None:
                pacer.before_frame()
            controller.scroll_to(offset)
            scroller.layout(compare.TABLE_WIDTH, compare.TABLE_HEIGHT)
            allocated.append(gc.get_count()[0] - before)
            if pacer is not None:
                pacer.after_frame(now)
                pacer.idle(now)
            elapsed = perf_counter() - started
            times.append(elapsed)
            built_in_passes += stats.built - built_before
            # What the frame left over goes to the idle work, as the loop does.
            built_before = stats.built
            run_idle_work(max(0.0, FRAME_SECONDS - elapsed))
            built_in_idle += stats.built - built_before
        held = len(scroller._child._laid_out_children)
        waiting = len(gc.get_objects()) - alive
        rss_growth = _peak_rss_mb() - rss_before
        # What a quiet moment would pay: the full collection the pacer runs
        # there, over the heap as this policy left it.
        started = perf_counter()
        if pacer is not None:
            pacer.idle(now + pacer._quiet_seconds)
        else:
            gc.collect()
        full_ms = (perf_counter() - started) * 1000
    finally:
        gc.callbacks.remove(collections)
        if pacer is not None:
            pacer.uninstall()
        gc.enable()

    ms = sorted(t * 1000 for t in times)
    p95 = ms[int(len(ms) * 0.95) - 1]
    print(
        f"{policy:>13} | {rows_per_pass:2d} rows/pass | mean {statistics.fmean(ms):5.1f} | p95 {p95:5.1f} | "
        f"max {ms[-1]:6.1f} ms | alloc/pass {statistics.fmean(allocated):7.0f} | {collections.summary()}"
    )
    print(
        f"{'':>13} | rows built: {built_in_passes / passes:.1f} per pass inside the frame, "
        f"{built_in_idle / passes:.1f} per pass in idle time; {held} rows held at the end"
    )
    print(
        f"{'':>13} | after the passes: {waiting:,} tracked objects more than before, peak RSS +{rss_growth:.0f} MB, "
        f"the quiet collection {full_ms:.1f} ms"
    )
    print(f"{'':>13} | {alive:,} tracked objects alive before the passes" + (" (eager table alive)" if eager else ""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--rows-per-pass", type=int, default=11)
    parser.add_argument("--passes", type=int, default=120)
    parser.add_argument("--eager-alive", action="store_true", help="keep an eager table of the same rows alive")
    parser.add_argument("--turn-every", type=int, default=0, help="reverse the scroll every N passes; 0 never")
    parser.add_argument("--middle-budget", type=int, default=None, help="the pacer's middle_budget")
    parser.add_argument("--old-budget", type=int, default=None, help="the pacer's old_budget")
    parser.add_argument(
        "--policy",
        choices=("default", "disabled", "pacer", "pacer-nofreeze", "all"),
        default="all",
        help="'all' runs each policy in its own process, so one run's heap never shapes the next",
    )
    args = parser.parse_args()
    if args.policy == "all":
        for policy in ("default", "disabled", "pacer", "pacer-nofreeze"):
            argv = [a for a in sys.argv[1:] if a not in ("--policy", "all")]
            subprocess.run([sys.executable, __file__, *argv, "--policy", policy], check=True)
        return
    run(
        args.policy,
        rows=args.rows,
        rows_per_pass=args.rows_per_pass,
        passes=args.passes,
        eager_alive=args.eager_alive,
        turn_every=args.turn_every,
        middle_budget=args.middle_budget,
        old_budget=args.old_budget,
    )


if __name__ == "__main__":
    main()
