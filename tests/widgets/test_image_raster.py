"""Image showing a Raster, and the sampling it draws with, on a real Skia surface."""

from __future__ import annotations

import threading
from typing import Any

import pytest

from nuiitivet.observable.value import State
from nuiitivet.rendering.raster import Raster
from nuiitivet.widgets.image import Image

skia = pytest.importorskip("skia")
np = pytest.importorskip("numpy")


def _render(widget: Image, width: int, height: int) -> Any:
    surface = skia.Surface(width, height)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorBLACK)
    widget.paint(canvas, 0, 0, width, height)
    return surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)


def _gradient(width: int, height: int) -> Any:
    ys, xs = np.mgrid[0:height, 0:width]
    rgba = np.empty((height, width, 4), dtype=np.uint8)
    rgba[..., 0] = (xs * 255 // max(1, width - 1)).astype(np.uint8)
    rgba[..., 1] = (ys * 255 // max(1, height - 1)).astype(np.uint8)
    rgba[..., 2] = 90
    rgba[..., 3] = 255
    return rgba


def _png(rgba: Any) -> bytes:
    image = skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)
    return bytes(image.encodeToData(skia.EncodedImageFormat.kPNG, 100))


def _gray_raster(levels: list[list[int]]) -> Raster:
    gray = np.array(levels, dtype=np.uint8)
    rgba = np.stack([gray, gray, gray, np.full_like(gray, 255)], axis=-1)
    return Raster.rgba(rgba, gray.shape[1], gray.shape[0])


@pytest.mark.parametrize("fit", ["contain", "cover", "fill", "none"])
@pytest.mark.parametrize("alignment", ["start", "center", "end"])
def test_a_raster_draws_as_the_same_picture_in_bytes_does(fit: str, alignment: str) -> None:
    rgba = _gradient(30, 20)

    raster = Raster.rgba(rgba, 30, 20)
    from_bytes = _render(Image(_png(rgba), fit=fit, alignment=alignment), 50, 50)  # type: ignore[arg-type]
    from_raster = _render(Image(raster, fit=fit, alignment=alignment), 50, 50)  # type: ignore[arg-type]

    assert from_raster.any()
    # A decoded PNG is premultiplied and a Raster is not: filtering rounds them up to 2 apart.
    assert int(np.abs(from_bytes.astype(int) - from_raster.astype(int)).max()) <= 2


def test_a_raster_takes_its_size_as_the_preferred_size() -> None:
    assert Image(_gray_raster([[0, 0, 0]] * 2)).preferred_size() == (3, 2)


def test_a_raster_is_shown_without_a_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(_data: bytes) -> None:
        raise AssertionError("decoded")

    monkeypatch.setattr(skia.Image, "MakeFromEncoded", refuse)

    shown = _render(Image(_gray_raster([[200]])), 4, 4)

    assert int(shown[2, 2, 0]) == 200


def test_a_raster_built_on_a_thread_is_shown() -> None:
    built: list[Raster] = []
    thread = threading.Thread(target=lambda: built.append(_gray_raster([[120, 120]])))
    thread.start()
    thread.join()

    shown = _render(Image(built[0], fit="fill"), 4, 4)

    assert int(shown[1, 1, 0]) == 120


def test_an_enlarged_picture_is_smoothed_not_blocky() -> None:
    shown = _render(Image(_gray_raster([[0, 255]]), fit="fill"), 8, 1)

    row = [int(value) for value in shown[0, :, 0]]
    assert any(0 < value < 255 for value in row)
    assert row == sorted(row)


def test_a_shrunk_picture_shows_no_moire() -> None:
    checker = [[255 * ((x + y) % 2) for x in range(64)] for y in range(64)]

    shown = _render(Image(_gray_raster(checker), fit="fill"), 7, 7)

    gray = shown[..., 0].astype(int)
    assert abs(int(gray.mean()) - 127) < 10
    assert int(gray.max()) - int(gray.min()) < 40


def test_a_new_raster_of_the_same_size_keeps_the_layout() -> None:
    source: State[Raster | None] = State(_gray_raster([[0, 0]]))
    widget = Image(source)
    widget.clear_needs_layout()

    source.value = _gray_raster([[255, 255]])
    assert not widget.needs_layout

    source.value = _gray_raster([[255, 255, 255]])
    assert widget.needs_layout
