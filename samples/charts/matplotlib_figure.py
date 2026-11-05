"""Charts - a matplotlib Figure as a widget, live, in the theme's colors, taking the mouse.

The live chart keeps its line and only moves its data: ``plot`` runs on every
value of ``samples`` with ``line.set_ydata``. The bar chart is drawn once and
handed over; a click on a bar picks it, through ``mpl_connect`` as in a
matplotlib window, and writes the pick to an Observable. Both
follow the theme: press Dark and the lines, text and ticks take the dark
scheme's colors.
"""

from __future__ import annotations

import asyncio
import math

from matplotlib.backend_bases import PickEvent
from matplotlib.figure import Figure

import nuiitivet.material as nv

light, dark = nv.ThemeFactory.from_seed_pair("#6750A4")

XS = [i / 20 for i in range(200)]
samples = nv.Observable([math.sin(x) for x in XS])

live = Figure()
live_ax = live.subplots()
(line,) = live_ax.plot(XS, samples.value)
live_ax.set_ylim(-1.2, 1.2)
live_ax.set_title("Live")


def plot(figure: Figure, ys: list[float]) -> None:
    """Runs before each draw with the latest samples: same artists, new data."""
    line.set_ydata(ys)


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
COUNTS = [3, 7, 4, 6, 5]
picked = nv.Observable("Click a bar")

bars = Figure()
bars_ax = bars.subplots()
rects = list(bars_ax.bar(DAYS, COUNTS, picker=True))
bars_ax.set_title("Static")


def on_pick(event: PickEvent) -> None:
    """Click: the picked bar stays full, the others fade, and the app's state follows."""
    for rect in rects:
        rect.set_alpha(1.0 if rect is event.artist else 0.4)
    index = rects.index(event.artist)
    picked.value = f"{DAYS[index]}: {COUNTS[index]}"
    bars.canvas.draw_idle()


bars.canvas.mpl_connect("pick_event", on_pick)


class ChartScreen(nv.ComposableWidget):
    """Two charts and a theme toggle; the live one is fed for as long as the screen is mounted."""

    def __init__(self) -> None:
        super().__init__(width="wt", height="wt")
        self._is_dark = False
        self._toggle_label = nv.Observable("Dark")

    async def _feed(self) -> None:
        phase = 0.0
        while True:
            phase += 0.1
            samples.value = [math.sin(x + phase) for x in XS]
            await asyncio.sleep(0.05)

    def _toggle(self) -> None:
        self._is_dark = not self._is_dark
        self._toggle_label.value = "Light" if self._is_dark else "Dark"
        nv.App.of(self).set_theme(dark if self._is_dark else light)

    def build(self) -> nv.Widget:
        return nv.Column(
            [
                nv.Row(
                    [
                        nv.Text("matplotlib in the app's colors"),
                        nv.Spacer(width="wt"),
                        nv.Text(picked, key="picked"),
                        nv.Button(self._toggle_label, on_click=self._toggle, style=nv.ButtonStyle.tonal()),
                    ],
                    gap=16,
                    cross_alignment="center",
                    width="wt",
                ),
                nv.Row(
                    [
                        # plot(live, samples.value) runs before each draw, on every change of samples.
                        nv.MatplotlibFigure.plot(live, samples, plot, width="wt", height="wt"),
                        nv.MatplotlibFigure(bars, width=260, height="wt", key="bars"),
                    ],
                    gap=16,
                    width="wt",
                    height="wt",
                ),
            ],
            gap=16,
            padding=16,
            width="wt",
            height="wt",
        ).modifier(nv.on_mount(self._feed))


def build_root() -> nv.Widget:
    return ChartScreen()


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, width=760, height=400, title="MatplotlibFigure"))
    if png_path:
        app.render_to_png(png_path)
        print(f"Rendered {png_path}")
        return
    app.run()


if __name__ == "__main__":
    main()
