"""Charts - a pandas plot, shown as the matplotlib figure it draws into.

``DataFrame.plot`` draws into the axes it is given, so the chart is a
matplotlib figure and ``MatplotlibFigure`` shows it: crisp, in the theme's
colors.

Needs pandas and matplotlib: ``pip install pandas nuiitivet[matplotlib]``.
"""

from __future__ import annotations

import pandas as pd
from matplotlib.figure import Figure

import nuiitivet.material as nv

FRAME = pd.DataFrame(
    {"visits": [30, 70, 40, 60, 50], "orders": [3, 7, 4, 6, 5]},
    index=["Mon", "Tue", "Wed", "Thu", "Fri"],
)


def build_root() -> nv.Widget:
    figure = Figure()
    ax = figure.subplots()
    FRAME.plot(ax=ax)  # pandas draws into the axes it is given
    return nv.MatplotlibFigure(figure, width="wt", height="wt")


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, width=480, height=320, title="pandas"))
    if png_path:
        app.render_to_png(png_path)
        print(f"Rendered {png_path}")
        return
    app.run()


if __name__ == "__main__":
    main()
