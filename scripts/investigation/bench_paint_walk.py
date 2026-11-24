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

``--scroll`` times one frame of a scroll under a viewport. ``--row mixed``
swaps the row for one of widgets that draw without a container: a
``RadioButton``, an ``Icon`` with a badge stuck to it, a ``Text`` with a
tooltip, a ``Spacer``, two progress indicators and a divider.

``--board`` times a drag on a board: cards of 300x80 placed on a ``Stack``,
each a bordered, rounded ``Container`` of three coloured boxes, one card moved
every frame and marked as its pointer handler marks it. The cards step
diagonally out of the 1200x800 canvas; ``--in-view`` keeps all of them inside.
``--no-replay`` paints every child directly.

Run:  python scripts/investigation/bench_paint_walk.py [--rows N] [--frames N] [--wrap NAME] [--profile]
      python scripts/investigation/bench_paint_walk.py --scroll PX [--row NAME]
      python scripts/investigation/bench_paint_walk.py --board N [--in-view] [--no-replay]
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
BOARD_WIDTH = 1200
BOARD_HEIGHT = 800

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
ROWS = ("settings", "mixed")


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


def _mixed_row(nv: Any, i: int) -> Any:
    return nv.Column(
        children=[
            nv.Row(
                gap=12,
                padding=8,
                cross_alignment="center",
                children=[
                    nv.RadioButton(i),
                    nv.Icon("star").modifier(nv.stick(nv.SmallBadge())),
                    nv.Text(f"Download number {i}").modifier(nv.tooltip(nv.Text(f"Tip {i}"))),
                    nv.Spacer(width=24),
                    nv.LinearProgressIndicator((i % 10) / 10.0, width=160),
                    nv.CircularProgressIndicator((i % 7) / 7.0),
                ],
            ),
            nv.HorizontalDivider(),
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


def measure_scroll(skia: Any, rows: int, frames: int, viewport: int, row: str = "settings") -> dict[str, float]:
    """Time one frame of a scroll: the list under a viewport, moved 7 px per frame."""
    import nuiitivet.material as nv
    from nuiitivet.scrolling import ScrollController, ScrollDirection
    from nuiitivet.testing import mount

    controller = ScrollController()
    build = _mixed_row if row == "mixed" else _row
    content = nv.Column(children=[build(nv, i) for i in range(rows)])
    if row == "mixed":
        content = nv.RadioGroup(content, value=0)
    tree = nv.VerticalScrollable(content, controller=controller, height=viewport)
    out: dict[str, float] = {}

    with mount(tree, theme=nv.ThemeFactory.light("#6750A4"), leak_check="off") as host:
        host.layout(WIDTH, viewport)
        row_height = max(1, content.layout_rect[3] // rows)
        limit = max(1, rows * row_height - viewport)
        out["visible_widgets"] = float(viewport // row_height * (_count_widgets(content) - 1) // rows)

        def paint() -> None:
            recorder = skia.PictureRecorder()
            canvas = recorder.beginRecording(skia.Rect.MakeWH(WIDTH, viewport))
            host.root.paint(canvas, 0, 0, WIDTH, viewport)
            recorder.finishRecordingAsPicture()

        paint()
        offset = 0.0
        samples = []
        for _ in range(frames):
            offset = (offset + 7.0) % limit
            controller.scroll_to(offset, axis=ScrollDirection.VERTICAL)
            start = time.perf_counter()
            paint()
            samples.append((time.perf_counter() - start) * 1000.0)
        out["scroll_frame_ms"] = statistics.median(samples)
        out["scroll_frame_max_ms"] = max(samples)
    return out


def measure_board(skia: Any, cards: int, frames: int, in_view: bool) -> dict[str, float]:
    """Time one frame of a drag: one card of a board moved, the others still."""
    import nuiitivet.material as nv
    from nuiitivet.layout.layout_utils import layout_child_if_needed
    from nuiitivet.testing import mount

    if in_view:
        positions = [[20 + (i * 37) % 860, 20 + (i * 53) % 680] for i in range(cards)]
    else:
        positions = [[50 + 10 * i, 50 + 10 * i] for i in range(cards)]

    class Board(nv.Stack):
        def layout(self, width: int, height: int) -> None:
            nv.Widget.layout(self, width, height)
            for child, (x, y) in zip(self.children_snapshot(), positions):
                layout_child_if_needed(child, 300, 80, sized_by_parent=True)
                child.set_layout_rect(x, y, 300, 80)

    def square() -> Any:
        return nv.Container(width=50, height=80).modifier(nv.background("#4CAF50"))

    def card() -> Any:
        body = nv.Container(width="wt", height=80).modifier(nv.background("#FFC107"))
        row = nv.Row([square(), body, square()], width=300, height=80)
        return nv.Container(row, width=300, height=80).modifier(nv.border("#000000", 1) | nv.corner_radius(5))

    board = Board([card() for _ in range(cards)], width="wt", height="wt")
    background = nv.Container(width="wt", height="wt").modifier(nv.background("#90CAF9"))
    tree = nv.Stack([background, board], width="wt", height="wt")
    moved = board.children_snapshot()[0]
    out: dict[str, float] = {}

    with mount(tree, theme=nv.ThemeFactory.light("#6750A4"), leak_check="off") as host:

        def paint() -> None:
            recorder = skia.PictureRecorder()
            canvas = recorder.beginRecording(skia.Rect.MakeWH(BOARD_WIDTH, BOARD_HEIGHT))
            host.root.paint(canvas, 0, 0, BOARD_WIDTH, BOARD_HEIGHT)
            recorder.finishRecordingAsPicture()

        host.layout(BOARD_WIDTH, BOARD_HEIGHT)
        start = time.perf_counter()
        paint()
        out["first_paint_ms"] = (time.perf_counter() - start) * 1000.0
        out["widgets"] = float(_count_widgets(host.root))

        layouts = []
        paints = []
        for frame in range(frames + 1):
            positions[0][0] = 20 + (frame * 5) % 400
            positions[0][1] = 20 + (frame * 3) % 300
            board.mark_needs_layout()
            # What delivering the pointer event to the card's handler does.
            moved._mark_replay_dirty()
            start = time.perf_counter()
            host.layout(BOARD_WIDTH, BOARD_HEIGHT)
            middle = time.perf_counter()
            paint()
            end = time.perf_counter()
            if frame:
                layouts.append((middle - start) * 1000.0)
                paints.append((end - middle) * 1000.0)
            else:
                out["drag_first_paint_ms"] = (end - middle) * 1000.0
        out["drag_layout_ms"] = statistics.median(layouts)
        out["drag_paint_ms"] = statistics.median(paints)
        out["drag_paint_max_ms"] = max(paints)
    return out


def report(result: dict[str, float]) -> str:
    return json.dumps({"python": sys.version.split()[0], **{k: round(v, 2) for k, v in result.items()}})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100, help="rows in the list (8 widgets per row)")
    parser.add_argument("--frames", type=int, default=20, help="frames to time per case")
    parser.add_argument("--wrap", choices=WRAPPERS, default="none", help="wrapper between the list and its rows")
    parser.add_argument("--scroll", type=int, metavar="PX", help="time a scroll frame under a viewport this tall")
    parser.add_argument("--row", choices=ROWS, default="settings", help="what a row holds, with --scroll")
    parser.add_argument("--board", type=int, metavar="N", help="time a drag frame on a board of this many cards")
    parser.add_argument("--in-view", action="store_true", help="keep every card inside the canvas, with --board")
    parser.add_argument("--no-replay", action="store_true", help="paint every child directly")
    parser.add_argument("--profile", action="store_true", help="also print a cProfile of the run")
    args = parser.parse_args()

    _add_src_to_path()
    from nuiitivet.rendering.skia.skia_module import get_skia

    skia = get_skia()
    if skia is None:
        print("skia unavailable; cannot run benchmark", file=sys.stderr)
        return 1

    if args.no_replay:
        from nuiitivet.layout import layout_utils

        layout_utils._REPLAY = False

    if args.board:
        print(report(measure_board(skia, args.board, args.frames, args.in_view)))
        return 0

    if args.scroll:
        print(report(measure_scroll(skia, args.rows, args.frames, args.scroll, args.row)))
        return 0

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
