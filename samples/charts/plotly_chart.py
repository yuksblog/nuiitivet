"""Charts - a plotly chart, written to a PNG and shown as an image.

``to_image`` writes a plotly chart as PNG bytes, and ``Image`` shows them.
Writing takes seconds, so it is done once and the bytes are kept.

Needs plotly and kaleido: ``pip install plotly kaleido``.
"""

from __future__ import annotations

import functools

import plotly.graph_objects as go

import nuiitivet.material as nv

WIDTH, HEIGHT = 480, 320


@functools.cache  # writing takes seconds: once, and the bytes are kept
def chart_png() -> bytes:
    chart = go.Figure(go.Bar(x=["Mon", "Tue", "Wed", "Thu", "Fri"], y=[3, 7, 4, 6, 5]))
    # scale=2 writes 960x640 pixels, enough for a 2x display.
    return chart.to_image(format="png", width=WIDTH, height=HEIGHT, scale=2)


def build_root() -> nv.Widget:
    return nv.Image(chart_png(), width=WIDTH, height=HEIGHT)


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, width=WIDTH, height=HEIGHT, title="plotly"))
    if png_path:
        app.render_to_png(png_path)
        print(f"Rendered {png_path}")
        return
    app.run()


if __name__ == "__main__":
    main()
