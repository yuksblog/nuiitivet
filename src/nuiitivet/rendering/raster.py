"""Decoded pixels with their size, the value ``Image`` shows."""

from __future__ import annotations

import operator
from typing import Any

from nuiitivet.rendering.skia import make_raster_image


class Raster:
    """Decoded pixels with their size, shown by :class:`~nuiitivet.widgets.Image`.

    A Raster never changes, and it may be built on any thread. Two Rasters are
    equal only when they are the same object, so writing a new one to a
    ``State`` always notifies.

    From RGBA pixels: :meth:`rgba`.
    """

    __slots__ = ("_image", "_width", "_height")

    _image: Any
    _width: int
    _height: int

    def __init__(self) -> None:
        """Refuse direct construction; build a Raster with :meth:`rgba`.

        Raises:
            TypeError: Always.
        """
        raise TypeError("build a Raster with Raster.rgba")

    @classmethod
    def rgba(cls, pixels: Any, width: int, height: int) -> "Raster":
        """Build a Raster from RGBA pixels.

        The Raster holds its own copy: the caller may write to ``pixels`` or
        drop them afterwards. Once the app has imported numpy the copy runs
        without the GIL, so a call on another thread does not stop the UI
        thread.

        Args:
            pixels: Any object exposing the buffer protocol: ``bytes``, a numpy
                array, a Pillow image's ``tobytes()``. Tightly packed RGBA
                8-bit, straight alpha, rows top to bottom,
                ``width * height * 4`` bytes.
            width: The width in pixels.
            height: The height in pixels.

        Raises:
            TypeError: ``width`` or ``height`` is not an integer.
            ValueError: ``width`` or ``height`` is not positive, or the buffer
                does not hold exactly ``width * height * 4`` bytes.
            RuntimeError: skia-python is not available.
        """
        width, height = operator.index(width), operator.index(height)
        if width <= 0 or height <= 0:
            raise ValueError(f"a Raster needs a positive size, got {width}x{height}")
        raster = object.__new__(cls)
        raster._image = make_raster_image(pixels, width, height)
        raster._width = width
        raster._height = height
        return raster

    @property
    def width(self) -> int:
        """The width in pixels."""
        return self._width

    @property
    def height(self) -> int:
        """The height in pixels."""
        return self._height

    def __repr__(self) -> str:
        return f"Raster({self._width}x{self._height})"


def raster_image(raster: Raster) -> Any:
    """The Skia image a Raster holds."""
    return raster._image


__all__ = ["Raster"]
