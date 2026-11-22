"""Charts - a seaborn chart, shown as the matplotlib figure it draws into.

seaborn draws into the axes it is given, so the chart is a matplotlib figure
and ``MatplotlibFigure`` shows it: crisp, in the theme's colors.

Needs seaborn and matplotlib: ``pip install seaborn nuiitivet[matplotlib]``.
"""

from __future__ import annotations

import seaborn as sns
from matplotlib.figure import Figure

import nuiitivet.material as nv

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
COUNTS = [3, 7, 4, 6, 5]


def build_root() -> nv.Widget:
    figure = Figure()
    ax = figure.subplots()
    sns.barplot(x=DAYS, y=COUNTS, ax=ax)  # seaborn draws into the axes it is given
    return nv.MatplotlibFigure(figure, width="wt", height="wt")


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, width=480, height=320, title="seaborn"))
    if png_path:
        app.render_to_png(png_path)
        print(f"Rendered {png_path}")
        return
    app.run()


if __name__ == "__main__":
    main()
