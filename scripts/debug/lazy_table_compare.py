"""Feel the difference: ``Column.builder`` against ``Column.lazy`` on a rich table.

Both sides show the same table over the same records: a header and thousands
of rows, each with a checkbox, an id, a name, a department chip, a coloured
status chip, a right-aligned amount and a progress bar. The left side builds
every row up front with ``Column.builder``; the right side builds the rows in
view with ``Column.lazy``.

Under each table a stats line reports, for that side only:

* rows built so far and the time the builders took, in total and since the
  last button press,
* rows alive right now (mounted and not yet unmounted),
* the slowest layout pass and the slowest paint of the table since the
  stats line was last refreshed (every quarter second), in milliseconds.

Scroll each side with the wheel. Press the buttons to change the records and
watch which side rebuilds what:

* Shuffle: the same records in a new order. Rows are keyed by record id, so
  the eager side moves its rows and builds none; the lazy side builds the
  rows that came into its window.
* Bump amounts: a new amount in every record. The eager side rebuilds every
  row; the lazy side rebuilds the rows in view.
* Reload: fresh records with new ids. Both sides throw their rows away.

Run interactively, both sides or one of them::

    python scripts/debug/lazy_table_compare.py [--rows 3000] [--only eager|lazy]

Under hot reload with the dev bridge::

    python -m nuiitivet.dev run scripts/debug/lazy_table_compare.py -- --rows 3000

Headless, for a timing of the first build only::

    python scripts/debug/lazy_table_compare.py --rows 3000 --png /tmp/compare.png

The lazy side asks for a layout pass on every scroll step. In the side by
side run that pass walks the eager side too, so ``--only`` gives the cleaner
per-frame numbers.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass, replace
from time import perf_counter
from typing import Callable, List, Optional, Sequence, Tuple

import nuiitivet.material as nv
from nuiitivet.observable import runtime

ROW_HEIGHT = 40
TABLE_HEIGHT = 440
SCROLLBAR_WIDTH = 12
# (header, width) per column; the first column holds the checkbox.
COLUMNS: Sequence[Tuple[str, int]] = (
    ("", 40),
    ("ID", 64),
    ("Name", 150),
    ("Dept", 110),
    ("Status", 96),
    ("Amount", 100),
    ("Progress", 140),
)
TABLE_WIDTH = sum(width for _, width in COLUMNS)

FIRST_NAMES = ("Aiko", "Ben", "Chloe", "Dai", "Emma", "Farid", "Grace", "Hiro", "Ines", "Jun", "Kira", "Leo")
LAST_NAMES = ("Sato", "Nguyen", "Garcia", "Kim", "Okafor", "Müller", "Rossi", "Tanaka", "Silva", "Novak")
DEPARTMENTS = ("Sales", "Engineering", "Support", "Finance", "Design", "Legal")
STATUSES = ("Active", "Pending", "Overdue")
STATUS_COLORS = {
    "Active": (nv.ColorRole.PRIMARY_CONTAINER, nv.ColorRole.ON_PRIMARY_CONTAINER),
    "Pending": (nv.ColorRole.TERTIARY_CONTAINER, nv.ColorRole.ON_TERTIARY_CONTAINER),
    "Overdue": (nv.ColorRole.ERROR_CONTAINER, nv.ColorRole.ON_ERROR_CONTAINER),
}


@dataclass(frozen=True)
class Record:
    id: int
    name: str
    department: str
    status: str
    amount: float
    progress: float


def generate(count: int, first_id: int, rng: random.Random) -> List[Record]:
    return [
        Record(
            id=first_id + i,
            name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            department=rng.choice(DEPARTMENTS),
            status=rng.choice(STATUSES),
            amount=rng.uniform(10, 99_999),
            progress=rng.random(),
        )
        for i in range(count)
    ]


class Model:
    """The records both tables show, and the three ways to change them."""

    def __init__(self, count: int) -> None:
        self._rng = random.Random(254)
        self._next_id = 1
        self.records: nv.Observable[List[Record]] = nv.Observable(self._fresh(count))
        self.last_action: nv.Observable[str] = nv.Observable("")

    def _fresh(self, count: int) -> List[Record]:
        records = generate(count, self._next_id, self._rng)
        self._next_id += count
        return records

    def shuffle(self) -> None:
        records = list(self.records.value)
        self._rng.shuffle(records)
        self._apply("Shuffle", records)

    def bump_amounts(self) -> None:
        records = [replace(r, amount=self._rng.uniform(10, 99_999)) for r in self.records.value]
        self._apply("Bump amounts", records)

    def reload(self) -> None:
        self._apply("Reload", self._fresh(len(self.records.value)))

    def _apply(self, name: str, records: List[Record]) -> None:
        for stats in SideStats.all:
            stats.mark_action()
        self.records.value = records
        self.last_action.value = f"Last action: {name}. Each side reports what it built since."


class SideStats:
    """Counters for one side; a clock tick copies them into the visible text."""

    all: List["SideStats"] = []

    def __init__(self) -> None:
        self.built = 0
        self.build_seconds = 0.0
        self.alive = 0
        self.layout_ms = 0.0
        self.paint_ms = 0.0
        self._built_at_action = 0
        self._seconds_at_action = 0.0
        self.text: nv.Observable[str] = nv.Observable("")
        SideStats.all.append(self)

    def mark_action(self) -> None:
        self._built_at_action = self.built
        self._seconds_at_action = self.build_seconds

    def summary(self) -> str:
        since_rows = self.built - self._built_at_action
        since_ms = (self.build_seconds - self._seconds_at_action) * 1000
        return (
            f"built {self.built:,} rows in {self.build_seconds * 1000:,.0f} ms"
            f" (since last action: +{since_rows:,} rows, {since_ms:,.0f} ms)\n"
            f"alive {self.alive:,} rows | layout {self.layout_ms:.1f} ms | paint {self.paint_ms:.1f} ms"
        )

    def refresh(self) -> None:
        self.text.value = self.summary()
        self.layout_ms = 0.0
        self.paint_ms = 0.0


class Timed(nv.Container):
    """A Container that records the slowest layout and paint of its child since the last refresh."""

    def __init__(self, child: nv.Widget, stats: SideStats) -> None:
        super().__init__(child)
        self._stats = stats

    def layout(self, width: int, height: int) -> None:
        started = perf_counter()
        super().layout(width, height)
        self._stats.layout_ms = max(self._stats.layout_ms, (perf_counter() - started) * 1000)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        started = perf_counter()
        super().paint(canvas, x, y, width, height)
        self._stats.paint_ms = max(self._stats.paint_ms, (perf_counter() - started) * 1000)


def _cell(child: nv.Widget, width: int) -> nv.Widget:
    return nv.Container(child, width=width, height=ROW_HEIGHT, padding=(8, 0), alignment=("start", "center"))


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


def _header_row() -> nv.Widget:
    cells = [
        _cell(
            nv.Text(
                title,
                type_scale=nv.TypeScale.LABEL_LARGE,
                style=nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT),
            ),
            width,
        )
        for title, width in COLUMNS
    ]
    return nv.Row(cells, cross_alignment="center").modifier(nv.background(nv.ColorRole.SURFACE_CONTAINER))


def _row_builder(stats: SideStats) -> Callable[[Record, int], nv.Widget]:
    def build(record: Record, index: int) -> nv.Widget:
        started = perf_counter()
        widths = [width for _, width in COLUMNS]
        status_bg, status_fg = STATUS_COLORS[record.status]
        cells = [
            _cell(nv.Checkbox(False), widths[0]),
            _cell(
                nv.Text(
                    f"{record.id:05d}",
                    type_scale=nv.TypeScale.BODY_SMALL,
                    style=nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT),
                ),
                widths[1],
            ),
            _cell(nv.Text(record.name, type_scale=nv.TypeScale.BODY_MEDIUM), widths[2]),
            _cell(
                _chip(record.department, nv.ColorRole.SECONDARY_CONTAINER, nv.ColorRole.ON_SECONDARY_CONTAINER),
                widths[3],
            ),
            _cell(_chip(record.status, status_bg, status_fg), widths[4]),
            _cell(
                nv.Text(
                    f"{record.amount:,.2f}",
                    type_scale=nv.TypeScale.BODY_MEDIUM,
                    width=widths[5] - 16,
                    alignment="end",
                ),
                widths[5],
            ),
            _cell(_progress_bar(record.progress, widths[6] - 16), widths[6]),
        ]
        background = nv.ColorRole.SURFACE if index % 2 == 0 else nv.ColorRole.SURFACE_CONTAINER_LOW
        row = nv.Row(cells, cross_alignment="center", height=ROW_HEIGHT).modifier(
            nv.background(background)
            | nv.on_mount(lambda: _mounted(stats, 1))
            | nv.on_unmount(lambda: _mounted(stats, -1))
        )
        stats.built += 1
        stats.build_seconds += perf_counter() - started
        return row

    return build


def _mounted(stats: SideStats, delta: int) -> None:
    stats.alive += delta


def _key(record: Record, index: int) -> int:
    del index
    return record.id


def _side(title: str, table: nv.Widget, stats: SideStats) -> nv.Widget:
    return nv.Column(
        [
            nv.Text(title, type_scale=nv.TypeScale.TITLE_MEDIUM),
            _header_row(),
            Timed(nv.VerticalScrollable(table, width=TABLE_WIDTH + SCROLLBAR_WIDTH, height=TABLE_HEIGHT), stats),
            nv.Text(
                stats.text,
                type_scale=nv.TypeScale.BODY_SMALL,
                style=nv.TextStyle(color=nv.ColorRole.ON_SURFACE_VARIANT),
            ),
        ],
        gap=8,
    ).modifier(nv.border(color=nv.ColorRole.OUTLINE_VARIANT, width=1) | nv.corner_radius(8))


def build_root(model: Model, only: Optional[str], eager_stats: SideStats, lazy_stats: SideStats) -> nv.Widget:
    sides: List[nv.Widget] = []
    if only != "lazy":
        eager = nv.Column.builder(model.records, _row_builder(eager_stats), key_fn=_key)
        sides.append(_side("Column.builder — every row up front", eager, eager_stats))
    if only != "eager":
        lazy = nv.Column.lazy(model.records, _row_builder(lazy_stats), key_fn=_key, item_height=ROW_HEIGHT)
        sides.append(_side("Column.lazy — the rows in view", lazy, lazy_stats))

    controls = nv.Row(
        [
            nv.Button("Shuffle", on_click=model.shuffle, style=nv.ButtonStyle.tonal()),
            nv.Button("Bump amounts", on_click=model.bump_amounts, style=nv.ButtonStyle.tonal()),
            nv.Button("Reload", on_click=model.reload, style=nv.ButtonStyle.outlined()),
            nv.Text(model.last_action, type_scale=nv.TypeScale.BODY_SMALL),
        ],
        gap=8,
        cross_alignment="center",
    )
    return nv.Column(
        [
            nv.Text(f"{len(model.records.value):,} records", type_scale=nv.TypeScale.TITLE_LARGE),
            controls,
            nv.Row(sides, gap=16, cross_alignment="start"),
        ],
        gap=12,
        padding=16,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rows", type=int, default=3000, help="number of records (default 3000)")
    parser.add_argument("--only", choices=("eager", "lazy"), help="show one side alone")
    parser.add_argument("--png", default="", help="render one frame to this file and print the build stats")
    args = parser.parse_args()

    # args.only = "lazy"

    model = Model(args.rows)
    eager_stats = SideStats()
    lazy_stats = SideStats()
    sides = 1 if args.only else 2
    width = sides * (TABLE_WIDTH + SCROLLBAR_WIDTH + 2) + (sides - 1) * 16 + 32
    app = nv.App(
        nv.Window(
            content=lambda: build_root(model, args.only, eager_stats, lazy_stats),
            title="Column.builder vs Column.lazy",
            width=width,
            height=TABLE_HEIGHT + 260,
        )
    )

    def refresh(_dt: float) -> None:
        for stats in SideStats.all:
            stats.refresh()

    if args.png:
        started = perf_counter()
        app.render_to_png(args.png)
        print(f"Rendered {args.png} in {(perf_counter() - started) * 1000:,.0f} ms")
        for name, stats in (("eager", eager_stats), ("lazy", lazy_stats)):
            print(f"{name}: {stats.summary()}")
        return

    runtime.clock.schedule_interval(refresh, 0.25)
    app.run()


if __name__ == "__main__":
    main()
