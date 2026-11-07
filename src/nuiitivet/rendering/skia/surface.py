"""Surface and image helpers for the Skia backend."""

from __future__ import annotations

from typing import Any

from .skia_module import get_skia


def make_raster_surface(width: int, height: int) -> Any:
    """Create a raster Skia surface.

    Raises RuntimeError when skia-python is not available.
    """

    skia = get_skia(raise_if_missing=True)
    assert skia is not None

    return skia.Surface(int(width), int(height))


def make_raster_image(pixels: Any, width: int, height: int) -> Any:
    """Create a Skia image from tightly packed RGBA 8-bit pixels.

    Args:
        pixels: Any object exposing the buffer protocol: ``bytes``, a
            ``memoryview``, a numpy array. Straight (unpremultiplied) alpha,
            rows top to bottom, ``width * height * 4`` bytes.
        width: The image width in pixels.
        height: The image height in pixels.

    Raises:
        ValueError: The buffer does not hold exactly ``width * height * 4`` bytes.
        RuntimeError: skia-python is not available.
    """
    skia = get_skia(raise_if_missing=True)
    assert skia is not None

    view = memoryview(pixels)
    expected = int(width) * int(height) * 4
    if view.nbytes != expected:
        raise ValueError(f"expected {expected} bytes of RGBA pixels for {width}x{height}, got {view.nbytes}")
    if not view.c_contiguous or view.ndim != 1 or view.itemsize != 1:
        view = memoryview(view.tobytes())
    return skia.Image.frombytes(
        view,
        (int(width), int(height)),
        skia.ColorType.kRGBA_8888_ColorType,
        skia.AlphaType.kUnpremul_AlphaType,
    )


def save_png(image: Any, path: str) -> None:
    """Save a skia.Image to a PNG file path.

    Raises RuntimeError when skia-python (or PNG encoding) is not available.
    """

    skia = get_skia(raise_if_missing=True)
    assert skia is not None

    fmt = getattr(skia, "kPNG", None)
    if fmt is None:
        raise RuntimeError("skia.kPNG is required")

    image.save(path, fmt)


__all__ = [
    "make_raster_image",
    "make_raster_surface",
    "save_png",
]
