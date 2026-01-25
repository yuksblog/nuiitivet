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
    "make_raster_surface",
    "save_png",
]
