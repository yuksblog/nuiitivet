"""The RasterSurface asks for pixels at its device size, between frames, and paints them."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import nuiitivet.widgets.raster_surface as raster_mod
from nuiitivet.observable import State
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks
from nuiitivet.widgets.raster_surface import RasterSurface


class _FakeImage:
    def __init__(self, width: int, height: int) -> None:
        self.size = (width, height)


@pytest.fixture
def fake_skia(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int]]:
    """Builds no real image: records the size each raster was made at."""
    made: list[tuple[int, int]] = []

    def make_raster_image(pixels: object, width: int, height: int) -> _FakeImage:
        if memoryview(pixels).nbytes != width * height * 4:  # type: ignore[arg-type]
            raise ValueError("wrong size")
        made.append((width, height))
        return _FakeImage(width, height)

    monkeypatch.setattr(raster_mod, "make_raster_image", make_raster_image)
    monkeypatch.setattr(raster_mod, "make_rect", lambda x, y, w, h: (x, y, w, h))
    monkeypatch.setattr(raster_mod, "_linear_sampling", lambda: ())
    return made


def _on_display(monkeypatch: pytest.MonkeyPatch, ratio: float) -> None:
    monkeypatch.setattr(raster_mod, "find_window", lambda _widget: SimpleNamespace(pixel_ratio=ratio))


def _pixels(width: int, height: int) -> bytes:
    return bytes(width * height * 4)


def test_draw_is_asked_for_the_content_rect_in_device_pixels(
    fake_skia: list[tuple[int, int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _on_display(monkeypatch, 2.0)
    asked: list[tuple[int, int]] = []

    def draw(w: int, h: int) -> bytes:
        asked.append((w, h))
        return _pixels(w, h)

    surface = RasterSurface(draw, width=220, height=120, padding=10)
    surface.layout(220, 120)

    # Layout only queues; the pixels are made between frames.
    assert asked == []
    flush_size_change_callbacks()
    assert asked == [(400, 200)]
    assert fake_skia == [(400, 200)]
    assert surface.pixel_ratio == 2.0


def test_a_layout_at_the_same_size_asks_nothing(
    fake_skia: list[tuple[int, int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _on_display(monkeypatch, 1.0)
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = RasterSurface(draw, width=100, height=50)

    surface.layout(100, 50)
    flush_size_change_callbacks()
    surface.layout(100, 50)
    flush_size_change_callbacks()

    assert draw.call_count == 1


def test_a_resize_asks_again_and_the_old_raster_is_stretched_meanwhile(
    fake_skia: list[tuple[int, int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _on_display(monkeypatch, 1.0)
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = RasterSurface(draw, width="wt", height="wt")
    surface.layout(100, 50)
    flush_size_change_callbacks()

    surface.layout(300, 150)
    canvas = MagicMock()
    surface.paint(canvas, 0, 0, 300, 150)

    # The frame of the resize paints the 100x50 raster over the new rect.
    image, src, dst = canvas.drawImageRect.call_args[0]
    assert image.size == (100, 50)
    assert src == (0, 0, 100, 50)
    assert dst == (0, 0, 300, 150)
    flush_size_change_callbacks()
    assert draw.call_args_list[-1].args == (300, 150)


def test_without_a_window_the_ratio_is_one(fake_skia: list[tuple[int, int]]) -> None:
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = RasterSurface(draw, width=80, height=40)

    surface.layout(80, 40)
    flush_size_change_callbacks()

    assert draw.call_args.args == (80, 40)
    assert surface.pixel_ratio == 1.0


def test_a_request_before_layout_waits_for_the_size(fake_skia: list[tuple[int, int]]) -> None:
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = RasterSurface(draw, width=80, height=40)

    surface.request_render()
    flush_size_change_callbacks()
    assert draw.call_count == 0

    surface.layout(80, 40)
    flush_size_change_callbacks()
    assert draw.call_count == 1


def test_requests_in_one_frame_make_one_raster(fake_skia: list[tuple[int, int]]) -> None:
    draw = MagicMock(side_effect=lambda w, h: _pixels(w, h))
    surface = RasterSurface(draw, width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    surface.request_render()
    surface.request_render()
    surface.request_render()
    flush_size_change_callbacks()

    assert draw.call_count == 2


def test_draw_from_data_passes_the_value_and_follows_changes(fake_skia: list[tuple[int, int]]) -> None:
    data: State[int] = State(1)
    seen: list[tuple[int, int, int]] = []

    def draw(value: int, w: int, h: int) -> bytes:
        seen.append((value, w, h))
        return _pixels(w, h)

    surface = RasterSurface.draw(data, draw, width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()
    data.value = 2
    flush_size_change_callbacks()

    assert seen == [(1, 80, 40), (2, 80, 40)]


def test_a_buffer_of_the_wrong_size_leaves_the_surface_as_it_was(fake_skia: list[tuple[int, int]]) -> None:
    surface = RasterSurface(lambda w, h: bytes(7), width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    canvas = MagicMock()
    surface.paint(canvas, 0, 0, 80, 40)
    canvas.drawImageRect.assert_not_called()


def test_none_empties_the_surface(fake_skia: list[tuple[int, int]]) -> None:
    pixels: list[bytes | None] = [_pixels(80, 40)]
    surface = RasterSurface(lambda w, h: pixels[0], width=80, height=40)
    surface.layout(80, 40)
    flush_size_change_callbacks()

    pixels[0] = None
    surface.request_render()
    flush_size_change_callbacks()

    canvas = MagicMock()
    surface.paint(canvas, 0, 0, 80, 40)
    canvas.drawImageRect.assert_not_called()


def test_the_raster_is_painted_into_the_content_rect(
    fake_skia: list[tuple[int, int]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _on_display(monkeypatch, 2.0)
    surface = RasterSurface(lambda w, h: _pixels(w, h), width=100, height=60, padding=(10, 5))
    surface.layout(100, 60)
    flush_size_change_callbacks()

    canvas = MagicMock()
    surface.paint(canvas, 20, 30, 100, 60)

    _image, src, dst = canvas.drawImageRect.call_args[0]
    assert src == (0, 0, 160, 100)
    assert dst == (30, 35, 80, 50)
