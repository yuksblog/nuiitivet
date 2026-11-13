"""Charts - a matplotlib Figure as a widget, live, in the theme's colors, with pan and zoom.

The live chart keeps its line and only moves its data: ``_plot`` runs on every
value of ``_samples`` with ``line.set_ydata``. A ``MatplotlibController`` made
beside its figure is matplotlib's pan, zoom and view history behind MD3 icon
buttons; the wheel zooms around the pointer. The bar chart is drawn once and
handed over; a click on a bar picks it, through ``mpl_connect`` as in a
matplotlib window, and writes the pick to a State. Both follow the theme:
press Dark and the lines, text and ticks take the dark scheme's colors.
"""

from __future__ import annotations

import asyncio
import math
import operator

from matplotlib.backend_bases import PickEvent
from matplotlib.figure import Figure

import nuiitivet.material as nv

light, dark = nv.ThemeFactory.from_seed_pair("#6750A4")

XS = [i / 20 for i in range(200)]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
COUNTS = [3, 7, 4, 6, 5]


class ChartScreen(nv.ComposableWidget):
    """Two charts and a theme toggle; the live one is fed for as long as the screen is mounted."""

    def __init__(self) -> None:
        super().__init__(width="wt", height="wt")
        self._is_dark = False
        self._toggle_label = nv.State("Dark")

        # The figures live with the screen, not in build(): a rebuild keeps them and their history.
        self._samples = nv.State([math.sin(x) for x in XS])
        self._live = Figure()
        live_ax = self._live.subplots()
        (self._line,) = live_ax.plot(XS, self._samples.value)
        live_ax.set_ylim(-1.2, 1.2)
        live_ax.set_title("Live")
        self._controller = nv.MatplotlibController(self._live)  # pan, zoom and the view history

        self._picked = nv.State("Click a bar")
        self._bars = Figure()
        bars_ax = self._bars.subplots()
        self._rects = list(bars_ax.bar(DAYS, COUNTS, picker=True))
        bars_ax.set_title("Static")
        self._bars.canvas.mpl_connect("pick_event", self._on_pick)

    def _plot(self, figure: Figure, ys: list[float]) -> None:
        """Runs before each draw with the latest samples: same artists, new data."""
        self._line.set_ydata(ys)

    def _on_pick(self, event: PickEvent) -> None:
        """Click: the picked bar stays full, the others fade, and the app's state follows."""
        for rect in self._rects:
            rect.set_alpha(1.0 if rect is event.artist else 0.4)
        index = self._rects.index(event.artist)
        self._picked.value = f"{DAYS[index]}: {COUNTS[index]}"
        self._bars.canvas.draw_idle()

    async def _feed(self) -> None:
        phase = 0.0
        while True:
            phase += 0.1
            self._samples.value = [math.sin(x + phase) for x in XS]
            await asyncio.sleep(0.05)

    def _toggle(self) -> None:
        self._is_dark = not self._is_dark
        self._toggle_label.value = "Light" if self._is_dark else "Dark"
        nv.App.of(self).set_theme(dark if self._is_dark else light)

    def build(self) -> nv.Widget:
        controller = self._controller
        return nv.Column(
            [
                nv.Row(
                    [
                        nv.Text("matplotlib in the app's colors"),
                        nv.Spacer(width="wt"),
                        nv.Text(self._picked, key="picked"),
                        nv.Button(self._toggle_label, on_click=self._toggle, style=nv.ButtonStyle.tonal()),
                    ],
                    gap=16,
                    cross_alignment="center",
                    width="wt",
                ),
                nv.Row(
                    [
                        nv.Column(
                            [
                                # _plot(live, samples) runs before each draw, on every change of the samples.
                                nv.MatplotlibFigure.plot(
                                    self._live, self._samples, self._plot, width="wt", height="wt", key="live"
                                ),
                                nv.Row(
                                    [
                                        nv.IconButton("home", on_click=controller.home, key="home"),
                                        nv.IconButton(
                                            "arrow_back",
                                            on_click=controller.back,
                                            disabled=controller.can_back.map(operator.not_),
                                            key="back",
                                        ),
                                        nv.IconButton(
                                            "arrow_forward",
                                            on_click=controller.forward,
                                            disabled=controller.can_forward.map(operator.not_),
                                            key="forward",
                                        ),
                                        nv.IconToggleButton("drag_pan", selected=controller.panning, key="pan"),
                                        nv.IconToggleButton("zoom_in", selected=controller.zooming, key="zoom"),
                                        nv.Text(controller.message, key="coords"),
                                    ],
                                    gap=4,
                                    cross_alignment="center",
                                    width="wt",
                                ),
                            ],
                            gap=4,
                            width="wt",
                            height="wt",
                        ),
                        nv.MatplotlibFigure(self._bars, width=260, height="wt", key="bars"),
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
