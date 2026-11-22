"""Surface and image helpers for the Skia backend."""

from __future__ import annotations

import logging
import sys
from typing import Any

from nuiitivet.common.logging_once import exception_once

from .skia_module import get_skia

_logger = logging.getLogger(__name__)


def make_raster_surface(width: int, height: int) -> Any:
    """Create a raster Skia surface.

    Raises RuntimeError when skia-python is not available.
    """

    skia = get_skia(raise_if_missing=True)
    assert skia is not None

    return skia.Surface(int(width), int(height))


def make_raster_image(pixels: Any, width: int, height: int) -> Any:
    """Create a Skia image from tightly packed RGBA 8-bit pixels.

    The image holds its own copy: the caller may write to ``pixels`` or drop
    them afterwards. Once the app has imported numpy the copy is made without
    the GIL, so a call on another thread does not stop the UI thread.

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
    image = _image_copied_by_numpy(skia, pixels, view, int(width), int(height))
    if image is not None:
        return image
    if view.c_contiguous:
        view = view.cast("B")
    else:
        view = memoryview(view.tobytes())
    return skia.Image.frombytes(
        view,
        (int(width), int(height)),
        skia.ColorType.kRGBA_8888_ColorType,
        skia.AlphaType.kUnpremul_AlphaType,
    )


def _image_copied_by_numpy(skia: Any, pixels: Any, view: memoryview, width: int, height: int) -> Any:
    """The image over a bitmap numpy filled; ``None`` where that route is closed.

    ``Image.frombytes`` copies with the GIL held: a 2560x1440 raster built on a
    worker thread stops the UI thread for the whole copy. numpy releases the
    GIL for a plain copy. numpy is used only when the app has imported it; the
    framework does not depend on it.

    The bitmap is made immutable before the image is taken from it, so the
    image shares the bitmap's pixels and keeps them alive. ``Image.MakeRasterData``
    over a ``Data`` does not: the pixels die with the ``Data`` object.
    """
    numpy = sys.modules.get("numpy")
    bitmap_class = getattr(skia, "Bitmap", None)
    from_bitmap = getattr(getattr(skia, "Image", None), "MakeFromBitmap", None)
    if numpy is None or bitmap_class is None or from_bitmap is None:
        return None
    try:
        bitmap = bitmap_class()
        info = skia.ImageInfo.Make(
            width, height, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kUnpremul_AlphaType
        )
        if not bitmap.tryAllocPixels(info):
            return None
        target = numpy.frombuffer(bitmap, dtype=numpy.uint8)
        if target.nbytes != view.nbytes:
            return None
        if view.c_contiguous:
            source = numpy.frombuffer(view, dtype=numpy.uint8)
        else:
            source = numpy.ascontiguousarray(pixels).reshape(-1).view(numpy.uint8)
        numpy.copyto(target, source)
        del target
        bitmap.setImmutable()
        return from_bitmap(bitmap)
    except Exception:
        exception_once(_logger, "make_raster_image_numpy_exc", "The copy by numpy failed; copying with the GIL held")
        return None


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
