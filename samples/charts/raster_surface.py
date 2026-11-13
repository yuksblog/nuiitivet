"""Charts - a level meter drawn pixel by pixel on a RasterSurface.

The surface asks ``draw`` for exactly the device pixels it covers, so the
one-pixel ticks stay one device pixel wide on any display and the meter never
blurs. Drag the slider: the level is a State, and the surface redraws
from it.
"""

from __future__ import annotations

import nuiitivet.material as nv

_FILL = bytes((101, 85, 143, 255))  # RGBA, straight alpha
_REST = bytes((232, 222, 248, 255))
_TICK = bytes((255, 255, 255, 255))


def draw_meter(level: float, width_px: int, height_px: int) -> bytes:
    """The meter at ``level`` (0..1): rows of filled, tick and rest pixels, top to bottom."""
    filled = int(round(width_px * max(0.0, min(1.0, level))))
    row = bytearray(_FILL * filled + _REST * (width_px - filled))
    # A one-pixel tick every 16 device pixels of the filled part.
    for x in range(16, filled, 16):
        row[x * 4 : x * 4 + 4] = _TICK
    return bytes(row) * height_px


level = nv.State(0.6)


def build_root() -> nv.Widget:
    return nv.Column(
        [
            nv.Text("Drag to set the level"),
            nv.HorizontalSlider(level, width="wt"),
            # Asks draw_meter(level.value, width_px, height_px) at each change of size or level.
            nv.RasterSurface.draw(level, draw_meter, width="wt", height=48),
            nv.Text(level.map(lambda v: f"{v:.0%}")),
        ],
        gap=16,
        padding=24,
        width="wt",
    )


def main(png_path: str = "") -> None:
    app = nv.App(nv.Window(content=build_root, width=480, height=240, title="RasterSurface"))
    if png_path:
        app.render_to_png(png_path)
        print(f"Rendered {png_path}")
        return
    app.run()


if __name__ == "__main__":
    main()
