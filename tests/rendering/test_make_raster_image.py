"""make_raster_image accepts any RGBA buffer and makes the same image from it."""

from __future__ import annotations

from typing import Any

import pytest

from nuiitivet.rendering.skia import make_raster_image

np = pytest.importorskip("numpy")
skia = pytest.importorskip("skia")

W, H = 5, 3


def _pixels() -> Any:
    """An (H, W, 4) array whose every byte differs, so any reordering shows."""
    return np.arange(H * W * 4, dtype=np.uint8).reshape(H, W, 4)


def _read(image: object) -> bytes:
    info = skia.ImageInfo.Make(W, H, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kUnpremul_AlphaType)
    out = bytearray(W * H * 4)
    assert image.readPixels(info, out, W * 4)  # type: ignore[attr-defined]
    return bytes(out)


@pytest.mark.parametrize(
    "make",
    [
        pytest.param(lambda p: p, id="3-D array"),
        pytest.param(lambda p: p.reshape(-1), id="1-D array"),
        pytest.param(lambda p: p.tobytes(), id="bytes"),
        pytest.param(lambda p: memoryview(p), id="memoryview"),
    ],
)
def test_contiguous_buffers_make_the_image_in_their_byte_order(make: object) -> None:
    pixels = _pixels()
    image = make_raster_image(make(pixels), W, H)  # type: ignore[operator]
    assert _read(image) == pixels.tobytes()


def test_a_non_contiguous_array_makes_the_image_in_its_logical_order() -> None:
    flipped = _pixels()[:, ::-1]
    assert not flipped.flags.c_contiguous
    image = make_raster_image(flipped, W, H)
    assert _read(image) == flipped.tobytes()


def test_a_wider_dtype_is_read_as_its_bytes() -> None:
    pixels = _pixels()
    as_uint32 = pixels.view(np.uint32)
    image = make_raster_image(as_uint32, W, H)
    assert _read(image) == pixels.tobytes()


def test_a_buffer_of_the_wrong_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_raster_image(_pixels()[:, :-1], W, H)
