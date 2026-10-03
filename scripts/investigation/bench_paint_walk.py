"""Benchmark the paint tree walk on a list of Material widgets.

The scene is a ``Column`` of rows, 8 widgets per row: a ``Checkbox``, two
``Text`` in a ``Column``, a ``Switch`` and a tonal ``Button``. It reports, per
frame:

* ``paint_full_ms``:     ``root.paint(...)`` over the whole tree.
* ``paint_viewport_ms``: the same paint clipped to 800 px, as a scrolled window
  issues it.
* ``layout_resize_ms``:  a re-layout after the width changed.
* ``edit_one_text_ms``:  one ``Text`` changed, then settled.

Paint goes to a ``skia.PictureRecorder``, so the numbers hold the Python tree
walk and the draw calls and no rasterization.

``measure`` takes the Skia module as an argument: ``spike_web_pyodide`` runs the
same function on Pyodide with a CanvasKit adapter in its place.

``--wrap`` puts a wrapper between the list and its rows, to measure what a
container below that wrapper pays. A row wrapper (``composable``, ``card``, ...)
wraps each row. A list wrapper puts the whole list under one wrapper that hides
most of it: ``scroll`` and ``clip`` show 800 px of it, ``translate`` moves it
off the canvas.

Run:  python scripts/investigation/bench_paint_walk.py [--rows N] [--frames N] [--wrap NAME] [--profile]
"""

from __future__ import annotations

import argparse
import cProfile
import json
import os
import pstats
import statistics
import sys
import time
from typing import Any, Callable

WIDTH = 900
ROW_HEIGHT = 72
VIEWPORT_HEIGHT = 800

ROW_WRAPPERS = (
    "composable",
    "container",
    "card",
    "stack",
    "deck",
    "geometry",
    "cross_aligned",
    "opacity",
    "visible",
    "clickable",
    "will_pop",
)
LIST_WRAPPERS = ("scroll", "clip", "translate")
WRAPPERS = ("none", *ROW_WRAPPERS, *LIST_WRAPPERS)


def _add_src_to_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def _wrap_row(nv: Any, wrap: str, row: Any) -> Any:
    if wrap == "composable":

        class _Host(nv.ComposableWidget):
            def build(self) -> Any:
                return row

        return _Host()
    if wrap == "container":
        return nv.Container(row)
    if wrap == "card":
        return nv.Card(row, style=nv.CardStyle.filled())
    if wrap == "stack":
        return nv.Stack([row])
    if wrap == "deck":
        return nv.Deck([row])
    if wrap == "geometry":
        return nv.Geometry(row)
    if wrap == "cross_aligned":
        return nv.CrossAligned(row, "start")
    if wrap == "opacity":
        return row.modifier(nv.opacity(1.0))
    if wrap == "visible":
        return row.modifier(nv.visible(True))
    if wrap == "clickable":
        return row.modifier(nv.clickable(lambda: None))
    if wrap == "will_pop":
        return row.modifier(nv.will_pop(lambda: True))
    return row


def _wrap_list(nv: Any, wrap: str, rows: int, content: Any) -> Any:
    if wrap == "scroll":
        return nv.Column(children=[nv.VerticalScrollable(content, height=VIEWPORT_HEIGHT)])
    if wrap == "clip":
        return nv.Column(children=[nv.Container(content, height=VIEWPORT_HEIGHT).modifier(nv.clip())])
    if wrap == "translate":
        return nv.Column(children=[content.modifier(nv.translate((0, -rows * ROW_HEIGHT)))])
    return content


def build_scene(rows: int, wrap: str = "none") -> Any:
    import nuiitivet.material as nv

    def row(i: int) -> Any:
        return _wrap_row(nv, wrap, _row(nv, i))

    return _wrap_list(nv, wrap, rows, nv.Column(children=[row(i) for i in range(rows)]))


def _row(nv: Any, i: int) -> Any:
    return nv.Row(
        gap=12,
        padding=8,
        children=[
            nv.Checkbox(i % 2 == 0),
            nv.Column(
                children=[
                    nv.Text(f"Setting number {i}"),
                    nv.Text(f"Description of what setting {i} changes"),
                ],
            ),
            nv.Switch(i % 3 == 0),
            nv.Button("Apply", style=nv.ButtonStyle.tonal()),
        ],
    )


def _median_ms(fn: Callable[[], None], frames: int) -> float:
    # One warm-up frame (first paint primes lazy caches) then measure.
    fn()
    samples = []
    for _ in range(frames):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return statistics.median(samples)


def _below(widget: Any) -> list:
    """The widgets directly below ``widget``: its children, and what a composable built."""
    below = list(widget.children_snapshot())
    built = getattr(widget, "built_child", None)
    if built is not None and built not in below:
        below.append(built)
    return below


def _count_widgets(root: Any) -> int:
    return 1 + sum(_count_widgets(child) for child in _below(root))


def _first_text(root: Any) -> Any:
    from nuiitivet.material import Text

    if isinstance(root, Text):
        return root
    for child in _below(root):
        found = _first_text(child)
        if found is not None:
            return found
    return None


def measure(skia: Any, rows: int, frames: int, wrap: str = "none") -> dict[str, float]:
    import nuiitivet.material as nv
    from nuiitivet.testing import mount

    height = rows * ROW_HEIGHT
    out: dict[str, float] = {}

    start = time.perf_counter()
    tree = build_scene(rows, wrap)
    out["build_ms"] = (time.perf_counter() - start) * 1000.0

    with mount(tree, theme=nv.ThemeFactory.light("#6750A4"), leak_check="off") as host:

        def record(clip_height: int | None) -> None:
            recorder = skia.PictureRecorder()
            canvas = recorder.beginRecording(skia.Rect.MakeWH(WIDTH, height))
            if clip_height is not None:
                canvas.save()
                canvas.clipRect(skia.Rect.MakeWH(WIDTH, clip_height))
            host.root.paint(canvas, 0, 0, WIDTH, height)
            if clip_height is not None:
                canvas.restore()
            recorder.finishRecordingAsPicture()

        start = time.perf_counter()
        host.layout(WIDTH, height)
        record(None)
        out["first_frame_ms"] = (time.perf_counter() - start) * 1000.0
        out["widgets"] = float(_count_widgets(host.root))

        widths = [WIDTH - 40, WIDTH]

        def resize() -> None:
            widths.reverse()
            host.layout(widths[0], height)

        label = _first_text(host.root)
        edits = [0]

        def edit_one() -> None:
            edits[0] += 1
            label.text = f"Changed {edits[0]}"
            host.settle()

        out["layout_resize_ms"] = _median_ms(resize, frames)
        host.layout(WIDTH, height)
        out["edit_one_text_ms"] = _median_ms(edit_one, frames)
        out["paint_full_ms"] = _median_ms(lambda: record(None), frames)
        out["paint_viewport_ms"] = _median_ms(lambda: record(VIEWPORT_HEIGHT), frames)
    return out


def report(result: dict[str, float]) -> str:
    return json.dumps({"python": sys.version.split()[0], **{k: round(v, 2) for k, v in result.items()}})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100, help="rows in the list (8 widgets per row)")
    parser.add_argument("--frames", type=int, default=20, help="frames to time per case")
    parser.add_argument("--wrap", choices=WRAPPERS, default="none", help="wrapper between the list and its rows")
    parser.add_argument("--profile", action="store_true", help="also print a cProfile of the run")
    args = parser.parse_args()

    _add_src_to_path()
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia()
    if skia is None:
        print("skia unavailable; cannot run benchmark", file=sys.stderr)
        return 1

    print(report(measure(skia, args.rows, args.frames, args.wrap)))

    if args.profile:
        profile = cProfile.Profile()
        profile.enable()
        measure(skia, args.rows, 5, args.wrap)
        profile.disable()
        pstats.Stats(profile).sort_stats("tottime").print_stats(20)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
