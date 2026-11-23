"""Compare RasterSurface.draw and RasterSurface.draw_in_thread on a camera-sized image.

A 4000x3000 picture is scaled to the surface on every change of its size or of
its value. One scaling takes tens of milliseconds, more than a frame, and
"Work" repeats it to stand in for heavier processing.

* With ``draw`` the scaling runs at the start of the frame, on the UI thread:
  every frame is that much longer, and the loop comes round fewer times a
  second. The switches and the slider answer late.
* With ``draw_in_thread`` the frame only starts a thread or swaps an image.

To see it, turn "Live picture" and "Animate the panel" on, or drag the window's
edge, and flip "Draw on a thread". The line under the switches says, for each
way, how many times a second the loop came round, and how long the window had
a blank subtree out of the time it was kept busy. A subtree is blank while the
layout that missed its deadline has not reached it.

The blank time is read from the framework's own layout code, so this is an
investigation script, not a sample.

Run:  python scripts/investigation/compare_raster_surface_draw.py
"""

from __future__ import annotations

import math
import time

import numpy as np
import pyglet

import nuiitivet.material as nv
from nuiitivet.layout.layout_utils import has_pending_layout

SOURCE_WIDTH, SOURCE_HEIGHT = 4000, 3000


def _make_source() -> np.ndarray:
    """A picture with fine detail: a colour gradient under a grid, as RGBA."""
    x = np.arange(SOURCE_WIDTH, dtype=np.float32)[None, :]
    y = np.arange(SOURCE_HEIGHT, dtype=np.float32)[:, None]
    picture = np.empty((SOURCE_HEIGHT, SOURCE_WIDTH, 4), dtype=np.uint8)
    picture[..., 0] = 60 + 150 * x / SOURCE_WIDTH
    picture[..., 1] = 80 + 120 * y / SOURCE_HEIGHT
    picture[..., 2] = 200 - 100 * (x + y) / (SOURCE_WIDTH + SOURCE_HEIGHT)
    picture[..., 3] = 255
    grid = ((x % 200) < 6) | ((y % 200) < 6)
    picture[grid, :3] = 245
    return picture


SOURCE = _make_source()

in_thread = nv.State(False)
live = nv.State(False)
animate = nv.State(False)
work = nv.State(2.0)
shift = nv.State(0)
panel_width = nv.State(320)
report = nv.State("Turn on Live picture and Animate the panel, or drag the window's edge.")

# What the picture is made from, as one State: the drawing reads nothing else.
view = work.combine(shift).compute(lambda times, offset: (int(round(times)), offset))

# Per way of drawing, keyed by ``in_thread``.
_busy_seconds = {False: 0.0, True: 0.0}
_blank_seconds = {False: 0.0, True: 0.0}
_turns = {False: 0, True: 0}
_last_draw_ms = 0.0


def draw_picture(value: tuple[int, int], width_px: int, height_px: int) -> np.ndarray:
    """The picture scaled to the size asked for, moved sideways by the offset; the scaling done ``times`` over."""
    global _last_draw_ms
    times, offset = value
    start = time.perf_counter()
    ys = np.linspace(0, SOURCE_HEIGHT - 1, height_px).astype(np.intp)
    xs = (np.linspace(0, SOURCE_WIDTH - 1, width_px).astype(np.intp) + offset) % SOURCE_WIDTH
    pixels = SOURCE[ys[:, None], xs[None, :]]
    for _ in range(times - 1):  # stand-in for heavier processing
        pixels = SOURCE[ys[:, None], xs[None, :]]
    _last_draw_ms = (time.perf_counter() - start) * 1000
    return pixels


def _tick(dt: float) -> None:
    """Move the picture and the panel, and add this turn of the loop to the totals."""
    if not (live.value or animate.value):
        return
    way = in_thread.value
    _busy_seconds[way] += dt
    _turns[way] += 1
    # A subtree the last layout gave up on is painted as nothing until it is laid out.
    if has_pending_layout():
        _blank_seconds[way] += dt
    now = time.perf_counter()
    if live.value:
        shift.value = int(now * 600) % SOURCE_WIDTH
    if animate.value:
        panel_width.value = int(320 + 80 * math.sin(now * 3.0))


def _line(way: bool) -> str:
    busy = _busy_seconds[way]
    rate = _turns[way] / busy if busy else 0.0
    return f"blank {_blank_seconds[way]:.1f} s of {busy:.0f} s, {rate:.0f} turns/s"


def _publish(_dt: float) -> None:
    report.value = (
        f"draw: {_line(False)}   |   draw_in_thread: {_line(True)}   |   last drawing {_last_draw_ms:.0f} ms"
    )


def _surface(threaded: bool, _index: int) -> nv.Widget:
    make = nv.RasterSurface.draw_in_thread if threaded else nv.RasterSurface.draw
    return make(view, draw_picture, width="wt", height="wt")


def build_root() -> nv.Widget:
    cells = [
        nv.Row([nv.Text(f"cell {row}-{column}", width="wt") for column in range(4)], width="wt")
        for row in range(30)
    ]
    return nv.Column(
        [
            nv.Row(
                [
                    nv.Switch(in_thread, key="in-thread"),
                    nv.Text("Draw on a thread"),
                    nv.Switch(live, key="live"),
                    nv.Text("Live picture"),
                    nv.Switch(animate, key="animate"),
                    nv.Text("Animate the panel"),
                    nv.Text(work.map(lambda times: f"Work x{int(round(times))}")),
                    nv.HorizontalSlider(work, min_value=1, max_value=6, stops=6, width=160),
                ],
                gap=12,
                cross_alignment="center",
            ),
            nv.Text(report, key="report"),
            nv.Row(
                [
                    nv.Column(cells, width=panel_width, height="wt"),
                    # One surface at a time: flipping the switch drops it and builds the other kind.
                    nv.Stack.builder(in_thread.map(lambda threaded: [threaded]), _surface, width="wt", height="wt"),
                ],
                width="wt",
                height="wt",
            ),
        ],
        gap=12,
        padding=16,
        width="wt",
        height="wt",
    )


def main() -> None:
    app = nv.App(nv.Window(content=build_root, width=1100, height=720, title="draw or draw_in_thread"))
    pyglet.clock.schedule_interval(_tick, 1 / 60)
    pyglet.clock.schedule_interval(_publish, 0.25)
    app.run()


if __name__ == "__main__":
    main()
