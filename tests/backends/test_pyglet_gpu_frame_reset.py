"""Tests for the Skia GL state reset in the pyglet GPU frame path.

``GrDirectContext`` caches GL state and skips redundant GL calls, but the pyglet
side calls ``GL.glViewport()`` directly and pyglet's own ``on_resize`` rewrites
the viewport. Skia must be told, or it draws against stale bindings -- a stale,
garbled frame after a drag-resize.

``draw_gpu_frame`` takes ``GL`` and ``skia`` as arguments, so these run against
fakes with no GL context.
"""

from types import SimpleNamespace
from typing import Any

from nuiitivet.backends.pyglet.gpu_frame import draw_gpu_frame


class _FakeCanvas:
    def clear(self, color: Any) -> None:
        pass

    def scale(self, sx: float, sy: float) -> None:
        pass

    def drawImage(self, image: Any, x: float, y: float) -> None:
        pass


class _FakeSurface:
    def __init__(self) -> None:
        self.canvas = _FakeCanvas()

    def getCanvas(self) -> _FakeCanvas:
        return self.canvas

    def makeImageSnapshot(self) -> object:
        return object()


class _FakeGrContext:
    """A ``GrDirectContext`` stand-in that records the calls it receives."""

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def resetContext(self, state: int = 0xFFFFFFFF) -> None:
        self._calls.append("resetContext")

    def flush(self) -> None:
        self._calls.append("flush")


class _FakeGrContextWithoutReset:
    """An older ``GrDirectContext`` that predates ``resetContext``."""

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def flush(self) -> None:
        self._calls.append("flush")


class _FakeGrContextRaisingReset(_FakeGrContext):
    def resetContext(self, state: int = 0xFFFFFFFF) -> None:
        self._calls.append("resetContext")
        raise RuntimeError("reset failed")


def _make_gl() -> SimpleNamespace:
    values = {
        "GL_FRAMEBUFFER_BINDING": 0,
        "GL_SAMPLES": 0,
        "GL_STENCIL_BITS": 8,
    }

    def gl_get_integerv(name: str) -> int:
        return values[name]

    return SimpleNamespace(
        glGetIntegerv=gl_get_integerv,
        GL_FRAMEBUFFER_BINDING="GL_FRAMEBUFFER_BINDING",
        GL_SAMPLES="GL_SAMPLES",
        GL_STENCIL_BITS="GL_STENCIL_BITS",
        GL_RGBA8=0x8058,
    )


def _make_skia(calls: list[str]) -> SimpleNamespace:
    def make_from_backend_render_target(*args: Any, **kwargs: Any) -> _FakeSurface:
        calls.append("MakeFromBackendRenderTarget")
        return _FakeSurface()

    return SimpleNamespace(
        GrGLFramebufferInfo=lambda fbo, fmt: SimpleNamespace(fbo=fbo, fmt=fmt),
        GrBackendRenderTarget=lambda w, h, samples, stencil, info: SimpleNamespace(),
        Surface=SimpleNamespace(MakeFromBackendRenderTarget=make_from_backend_render_target),
        kBottomLeft_GrSurfaceOrigin=0,
        kRGBA_8888_ColorType=0,
        ColorWHITE=0xFFFFFFFF,
        Color=lambda r, g, b, a: 0,
    )


def _make_app() -> SimpleNamespace:
    # root=None keeps the tree walk out of it; _paint_dirty=True skips the
    # cached-frame fast path so this is the full paint route.
    return SimpleNamespace(
        width=400,
        height=300,
        _scale=1.0,
        root=None,
        _dirty=True,
        _paint_dirty=True,
        _gpu_frame_cache=None,
        _gpu_frame_cache_size=None,
    )


def test_draw_gpu_frame_resets_gr_context():
    calls: list[str] = []
    assert draw_gpu_frame(_make_app(), _FakeGrContext(calls), _make_gl(), _make_skia(calls)) is True
    assert "resetContext" in calls


def test_reset_happens_before_the_render_target_is_bound():
    # A reset after Skia has already drawn is useless: the stale viewport and
    # texture bindings have to be invalidated before this frame's draw calls.
    calls: list[str] = []
    draw_gpu_frame(_make_app(), _FakeGrContext(calls), _make_gl(), _make_skia(calls))
    assert calls.index("resetContext") < calls.index("MakeFromBackendRenderTarget")


def test_reset_happens_once_per_frame():
    calls: list[str] = []
    draw_gpu_frame(_make_app(), _FakeGrContext(calls), _make_gl(), _make_skia(calls))
    assert calls.count("resetContext") == 1


def test_frame_still_renders_without_reset_context():
    # A GrDirectContext lacking resetContext must degrade to the old behaviour,
    # not break the frame.
    calls: list[str] = []
    ok = draw_gpu_frame(_make_app(), _FakeGrContextWithoutReset(calls), _make_gl(), _make_skia(calls))
    assert ok is True
    assert "flush" in calls


def test_frame_still_renders_when_reset_context_raises():
    calls: list[str] = []
    ok = draw_gpu_frame(_make_app(), _FakeGrContextRaisingReset(calls), _make_gl(), _make_skia(calls))
    assert ok is True
    assert "flush" in calls


def test_cached_frame_reblit_also_resets():
    # The fast path returns early, but it still issues Skia draw calls into the
    # framebuffer, so it needs the same reset.
    calls: list[str] = []
    app = _make_app()
    app._paint_dirty = False
    cache = object()
    app._gpu_frame_cache = cache
    app._gpu_frame_cache_size = (400, 300)
    assert draw_gpu_frame(app, _FakeGrContext(calls), _make_gl(), _make_skia(calls)) is True
    # An untouched cache confirms the fast path ran; a full paint would have
    # replaced it with a fresh snapshot.
    assert app._gpu_frame_cache is cache
    assert "resetContext" in calls
