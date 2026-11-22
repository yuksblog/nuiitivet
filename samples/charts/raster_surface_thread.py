"""Charts - ripples from four sources, drawn on a thread.

One picture takes tens of milliseconds, more than a frame. ``draw_in_thread``
keeps that off the UI thread: the slider follows the pointer while the picture
catches up, and a resize stretches the last picture until the next one arrives.
Swap ``draw_in_thread`` for ``draw`` to feel the difference.

Needs numpy: ``pip install numpy``.
"""

from __future__ import annotations

import numpy as np

import nuiitivet.material as nv

# Where the ripples start, as fractions of the surface.
_SOURCES = ((0.2, 0.3), (0.8, 0.25), (0.35, 0.8), (0.7, 0.7))


def draw_ripples(wavelength: float, width_px: int, height_px: int) -> np.ndarray:
    """The ripples at ``wavelength`` (a fraction of the width), as RGBA rows top to bottom."""
    x = np.arange(width_px, dtype=np.float32)[None, :]
    y = np.arange(height_px, dtype=np.float32)[:, None]
    wave = np.zeros((height_px, width_px), dtype=np.float32)
    for fx, fy in _SOURCES:
        wave += np.sin(np.hypot(x - fx * width_px, y - fy * height_px) / (wavelength * width_px))
    level = (wave / len(_SOURCES) + 1.0) * 0.5
    pixels = np.empty((height_px, width_px, 4), dtype=np.uint8)
    pixels[..., 0] = 103 + level * 130
    pixels[..., 1] = 80 + level * 140
    pixels[..., 2] = 164 + level * 84
    pixels[..., 3] = 255
    return pixels


wavelength = nv.State(0.02)


def build_root() -> nv.Widget:
    return nv.Column(
        [
            nv.Text("Drag to set the wavelength"),
            nv.HorizontalSlider(wavelength, min_value=0.005, max_value=0.05, width="wt"),
            # Calls draw_ripples(wavelength.value, width_px, height_px) on a thread, one call at a time.
            nv.RasterSurface.draw_in_thread(wavelength, draw_ripples, width="wt", height="wt"),
        ],
        gap=16,
        padding=24,
        width="wt",
        height="wt",
    )


def main() -> None:
    nv.App(nv.Window(content=build_root, width=720, height=540, title="RasterSurface on a thread")).run()


if __name__ == "__main__":
    main()
