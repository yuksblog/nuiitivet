"""The drawing: on the desktop it runs in a child process, in a browser on the page's worker."""

import math

import nuiitivet.material as nv


@nv.worker(process=True)
def draw_plasma(phase: float, width_px: int, height_px: int) -> bytes:
    """Three sine waves added up, as RGBA rows top to bottom: pure Python, one pixel at a time."""
    pixels = bytearray(width_px * height_px * 4)
    for y in range(height_px):
        across = math.sin(y / height_px * 9.0 - phase)
        for x in range(width_px):
            wave = math.sin(x / width_px * 12.0 + phase) + across + math.sin((x + y) / width_px * 7.0)
            level = int((wave + 3.0) / 6.0 * 255.0)
            at = (y * width_px + x) * 4
            pixels[at] = level
            pixels[at + 1] = 80
            pixels[at + 2] = 255 - level
            pixels[at + 3] = 255
    return bytes(pixels)
