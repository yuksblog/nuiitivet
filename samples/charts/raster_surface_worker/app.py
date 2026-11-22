"""Charts - a plasma drawn by a worker function.

The drawing is pure Python and takes longer than a frame. As a worker function
it runs in a child process on the desktop and on a Web Worker in a browser, so
the slider follows the pointer while the picture catches up.

Run on the desktop:   python app.py
Run in a browser:     python -m nuiitivet.web run app.py
"""

import nuiitivet.material as nv
from jobs import draw_plasma

phase = nv.State(0.0)


def build_root() -> nv.Widget:
    return nv.Column(
        [
            nv.Text("Drag to move the waves"),
            nv.HorizontalSlider(phase, max_value=6.28, width="wt"),
            # Awaits draw_plasma(phase.value, width_px, height_px); no frame waits for it.
            nv.RasterSurface.draw(phase, draw_plasma, width="wt", height=160),
        ],
        gap=16,
        padding=24,
        width="wt",
    )


def main() -> None:
    nv.App(nv.Window(content=build_root, width=480, height=300, title="RasterSurface and a worker function")).run()


if __name__ == "__main__":
    main()
