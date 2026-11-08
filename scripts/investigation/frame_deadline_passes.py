"""A screen of heavy cards laid out as a page's first frame: the pass stops at the deadline, idle time fills the blanks.

The screen is ``--rows`` rows of ``--columns`` cards, each sized fixed on
both axes, so the layout engine knows a card's rect before it measures the
card. A card holds a title, two lines of text, two chips, a progress bar and
a checkbox: the row of ``scripts/debug/lazy_table_compare.py`` folded into a
card. ``--container column`` nests a ``Row`` per card row in a ``Column``;
``--container grid`` places the cards in a ``Grid`` of fixed tracks.

One run mounts the screen fresh and lays it out inside a frame, as the first
frame after a navigation does. Frames then follow as the loop runs them: the
time the frame left over goes to idle work, which lays the pending cards out;
a frame is drawn when a card asked for one. The run reports the first pass's
time, the cards left pending by it, the frames until no card is pending, and
whether every rect the first pass set is the same at the end. ``--no-budget``
lays the screen out outside a frame: the whole screen in one pass, as before
the deadline existed.

Run::

    uv run python scripts/investigation/frame_deadline_passes.py
    uv run python scripts/investigation/frame_deadline_passes.py --container grid --rows 12 --columns 6
    uv run python scripts/investigation/frame_deadline_passes.py --no-budget

Live, under hot reload with the dev bridge::

    python -m nuiitivet.dev run scripts/investigation/frame_deadline_passes.py -- --app
"""

from __future__ import annotations

import argparse
import statistics
from time import perf_counter
from typing import Any, Dict, List, Tuple

import nuiitivet.material as nv
from nuiitivet.layout.layout_utils import has_pending_layout
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgeting.frame_clock import begin_frame, end_frame, set_frame_interval
from nuiitivet.widgeting.idle_work import run_idle_work

FRAME_SECONDS = 1.0 / 60.0
CARD_WIDTH = 220
CARD_HEIGHT = 150
GAP = 12
PADDING = 16
DEPARTMENTS = ("Sales", "Engineering", "Support", "Finance", "Design", "Legal")
STATUSES = (
    ("Active", nv.ColorRole.PRIMARY_CONTAINER, nv.ColorRole.ON_PRIMARY_CONTAINER),
    ("Pending", nv.ColorRole.TERTIARY_CONTAINER, nv.ColorRole.ON_TERTIARY_CONTAINER),
    ("Overdue", nv.ColorRole.ERROR_CONTAINER, nv.ColorRole.ON_ERROR_CONTAINER),
)


class _App:
    def __init__(self) -> None:
        self._pointer_capture_manager = PointerCaptureManager()
        self.draw_requests = 0

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.draw_requests += 1


def _chip(label: str, background: nv.ColorRole, foreground: nv.ColorRole) -> nv.Widget:
    return nv.Text(
        label,
        type_scale=nv.TypeScale.LABEL_SMALL,
        padding=(8, 2),
        style=nv.TextStyle(color=foreground),
    ).modifier(nv.background(background) | nv.corner_radius(8))


def _progress_bar(fraction: float, width: int) -> nv.Widget:
    return nv.Box(
        nv.Box(width=max(2, int(width * fraction)), height=8, background_color=nv.ColorRole.PRIMARY, corner_radius=4),
        width=width,
        height=8,
        background_color=nv.ColorRole.SURFACE_CONTAINER_HIGHEST,
        corner_radius=4,
        alignment=("start", "center"),
    )


def card(index: int) -> nv.Widget:
    """One card, sized fixed on both axes."""
    status, status_bg, status_fg = STATUSES[index % len(STATUSES)]
    inner = CARD_WIDTH - 2 * PADDING
    return nv.Box(
        nv.Column(
            [
                nv.Row(
                    [
                        nv.Text(f"Record {index + 1:04d}", type_scale=nv.TypeScale.TITLE_SMALL),
                        nv.Spacer(width="wt"),
                        nv.Checkbox(index % 4 == 0),
                    ],
                    cross_alignment="center",
                ),
                nv.Text(
                    f"Owner {index % 97:02d}, {(index * 7919) % 100_000:,} units",
                    type_scale=nv.TypeScale.BODY_MEDIUM,
                ),
                nv.Text(
                    f"Amount {(index * 1_234.5) % 99_999:,.2f}",
                    type_scale=nv.TypeScale.BODY_SMALL,
                    style=nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT),
                ),
                nv.Row(
                    [
                        _chip(
                            DEPARTMENTS[index % len(DEPARTMENTS)],
                            nv.ColorRole.SECONDARY_CONTAINER,
                            nv.ColorRole.ON_SECONDARY_CONTAINER,
                        ),
                        _chip(status, status_bg, status_fg),
                    ],
                    gap=8,
                ),
                _progress_bar(((index * 37) % 100) / 100, inner),
            ],
            gap=8,
        ),
        width=CARD_WIDTH,
        height=CARD_HEIGHT,
        padding=PADDING,
        background_color=nv.ColorRole.SURFACE_CONTAINER_LOW,
        corner_radius=12,
    )


def screen(container: str, rows: int, columns: int) -> nv.Widget:
    """The screen of cards, one ``Column`` of ``Row``s or one ``Grid`` of fixed tracks."""
    if container == "grid":
        items = [nv.GridItem(card(r * columns + c), row=r, column=c) for r in range(rows) for c in range(columns)]
        return nv.Grid(
            rows=[CARD_HEIGHT] * rows,
            columns=[CARD_WIDTH] * columns,
            row_gap=GAP,
            column_gap=GAP,
            padding=PADDING,
            children=items,
        )
    # Each row is sized by the column, the column by the window: no row is
    # measured, so the pass reaches the cards with the deadline unspent.
    width, height = _screen_size(rows, columns)
    return nv.Column(
        [
            nv.Row([card(r * columns + c) for c in range(columns)], gap=GAP, width="wt", height=CARD_HEIGHT)
            for r in range(rows)
        ],
        gap=GAP,
        padding=PADDING,
        width=width,
        height=height,
    )


def _screen_size(rows: int, columns: int) -> Tuple[int, int]:
    width = columns * CARD_WIDTH + (columns - 1) * GAP + 2 * PADDING
    height = rows * CARD_HEIGHT + (rows - 1) * GAP + 2 * PADDING
    return (width, height)


def _walk(root: nv.Widget):
    stack: List[Any] = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children_snapshot())
        built = getattr(node, "built_child", None)
        if built is not None:
            stack.append(built)


def _rects(root: nv.Widget) -> Dict[int, Tuple[int, int, int, int]]:
    """Every rect the tree holds, by widget identity."""
    found: Dict[int, Tuple[int, int, int, int]] = {}
    for node in _walk(root):
        rect = getattr(node, "layout_rect", None)
        if rect is not None:
            found[id(node)] = rect
    return found


def _count_pending(root: nv.Widget) -> int:
    return sum(1 for node in _walk(root) if getattr(node, "_layout_pending", False))


def run(container: str, rows: int, columns: int, *, budget: bool, repeat: int) -> None:
    set_frame_interval(FRAME_SECONDS)
    width, height = _screen_size(rows, columns)
    first_pass_ms: List[float] = []
    pending_after: List[int] = []
    frames_to_fill: List[int] = []
    idle_ms: List[float] = []
    moved = 0
    # The fonts and the theme load on the first screen; that screen is not counted.
    warmup = screen(container, rows, columns)
    warmup.mount(_App())
    warmup.layout(width, height)
    warmup.unmount()
    for _ in range(repeat):
        app = _App()
        root = screen(container, rows, columns)
        root.mount(app)
        started = perf_counter()
        if budget:
            begin_frame(started)
        root.layout(width, height)
        end_frame()
        first_pass_ms.append((perf_counter() - started) * 1000)
        pending_after.append(_count_pending(root))
        before = _rects(root)
        # The frames that follow: the time the pass left over goes to idle work,
        # then the loop draws a frame when one was asked for.
        frames = 0
        spent = 0.0
        left = max(0.0, FRAME_SECONDS - (perf_counter() - started))
        while has_pending_layout():
            idle_started = perf_counter()
            run_idle_work(left)
            spent += perf_counter() - idle_started
            frames += 1
            frame_started = perf_counter()
            begin_frame(frame_started)
            if root.needs_layout:
                root.layout(width, height)
            end_frame()
            left = max(0.0, FRAME_SECONDS - (perf_counter() - frame_started))
        frames_to_fill.append(frames)
        idle_ms.append(spent * 1000)
        after = _rects(root)
        moved += sum(1 for key, rect in before.items() if after.get(key) != rect)
        root.unmount()

    label = f"{container:>6} {rows}x{columns} cards | {'budget' if budget else 'no budget':>9}"
    print(
        f"{label} | first pass median {statistics.median(first_pass_ms):6.1f} ms, max {max(first_pass_ms):6.1f} ms"
        f" | frame {FRAME_SECONDS * 1000:.1f} ms, the deadline at half"
    )
    print(
        f"{'':>{len(label)}} | cards pending after the pass: mean {statistics.fmean(pending_after):5.1f}"
        f" of {rows * columns}; frames until none: max {max(frames_to_fill)},"
        f" idle time used {statistics.fmean(idle_ms):5.1f} ms"
    )
    print(f"{'':>{len(label)}} | rects moved while filling: {moved}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--container", choices=("column", "grid"), default="column")
    parser.add_argument("--rows", type=int, default=8)
    parser.add_argument("--columns", type=int, default=6)
    parser.add_argument("--repeat", type=int, default=5, help="fresh screens laid out, after one warmup screen")
    parser.add_argument("--no-budget", action="store_true", help="lay the screen out outside a frame, as before")
    parser.add_argument("--app", action="store_true", help="show the screen in a window instead of measuring")
    args = parser.parse_args()
    if args.app:
        width, height = _screen_size(args.rows, args.columns)
        nv.App(
            nv.Window(
                content=lambda: screen(args.container, args.rows, args.columns),
                title="Frame deadline: a screen of cards",
                width=width,
                height=height,
            )
        ).run()
        return
    run(args.container, args.rows, args.columns, budget=not args.no_budget, repeat=args.repeat)


if __name__ == "__main__":
    main()
