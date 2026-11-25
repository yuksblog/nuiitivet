from __future__ import annotations

import pytest

from nuiitivet.observable.value import State
from nuiitivet.rendering.raster import Raster, raster_image

skia = pytest.importorskip("skia")


def _gray(width: int, height: int, level: int) -> bytearray:
    return bytearray([level, level, level, 255] * (width * height))


def test_rgba_keeps_the_size() -> None:
    raster = Raster.rgba(_gray(3, 2, 10), 3, 2)

    assert (raster.width, raster.height) == (3, 2)
    assert repr(raster) == "Raster(3x2)"


def test_rgba_copies_the_pixels() -> None:
    pixels = _gray(2, 2, 10)
    raster = Raster.rgba(pixels, 2, 2)

    pixels[:] = _gray(2, 2, 200)

    shown = raster_image(raster).toarray(colorType=skia.kRGBA_8888_ColorType)
    assert int(shown[0, 0, 0]) == 10


@pytest.mark.parametrize("size", [(0, 2), (2, 0), (-1, 2)])
def test_rgba_refuses_a_size_that_is_not_positive(size: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        Raster.rgba(b"", *size)


def test_rgba_refuses_a_buffer_of_another_length() -> None:
    with pytest.raises(ValueError):
        Raster.rgba(_gray(2, 2, 10), 3, 2)


def test_direct_construction_is_refused() -> None:
    with pytest.raises(TypeError):
        Raster()


def test_a_state_notifies_for_a_new_raster_of_the_same_pixels() -> None:
    first = Raster.rgba(_gray(2, 2, 10), 2, 2)
    state: State[Raster] = State(first)
    seen: list[Raster] = []
    state.subscribe(seen.append)

    second = Raster.rgba(_gray(2, 2, 10), 2, 2)
    state.value = second

    assert first != second
    assert seen[-1] is second


def test_rgba_refuses_a_size_that_is_not_an_integer() -> None:
    with pytest.raises(TypeError):
        Raster.rgba(_gray(2, 2, 10), 2.0, 2)  # type: ignore[arg-type]
