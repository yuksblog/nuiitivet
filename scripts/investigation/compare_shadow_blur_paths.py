"""Compare the two ways to blur an MD3 elevation shadow (issue #661).

The elevation shadow is now two layers per level rather than one, so whatever a
single blur pass costs, it is paid twice. ``BackgroundRenderer._draw_shadow``
already knows two ways to blur:

* **maskfilter** — ``drawRRect`` with a blur ``MaskFilter``. What ships. Skia
  blurs a round rect's mask analytically, so no offscreen layer is allocated.
* **imagefilter** — ``saveLayer`` with a blur ``ImageFilter``. The fallback,
  taken when the MaskFilter path cannot draw. Each pass allocates an offscreen
  layer padded by ``sigma * 3`` on every side.

The two are visually indistinguishable on a rounded rect, which is what makes
the cheaper one safe to ship: it removes an allocation per layer, and the
two-layer shadow would otherwise pay that twice per repaint.

This renders both, side by side, and reports the sampled darkness profile and
the per-draw cost of each, so the choice stays open to re-checking.

Run:  python scripts/investigation/compare_shadow_blur_paths.py [--out PATH] [--reps N]
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import skia  # noqa: E402

from nuiitivet.material.theme.color_role import ColorRole  # noqa: E402
from nuiitivet.material.theme.elevation import md3_elevation_to_shadow  # noqa: E402
from nuiitivet.rendering import background_renderer as br_mod  # noqa: E402
from nuiitivet.rendering.background_renderer import BackgroundRenderer  # noqa: E402
from nuiitivet.rendering.shadow import ShadowLayers  # noqa: E402

CARD_W = 120
CARD_H = 70
CORNER = 12.0
PAD = 44
CELL_W = CARD_W + PAD * 2
CELL_H = CARD_H + PAD * 2
LEVELS = (1, 2, 3, 4, 5)


class _Owner:
    """The minimum surface ``BackgroundRenderer`` reads from its owner."""

    def __init__(self, shadows: ShadowLayers) -> None:
        self._parent = None
        self._mounted = False
        self.bgcolor = None
        self.corner_radius = CORNER
        self.corner_radii = (CORNER,) * 4
        self.border_width = 0
        self.border_color = None
        self.shadows = shadows


def _concrete(layers: ShadowLayers) -> ShadowLayers:
    """Bake ``md.sys.color.shadow`` in: there is no mounted theme to resolve it."""
    return tuple(
        dataclasses.replace(layer, color=("#000000", layer.color[1]))
        if isinstance(layer.color, tuple) and layer.color[0] is ColorRole.SHADOW
        else layer
        for layer in layers
    )


class _ForceImageFilter:
    """Make the MaskFilter path bail out so ``_draw_shadow`` takes the fallback."""

    def __enter__(self) -> "_ForceImageFilter":
        self._saved = br_mod.make_blur_mask_filter
        br_mod.make_blur_mask_filter = lambda *_a, **_k: None  # type: ignore[assignment]
        return self

    def __exit__(self, *_exc: object) -> None:
        br_mod.make_blur_mask_filter = self._saved  # type: ignore[assignment]


def _paint_cell(canvas, ox: int, oy: int, layers: ShadowLayers) -> None:
    """Draw one card with its shadow at cell origin (ox, oy)."""
    BackgroundRenderer(_Owner(_concrete(layers))).paint_shadow_and_background(
        canvas, ox + PAD, oy + PAD, CARD_W, CARD_H
    )
    body = skia.RRect.MakeRectXY(
        skia.Rect.MakeXYWH(ox + PAD, oy + PAD, CARD_W, CARD_H), CORNER, CORNER
    )
    canvas.drawRRect(body, skia.Paint(Color=skia.ColorWHITE, AntiAlias=True))


def _profile(layers: ShadowLayers, *, force_image: bool, length: int = 14) -> list[int]:
    """Sample darkness below the card's bottom edge, 0 (white) .. 255 (black)."""
    surface = skia.Surface(CELL_W, CELL_H)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    if force_image:
        with _ForceImageFilter():
            _paint_cell(canvas, 0, 0, layers)
    else:
        _paint_cell(canvas, 0, 0, layers)
    pixels = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    col = PAD + CARD_W // 2
    return [255 - int(pixels[PAD + CARD_H + step][col][0]) for step in range(length)]


def _time_draw(layers: ShadowLayers, *, force_image: bool, reps: int) -> float:
    """Return the best per-draw time in microseconds over *reps* repetitions."""
    surface = skia.Surface(CELL_W, CELL_H)
    canvas = surface.getCanvas()
    owner = _Owner(_concrete(layers))
    renderer = BackgroundRenderer(owner)

    def _run() -> None:
        canvas.clear(skia.ColorWHITE)
        renderer.paint_shadow_and_background(canvas, PAD, PAD, CARD_W, CARD_H)

    ctx = _ForceImageFilter() if force_image else None
    if ctx is not None:
        ctx.__enter__()
    try:
        _run()  # warm up
        best = float("inf")
        for _ in range(reps):
            start = time.perf_counter()
            _run()
            best = min(best, time.perf_counter() - start)
    finally:
        if ctx is not None:
            ctx.__exit__()
    return best * 1e6


def _render_sheet(path: str) -> None:
    """Write a two-row sheet: maskfilter on top, imagefilter below."""
    surface = skia.Surface(CELL_W * len(LEVELS), CELL_H * 2 + 28)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)

    font = skia.Font(skia.Typeface(""), 13)
    label = skia.Paint(Color=skia.ColorBLACK, AntiAlias=True)

    for row, force_image in enumerate((False, True)):
        oy = row * CELL_H + 28
        canvas.drawString(
            "imagefilter (saveLayer + blur ImageFilter) -- the fallback"
            if force_image
            else "maskfilter (drawRRect + blur MaskFilter) -- ships today",
            8.0,
            float(oy - 8),
            font,
            label,
        )
        for col, level in enumerate(LEVELS):
            ox = col * CELL_W
            layers = md3_elevation_to_shadow(level)
            if force_image:
                with _ForceImageFilter():
                    _paint_cell(canvas, ox, oy, layers)
            else:
                _paint_cell(canvas, ox, oy, layers)
            canvas.drawString(f"level {level}", float(ox + PAD), float(oy + PAD - 10), font, label)

    surface.makeImageSnapshot().save(path, skia.kPNG)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="shadow_blur_paths.png", help="where to write the sheet")
    parser.add_argument("--reps", type=int, default=400, help="timing repetitions per arm")
    args = parser.parse_args()

    print("Darkness below the bottom edge, 0px..13px (0 = white, 255 = black)\n")
    for level in LEVELS:
        layers = md3_elevation_to_shadow(level)
        mask = _profile(layers, force_image=False)
        image = _profile(layers, force_image=True)
        drift = max(abs(a - b) for a, b in zip(image, mask))
        print(f"level {level}")
        print(f"  maskfilter   {mask}")
        print(f"  imagefilter  {image}")
        print(f"  max drift    {drift}")

    print(f"\nPer-draw cost, best of {args.reps} (microseconds, both layers)\n")
    print(f"{'level':>6}  {'maskfilter':>11}  {'imagefilter':>12}  {'speedup':>8}")
    for level in LEVELS:
        layers = md3_elevation_to_shadow(level)
        mask_us = _time_draw(layers, force_image=False, reps=args.reps)
        image_us = _time_draw(layers, force_image=True, reps=args.reps)
        print(f"{level:>6}  {mask_us:>11.1f}  {image_us:>12.1f}  {image_us / mask_us:>7.2f}x")

    _render_sheet(args.out)
    print(f"\nWrote {args.out} -- top row maskfilter, bottom row imagefilter.")


if __name__ == "__main__":
    main()
