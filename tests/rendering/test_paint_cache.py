import sys
import types

from nuiitivet.rendering.skia.paint_cache import CachedPaintMixin
from nuiitivet.widgeting.widget import Widget


class _CachedDummy(CachedPaintMixin, Widget):
    def __init__(self):
        super().__init__()
        self.render_count = 0

    def build(self) -> "Widget":  # pragma: no cover - trivial
        return self

    def preferred_size(self):  # pragma: no cover - not relevant
        return (0, 0)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        self.set_last_rect(x, y, width, height)
        with self.paint_cache(canvas, x, y, width, height) as target:
            if target is self.PAINT_CACHE_SKIP:
                return
            self.render_count += 1


class _FakeRecordingCanvas:
    def __init__(self):
        self.saved = 0
        self.restored = 0

    def clear(self, *_):
        return None

    def save(self):
        self.saved += 1

    def translate(self, *_):
        return None

    def restore(self):
        self.restored += 1


class _FakeSurface:
    def __init__(self, w: int, h: int):
        self._w = w
        self._h = h
        self._canvas = _FakeRecordingCanvas()

    def getCanvas(self):
        return self._canvas

    def makeImageSnapshot(self):
        return _FakeImage(self._w, self._h)


class _FakeImage:
    def __init__(self, w: int, h: int):
        self._w = w
        self._h = h

    def width(self):
        return self._w

    def height(self):
        return self._h


class _FakeDestCanvas:
    def __init__(self):
        self.draws = []

    def drawImage(self, image, x, y):
        self.draws.append((image.width(), image.height(), x, y))


class _FakeSkia(types.SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.Rect = types.SimpleNamespace(MakeXYWH=lambda *args: args)

    def Surface(self, w: int, h: int):
        return _FakeSurface(w, h)

    def Color4f(self, r: float, g: float, b: float, a: float):  # pragma: no cover - simple tuple
        return (r, g, b, a)


def _install_fake_skia():
    return _FakeSkia()


def test_cached_paint_mixin_reuses_snapshot(monkeypatch):
    fake_skia = _install_fake_skia()
    monkeypatch.setitem(sys.modules, "skia", fake_skia)

    widget = _CachedDummy()
    canvas = _FakeDestCanvas()

    widget.paint(canvas, 10, 12, 40, 20)
    assert widget.render_count == 1
    assert len(canvas.draws) == 1

    widget.paint(canvas, 10, 12, 40, 20)
    assert widget.render_count == 1  # cache hit
    assert len(canvas.draws) == 2  # cached image drawn again

    widget.invalidate_paint_cache()
    widget.paint(canvas, 10, 12, 40, 20)
    assert widget.render_count == 2
    assert len(canvas.draws) == 3


def test_cached_paint_mixin_size_change_forces_repaint(monkeypatch):
    fake_skia = _install_fake_skia()
    monkeypatch.setitem(sys.modules, "skia", fake_skia)

    widget = _CachedDummy()
    canvas = _FakeDestCanvas()

    widget.paint(canvas, 0, 0, 50, 30)
    widget.paint(canvas, 0, 0, 80, 30)  # different width -> cache miss

    assert widget.render_count == 2
    assert len(canvas.draws) == 2
