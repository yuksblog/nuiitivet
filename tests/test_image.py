from __future__ import annotations

from unittest.mock import MagicMock

from nuiitivet.observable import Observable
from nuiitivet.widgets.image import Image


class _DummyDecodedImage:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class _DummySkiaImage:
    @staticmethod
    def MakeFromEncoded(data: bytes):
        if data == b"ok":
            return _DummyDecodedImage(200, 100)
        return None


class _DummySkia:
    Image = _DummySkiaImage


class _CountingSkiaImage:
    calls = 0

    @classmethod
    def reset(cls) -> None:
        cls.calls = 0

    @classmethod
    def MakeFromEncoded(cls, data: bytes):
        cls.calls += 1
        if data == b"ok":
            return _DummyDecodedImage(200, 100)
        return None


class _CountingSkia:
    Image = _CountingSkiaImage


def test_image_accepts_none_source() -> None:
    w = Image(None, width=120, height=80)
    assert w.fit == "contain"
    assert w.preferred_size() == (120, 80)


def test_image_observable_none_to_bytes_updates_and_draws(monkeypatch) -> None:
    import nuiitivet.widgets.image as image_mod

    monkeypatch.setattr(image_mod, "get_skia", lambda raise_if_missing=False: _DummySkia)

    source = Observable(None)
    w = Image(source, width=100, height=100)
    canvas = MagicMock()

    w.paint(canvas, 0, 0, 100, 100)
    canvas.drawImageRect.assert_not_called()

    source.value = b"ok"
    w.paint(canvas, 0, 0, 100, 100)
    assert canvas.drawImageRect.call_count >= 1


def test_image_fit_contain_draws_centered(monkeypatch) -> None:
    import nuiitivet.widgets.image as image_mod

    monkeypatch.setattr(image_mod, "get_skia", lambda raise_if_missing=False: _DummySkia)
    monkeypatch.setattr(image_mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    w = Image(b"ok", fit="contain", width=100, height=100)
    canvas = MagicMock()
    w.paint(canvas, 0, 0, 100, 100)

    assert canvas.drawImageRect.call_count == 1
    _image, src_rect, dst_rect = canvas.drawImageRect.call_args[0]
    assert src_rect == (0.0, 0.0, 200.0, 100.0)
    assert dst_rect == (0.0, 25.0, 100.0, 50.0)


def test_image_fit_cover_uses_crop(monkeypatch) -> None:
    import nuiitivet.widgets.image as image_mod

    monkeypatch.setattr(image_mod, "get_skia", lambda raise_if_missing=False: _DummySkia)
    monkeypatch.setattr(image_mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    w = Image(b"ok", fit="cover", width=100, height=100)
    canvas = MagicMock()
    w.paint(canvas, 0, 0, 100, 100)

    assert canvas.drawImageRect.call_count == 1
    _image, src_rect, dst_rect = canvas.drawImageRect.call_args[0]
    assert src_rect == (50.0, 0.0, 100.0, 100.0)
    assert dst_rect == (0.0, 0.0, 100.0, 100.0)


def test_image_fit_fill_stretches(monkeypatch) -> None:
    import nuiitivet.widgets.image as image_mod

    monkeypatch.setattr(image_mod, "get_skia", lambda raise_if_missing=False: _DummySkia)
    monkeypatch.setattr(image_mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    w = Image(b"ok", fit="fill", width=120, height=80)
    canvas = MagicMock()
    w.paint(canvas, 0, 0, 120, 80)

    _image, src_rect, dst_rect = canvas.drawImageRect.call_args[0]
    assert src_rect == (0.0, 0.0, 200.0, 100.0)
    assert dst_rect == (0.0, 0.0, 120.0, 80.0)


def test_image_fit_none_uses_intrinsic_size(monkeypatch) -> None:
    import nuiitivet.widgets.image as image_mod

    monkeypatch.setattr(image_mod, "get_skia", lambda raise_if_missing=False: _DummySkia)
    monkeypatch.setattr(image_mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    w = Image(b"ok", fit="none", width=100, height=100)
    canvas = MagicMock()
    w.paint(canvas, 0, 0, 100, 100)

    _image, src_rect, dst_rect = canvas.drawImageRect.call_args[0]
    assert src_rect == (0.0, 0.0, 200.0, 100.0)
    assert dst_rect == (0.0, 0.0, 200.0, 100.0)


def test_image_invalid_source_type_ignored() -> None:
    w = Image(None)
    w._on_source_change("bad")  # type: ignore[arg-type]
    assert w._decode_image_if_needed() is None


def test_image_decode_failure_not_retried_on_same_source(monkeypatch) -> None:
    import nuiitivet.widgets.image as image_mod

    _CountingSkiaImage.reset()
    monkeypatch.setattr(image_mod, "get_skia", lambda raise_if_missing=False: _CountingSkia)

    w = Image(b"bad")
    assert _CountingSkiaImage.calls == 1

    canvas = MagicMock()
    w.paint(canvas, 0, 0, 100, 100)
    w.paint(canvas, 0, 0, 100, 100)

    # decode should not happen during paint for unchanged source
    assert _CountingSkiaImage.calls == 1


def test_image_paint_is_pure_consumer_for_decode(monkeypatch) -> None:
    import nuiitivet.widgets.image as image_mod

    _CountingSkiaImage.reset()
    monkeypatch.setattr(image_mod, "get_skia", lambda raise_if_missing=False: _CountingSkia)
    monkeypatch.setattr(image_mod, "make_rect", lambda x, y, w, h: (x, y, w, h))

    w = Image(b"ok", fit="contain", width=100, height=100)
    assert _CountingSkiaImage.calls == 1

    canvas = MagicMock()
    w.paint(canvas, 0, 0, 100, 100)
    w.paint(canvas, 0, 0, 100, 100)

    # decode runs on source change (init), not during paint.
    assert _CountingSkiaImage.calls == 1
