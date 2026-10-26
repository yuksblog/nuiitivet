"""Tests for the window scale the pyglet runner keeps on a HiDPI display.

The runner is driven with a fake pyglet window and a fake GL so the frame
loop runs without a display. The fake ``draw_gpu_frame`` sets the GL viewport
to the render target it would draw into, as Skia does.
"""

from __future__ import annotations

import ctypes
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Callable

import pytest

import pyglet

from nuiitivet.backends.pyglet import runner
from nuiitivet.runtime.window import Window
from nuiitivet.widgeting.widget import Widget


class _Leaf(Widget):
    def build(self) -> Widget:
        return self


class _FakeGL:
    """A GL whose viewport starts at the framebuffer size, as pyglet leaves it after a resize."""

    GL_VIEWPORT = 0x0BA2

    def __init__(self, width: int, height: int) -> None:
        self.viewport = (0, 0, width, height)

    def glViewport(self, x: int, y: int, w: int, h: int) -> None:
        self.viewport = (x, y, w, h)

    def glGetIntegerv(self, name: int) -> Any:
        if name == self.GL_VIEWPORT:
            return list(self.viewport)
        return 0


class _FakePygletWindow:
    """A Windows pyglet window: sizes in physical pixels, pixel ratio 1.0."""

    WINDOW_STYLE_BORDERLESS = "borderless"
    WINDOW_STYLE_DIALOG = "dialog"
    WINDOW_STYLE_TOOL = "tool"
    WINDOW_STYLE_TRANSPARENT = "transparent"

    def __init__(self, width: int, height: int, **_: Any) -> None:
        self.width = width
        self.height = height
        self.handlers: dict[str, Callable[..., Any]] = {}
        self._hwnd = 1

    def event(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        self.handlers[fn.__name__] = fn
        return fn

    def get_pixel_ratio(self) -> float:
        return 1.0

    def get_framebuffer_size(self) -> tuple[int, int]:
        return self.width, self.height

    def get_location(self) -> tuple[int, int]:
        return 0, 0

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def set_caption(self, caption: str) -> None:
        pass


@pytest.fixture
def realized(monkeypatch: pytest.MonkeyPatch) -> tuple[Window, _FakePygletWindow, _FakeGL]:
    """A nuiitivet Window realized on a fake 150% Windows display, 800x600 physical."""
    gl = _FakeGL(800, 600)

    opengl_pkg = ModuleType("OpenGL")
    opengl_pkg.GL = gl  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "OpenGL", opengl_pkg)
    monkeypatch.setitem(sys.modules, "OpenGL.GL", gl)  # type: ignore[arg-type]

    fake_skia = SimpleNamespace(GrDirectContext=SimpleNamespace(MakeGL=lambda *a: object()))
    monkeypatch.setattr(runner, "get_skia", lambda raise_if_missing=False: fake_skia)

    monkeypatch.setattr(pyglet.window, "Window", _FakePygletWindow)
    monkeypatch.setattr(runner, "_install_ime_patch", lambda window, win: None)
    monkeypatch.setattr(runner, "_install_first_mouse_patch", lambda window, win: None)

    # Windows: the DPI API answers 144 dpi (150%).
    monkeypatch.setattr(sys, "platform", "win32")
    user32 = SimpleNamespace(GetDpiForWindow=lambda hwnd: 144)
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(user32=user32), raising=False)

    def fake_draw_gpu_frame(app: Any, gr_context: Any, GL: Any, skia: Any) -> bool:
        phys_w = max(1, int(app.width * app._scale))
        phys_h = max(1, int(app.height * app._scale))
        GL.glViewport(0, 0, phys_w, phys_h)
        app._dirty = False
        return True

    monkeypatch.setattr(runner, "draw_gpu_frame", fake_draw_gpu_frame)

    win = Window(content=_Leaf(), width=800, height=600)
    runner._realize_window(SimpleNamespace(), win, event_loop=None, renderer="gpu")
    os_window = win._window
    assert isinstance(os_window, _FakePygletWindow)
    # pyglet queues the creation-time events and replays them when the loop starts.
    os_window.handlers["on_resize"](800, 600)
    os_window.handlers["on_show"]()
    return win, os_window, gl


def test_scale_survives_a_render_target_one_pixel_wider_than_the_window(realized) -> None:
    # 150%, 800 px: ceil(800 / 1.5) = 534 logical, 534 * 1.5 = 801 px render target.
    win, os_window, gl = realized
    on_draw = os_window.handlers["on_draw"]

    for _ in range(3):
        on_draw()
        assert gl.viewport[2] == 801
        assert win._scale == pytest.approx(1.5)
        assert (win.width, win.height) == (534, 400)


def test_scale_follows_the_window_through_a_resize(realized) -> None:
    win, os_window, gl = realized
    on_draw = os_window.handlers["on_draw"]
    on_resize = os_window.handlers["on_resize"]

    on_draw()
    os_window.width, os_window.height = 803, 600
    on_resize(803, 600)
    for _ in range(3):
        on_draw()
        assert win._scale == pytest.approx(1.5)
        assert (win.width, win.height) == (536, 400)
