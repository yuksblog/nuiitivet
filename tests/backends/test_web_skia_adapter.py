"""Tests for the CanvasKit adapter of the browser backend.

The adapter keeps the canvas matrix in Python, because CanvasKit has no
``setMatrix``. These run against a stand-in for the page's host, which records
every call that would cross into JS.
"""

import importlib
import sys
from types import ModuleType
from typing import Any, Iterator

import pytest


class _Handle:
    """Stands in for any CanvasKit object: every method call answers another handle."""

    def __getattr__(self, name: str) -> Any:
        return lambda *args: _Handle()


class _Host(_Handle):
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.CK = _Handle()

    def __getattr__(self, name: str) -> Any:
        def call(*args: Any) -> _Handle:
            self.calls.append((name, *args[1:]))
            return _Handle()

        return call

    def named(self, name: str) -> list[tuple[Any, ...]]:
        return [call[1:] for call in self.calls if call[0] == name]


@pytest.fixture
def web(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, _Host]]:
    host = _Host()
    js = ModuleType("js")
    js.NV_HOST = host  # type: ignore[attr-defined]
    ffi = ModuleType("pyodide.ffi")
    ffi.to_js = lambda value: value  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "js", js)
    monkeypatch.setitem(sys.modules, "pyodide", ModuleType("pyodide"))
    monkeypatch.setitem(sys.modules, "pyodide.ffi", ffi)
    monkeypatch.delitem(sys.modules, "nuiitivet.backends.web.skia", raising=False)
    skia = importlib.import_module("nuiitivet.backends.web.skia")
    yield skia, host
    sys.modules.pop("nuiitivet.backends.web.skia", None)


def _canvas(skia: Any) -> Any:
    return skia.Surface(300, 200, _Handle()).getCanvas()


def test_reset_matrix_is_exact_at_a_fractional_scale(web: tuple[Any, _Host]) -> None:
    skia, host = web
    canvas = _canvas(skia)
    canvas.scale(1.5, 1.5)
    canvas.translate(10.1, 20.3)
    canvas.save()
    canvas.resetMatrix()

    matrix = canvas.getTotalMatrix()
    assert (matrix.sx, matrix.kx, matrix.tx, matrix.ky, matrix.sy, matrix.ty) == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)

    canvas.drawRect(skia.Rect.MakeWH(10, 10), skia.Paint())
    # The host canvas is at the identity after a save, so nothing is sent to undo the scale.
    assert host.named("m") == []


def test_matrix_crosses_once_per_run_of_draws(web: tuple[Any, _Host]) -> None:
    skia, host = web
    canvas = _canvas(skia)
    paint = skia.Paint()
    canvas.scale(2.0, 2.0)
    canvas.translate(3.0, 4.0)
    canvas.translate(1.0, 1.0)
    canvas.drawOval(skia.Rect.MakeWH(10, 10), paint)
    canvas.drawOval(skia.Rect.MakeWH(20, 20), paint)

    assert host.named("m") == [(2.0, 0.0, 8.0, 0.0, 2.0, 10.0)]


def test_restore_brings_back_the_matrix_and_resends_it(web: tuple[Any, _Host]) -> None:
    skia, host = web
    canvas = _canvas(skia)
    paint = skia.Paint()
    canvas.translate(5.0, 5.0)
    canvas.save()
    canvas.translate(100.0, 0.0)
    canvas.restore()
    canvas.drawOval(skia.Rect.MakeWH(10, 10), paint)

    assert canvas.getTotalMatrix().tx == 5.0
    assert host.named("m") == [(1.0, 0.0, 5.0, 0.0, 1.0, 5.0)]


def test_clip_is_applied_in_device_coordinates(web: tuple[Any, _Host]) -> None:
    skia, host = web
    canvas = _canvas(skia)
    canvas.scale(2.0, 2.0)
    canvas.translate(5.0, 5.0)
    canvas.clipRect(skia.Rect.MakeWH(10, 10), True)

    assert host.named("clipRect") == [(10.0, 10.0, 30.0, 30.0, True)]
    bounds = canvas.getLocalClipBounds()
    assert (bounds.fLeft, bounds.fTop, bounds.fRight, bounds.fBottom) == (0.0, 0.0, 10.0, 10.0)


def test_round_clip_scales_its_radii(web: tuple[Any, _Host]) -> None:
    skia, host = web
    canvas = _canvas(skia)
    canvas.scale(2.0, 2.0)
    canvas.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(10, 10), 3.0, 3.0), True)

    assert host.named("clipRRect") == [(0.0, 0.0, 20.0, 20.0, True, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 6.0)]


def test_clip_under_a_rotation_is_sent_with_the_matrix(web: tuple[Any, _Host]) -> None:
    skia, host = web
    canvas = _canvas(skia)
    canvas.rotate(90.0)
    canvas.clipRect(skia.Rect.MakeWH(10, 20))

    assert host.named("clipRect") == []
    assert len(host.named("clipTransformed")) == 1
    # A quarter turn maps the 10 by 20 rect onto x in [-20, 0], which the surface cuts to nothing.
    assert canvas.getLocalClipBounds().isEmpty()


def test_save_counts_follow_skia(web: tuple[Any, _Host]) -> None:
    skia, host = web
    canvas = _canvas(skia)
    assert canvas.getSaveCount() == 1
    count = canvas.save()
    canvas.save()
    canvas.saveLayer(None, None)
    assert count == 1
    assert canvas.getSaveCount() == 4

    canvas.restoreToCount(count)
    assert canvas.getSaveCount() == 1
    assert len(host.named("restore")) == 3


def test_rrect_takes_both_radii_shapes(web: tuple[Any, _Host]) -> None:
    skia, _host = web
    rect = skia.Rect.MakeWH(10, 10)
    flat = skia.RRect.MakeRectRadii(rect, [1, 1, 2, 2, 3, 3, 4, 4])
    pairs = skia.RRect()
    pairs.setRectRadii(rect, [(1, 1), (2, 2), (3, 3), (4, 4)])

    assert flat.radii == pairs.radii == (1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0)
