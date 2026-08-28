"""Renderer selection - forcing CPU (software/raster) rendering.

``App.run`` chooses the drawing backend via the ``renderer`` argument:

- ``"auto"`` (default): try the GPU, fall back to software rendering silently.
- ``"gpu"``: require the GPU; raise if it cannot be initialized.
- ``"cpu"``: always render in software; never touch the GPU.

``"cpu"`` is useful for GPU-less machines, software-GL, or remote sessions that
have a display. Truly headless environments (no display at all) cannot run an
interactive window — render offscreen with ``App.render_to_png`` instead.

Run with an explicit mode, e.g.::

    python cpu_rendering.py cpu
"""

import sys

import nuiitivet.material as nv


class HomeScreen(nv.ComposableWidget):
    def __init__(self, renderer: nv.RendererMode) -> None:
        super().__init__()
        self._renderer = renderer

    def build(self) -> nv.Widget:
        return nv.Container(
            alignment="center",
            width="wt",
            height="wt",
            child=nv.Column(
                gap=16,
                children=[
                    nv.Text(f"renderer = {self._renderer!r}"),
                    nv.Button("Get Started", style=nv.ButtonStyle.filled()),
                ],
            ),
        )


def main(png_path: str = "") -> None:
    renderer: nv.RendererMode = "cpu"
    if len(sys.argv) > 1 and sys.argv[1] in ("auto", "gpu", "cpu"):
        renderer = sys.argv[1]  # type: ignore[assignment]

    app = nv.App(nv.Window(content=HomeScreen(renderer), title="Renderer Selection", width=400, height=240))
    if png_path:
        app.render_to_png(png_path)
    else:
        app.run(renderer=renderer)


if __name__ == "__main__":
    main()
