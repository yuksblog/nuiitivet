"""Frame counter — proving on-demand drawing produces zero idle frames.

nuiitivet draws **on demand**: a frame is produced only when a widget has
invalidated. An idle window — nothing animating, no interaction — draws zero
frames per second, so a static screen costs no CPU or battery.

This sample wraps the app's per-frame render call with a counter and prints the
frame rate once a second. Leave the window untouched and watch it settle to
``0 fps``. Click the button (or hover it) and you will see a brief burst of
frames as the tree repaints, then silence again.

``draw_fps`` is an upper-bound throttle, not a mandate to draw. Pass a value to
cap the rate while still only drawing when something changed::

    python on_demand_drawing.py 30   # cap at 30 fps, still 0 fps when idle

Run with no argument for pure on-demand (the default)::

    python on_demand_drawing.py
"""

from __future__ import annotations

import sys
import threading
import time
from typing import Optional

import nuiitivet.material as nv


class FrameCounterApp(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count = nv.Observable(0)

    def increment(self) -> None:
        self.count.value += 1

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=16,
                padding=24,
                children=[
                    nv.Text("Idle = 0 fps. Watch the console."),
                    nv.Text(self.count.map(lambda n: f"clicks: {n}")),
                    nv.Button("Repaint", on_click=self.increment),
                ],
            ),
        )


def _install_frame_counter(app: nv.App) -> None:
    """Wrap ``app._render_frame`` to count frames and log fps every second."""
    original_render_frame = app._render_frame
    state = {"frames": 0, "last_report": time.perf_counter()}

    def counting_render_frame(dt: float) -> None:
        state["frames"] += 1
        original_render_frame(dt)

    app._render_frame = counting_render_frame  # type: ignore[method-assign]

    # Report from a background daemon thread rather than a scheduled clock
    # callback: reporting must never invalidate the tree, or it would keep the
    # on-demand loop awake and defeat the very thing being measured.
    def report_loop() -> None:
        while True:
            time.sleep(1.0)
            now = time.perf_counter()
            elapsed = now - state["last_report"]
            frames = state["frames"]
            fps = frames / elapsed if elapsed > 0 else 0.0
            print(f"{fps:5.1f} fps  ({frames} frames in {elapsed:.2f}s)")
            state["frames"] = 0
            state["last_report"] = now

    threading.Thread(target=report_loop, daemon=True).start()


def main(png_path: str = "") -> None:
    draw_fps: Optional[float] = None
    if len(sys.argv) > 1:
        try:
            draw_fps = float(sys.argv[1])
        except ValueError:
            draw_fps = None

    app = nv.App(
        content=FrameCounterApp(),
        title="On-demand Frame Counter",
        width=360,
        height=220,
    )

    if png_path:
        app.render_to_png(png_path)
        return

    _install_frame_counter(app)
    app.run(draw_fps=draw_fps)


if __name__ == "__main__":
    main()
