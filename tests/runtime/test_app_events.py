import types


from nuiitivet.runtime import app_events
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.backends.pyglet.gpu_frame import draw_gpu_frame
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.widgeting.widget import Widget


class FakeCanvas:
    def __init__(self):
        self.scaled = False
        self.cleared = False
        self.drawn_images = []

    def scale(self, sx, sy):
        self.scaled = (sx, sy)

    def clear(self, col):
        self.cleared = True

    def drawImage(self, image, x, y):
        self.drawn_images.append((image, x, y))


class FakeImage:
    def __init__(self, w, h):
        self._w = w
        self._h = h

    def width(self):
        return self._w

    def height(self):
        return self._h


class FakeSurface:
    def __init__(self, canvas, snapshot_size=(100, 80)):
        self._canvas = canvas
        self._snapshot_size = snapshot_size
        self.snapshot_count = 0

    def getCanvas(self):
        return self._canvas

    def makeImageSnapshot(self):
        self.snapshot_count += 1
        return FakeImage(*self._snapshot_size)


class FakeSkiaModule:
    def __init__(self, make_surface_returns=True):
        self.kBottomLeft_GrSurfaceOrigin = object()
        self.kRGBA_8888_ColorType = object()
        self.ColorWHITE = 0
        self._make_returns = make_surface_returns

    @staticmethod
    def Color(r, g, b, a):
        return (r, g, b, a)

    class GrGLFramebufferInfo:
        def __init__(self, a, b):
            pass

    class GrBackendRenderTarget:
        def __init__(self, *args, **kwargs):
            pass

    class Surface:
        @staticmethod
        def MakeFromBackendRenderTarget(gr_context, backend, origin, ct, v):
            # will be monkeypatched in tests
            raise RuntimeError("not patched")


class DummyGL:
    GL_FRAMEBUFFER_BINDING = 0
    GL_SAMPLES = 1
    GL_STENCIL_BITS = 2
    GL_RGBA8 = 999

    def __init__(self, fb=0, samples=0, stencil=0):
        self._vals = {self.GL_FRAMEBUFFER_BINDING: fb, self.GL_SAMPLES: samples, self.GL_STENCIL_BITS: stencil}

    def glGetIntegerv(self, name):
        return self._vals.get(name, 0)


class DummyGrContext:
    def flush(self):
        self.flushed = True

    def submit(self):
        self.submitted = True


class FakeRoot:
    def __init__(self):
        self.painted = False

    def paint(self, canvas, x, y, w, h):
        self.painted = True

    def hit_test(self, x, y):
        return None

    def unmount(self):
        self.unmounted = True


class DummyApp:
    def __init__(self):
        self.width = 100
        self.height = 80
        self._scale = 1.0
        self.root = FakeRoot()
        self._last_image = None
        self._dirty = True
        self._last_hover_target = None
        self._pressed_target = None
        self._pointer_capture_manager = PointerCaptureManager()

    def _render_to_png_bytes(self):
        # return a minimal PNG header (not a valid image for pyglet, but we'll monkeypatch pyglet)
        return b"PNGDATA"

    def invalidate(self):
        self._dirty = True

    def _background_clear_color(self):
        return 0


def test_draw_gpu_frame_success(monkeypatch):
    app = DummyApp()
    canvas = FakeCanvas()
    surf = FakeSurface(canvas)

    skia = FakeSkiaModule()

    # patch Surface.MakeFromBackendRenderTarget to return our FakeSurface
    def make_backend(*args, **kwargs):
        return surf

    skia.Surface.MakeFromBackendRenderTarget = staticmethod(make_backend)

    gr = DummyGrContext()
    gl = DummyGL(fb=1, samples=4, stencil=8)

    ok = draw_gpu_frame(app, gr, gl, skia)
    assert ok is True
    assert app.root.painted is True


def test_draw_gpu_frame_fallback(monkeypatch):
    app = DummyApp()
    skia = FakeSkiaModule()

    # Make Surface.MakeFromBackendRenderTarget return None to simulate failure
    skia.Surface.MakeFromBackendRenderTarget = staticmethod(lambda *a, **k: None)

    gr = DummyGrContext()
    gl = DummyGL()

    ok = draw_gpu_frame(app, gr, gl, skia)
    assert ok is False


def _make_gpu_env():
    app = DummyApp()
    canvas = FakeCanvas()
    surf = FakeSurface(canvas, snapshot_size=(app.width, app.height))
    skia = FakeSkiaModule()
    skia.Surface.MakeFromBackendRenderTarget = staticmethod(lambda *a, **k: surf)
    gr = DummyGrContext()
    gl = DummyGL(fb=1, samples=4, stencil=8)
    return app, canvas, surf, skia, gr, gl


def test_gpu_frame_caches_after_full_paint():
    app, canvas, surf, skia, gr, gl = _make_gpu_env()
    app._paint_dirty = True

    ok = draw_gpu_frame(app, gr, gl, skia)

    assert ok is True
    assert app.root.painted is True
    # A clean full frame is cached and paint-dirtiness is cleared.
    assert app._gpu_frame_cache is not None
    assert app._gpu_frame_cache_size == (app.width, app.height)
    assert app._paint_dirty is False
    assert surf.snapshot_count == 1


def test_gpu_frame_reblits_cached_frame_when_clean():
    app, canvas, surf, skia, gr, gl = _make_gpu_env()

    # First frame: full paint populates the cache.
    app._paint_dirty = True
    draw_gpu_frame(app, gr, gl, skia)
    app.root.painted = False

    # Second frame with clean content: must re-blit, not re-walk the tree.
    app._paint_dirty = False
    ok = draw_gpu_frame(app, gr, gl, skia)

    assert ok is True
    assert app.root.painted is False  # tree walk skipped
    assert len(canvas.drawn_images) == 1  # cached frame blitted 1:1
    assert canvas.drawn_images[0][1:] == (0.0, 0.0)


def test_gpu_frame_repaints_when_size_changes():
    app, canvas, surf, skia, gr, gl = _make_gpu_env()

    app._paint_dirty = True
    draw_gpu_frame(app, gr, gl, skia)
    app.root.painted = False

    # Clean content but the physical size no longer matches the cache -> repaint.
    app._paint_dirty = False
    app.width = 200
    ok = draw_gpu_frame(app, gr, gl, skia)

    assert ok is True
    assert app.root.painted is True
    assert not canvas.drawn_images  # no stale-size re-blit


def test_invalidate_content_flag_controls_paint_dirty():
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window

    class LeafWidget(Widget):
        def paint(self, canvas, x, y, w, h):
            pass

    app = App(Window(content=LeafWidget(), title="t")).main_window
    app._paint_dirty = False
    app.invalidate(content=False)
    assert app._paint_dirty is False  # surface-loss redraw leaves content clean
    assert app._dirty is True

    app.invalidate()  # default content=True
    assert app._paint_dirty is True


def test_draw_raster_frame_success(monkeypatch):
    app = DummyApp()

    fake_img = object()

    class FakePygletImage:
        @staticmethod
        def load(name, file=None):
            return fake_img

    fake_pyglet = types.SimpleNamespace(
        image=FakePygletImage,
        app=types.SimpleNamespace(exit=lambda: None),
    )

    from nuiitivet.backends.pyglet import runner as pyglet_runner

    # _draw_raster_frame resolves pyglet through the runner module's global, so
    # patch that binding directly. Patching sys.modules would only work if this
    # test happened to be the first to import the runner.
    monkeypatch.setattr(pyglet_runner, "pyglet", fake_pyglet)

    ok = pyglet_runner._draw_raster_frame(app, skia=None)
    assert ok is True
    assert app._last_image is fake_img
    assert app._dirty is False


def test_draw_raster_frame_failure(monkeypatch):
    app = DummyApp()

    def bad_render():
        raise RuntimeError("boom")

    app._render_to_png_bytes = bad_render

    from nuiitivet.backends.pyglet import runner as pyglet_runner

    ok = pyglet_runner._draw_raster_frame(app, skia=None)
    assert ok is False


def test_enter_leave_sequence_and_hover_tracking():
    # Setup app and two widgets which record events
    class LogWidget(Widget):
        def __init__(self, name):
            super().__init__()
            self.name = name
            self.events = []

        def on_pointer_event(self, event: PointerEvent) -> bool:
            self.events.append(event.type)
            return True

        def paint(self, canvas, x, y, w, h):
            pass

    class Root:
        def __init__(self, a, b):
            self.a = a
            self.b = b

        def hit_test(self, x, y):
            return self.a if x < 50 else self.b

        def unmount(self):
            pass

    app = DummyApp()
    a = LogWidget("a")
    b = LogWidget("b")
    app.root = Root(a, b)
    app._last_hover_target = None
    app._dirty = False

    # Move into A
    app_events.dispatch_mouse_motion(app, 10, 10)
    assert PointerEventType.ENTER in a.events
    assert PointerEventType.HOVER in a.events
    assert app._last_hover_target is a
    assert app._dirty is True

    # reset dirty for next step
    app._dirty = False

    # Move from A to B
    app_events.dispatch_mouse_motion(app, 60, 10)
    # A should have received leave, B enter+move
    assert PointerEventType.LEAVE in a.events
    assert PointerEventType.ENTER in b.events
    assert PointerEventType.HOVER in b.events
    assert app._last_hover_target is b
    assert app._dirty is True


def test_pressed_capture_behavior_and_release():
    # A widget that handles press/move/release
    class PressWidget(Widget):
        def __init__(self):
            super().__init__()
            self.events = []

        def on_pointer_event(self, event: PointerEvent) -> bool:
            self.events.append(event.type)
            return True

        def paint(self, canvas, x, y, w, h):
            pass

    class RootSingle:
        def __init__(self, widget):
            self.w = widget

        def hit_test(self, x, y):
            # always return the single widget for simplicity
            return self.w

        def unmount(self):
            pass

    app = DummyApp()
    w = PressWidget()
    app.root = RootSingle(w)
    app._dirty = False

    # Dispatch press: should set app._pressed_target
    app_events.dispatch_mouse_press(app, 5, 5)
    assert app._pressed_target is w
    assert PointerEventType.PRESS in w.events
    assert app._dirty is True

    # reset dirty and clear events
    app._dirty = False
    w.events.clear()

    # While pressed, motion at arbitrary coords should be delivered to pressed widget
    app_events.dispatch_mouse_motion(app, 200, 200)
    assert PointerEventType.MOVE in w.events
    # no hover switching should occur (root has single widget)
    assert app._last_hover_target is None or app._last_hover_target is w

    # Release should call mouse_release on the pressed widget and clear pressed_target
    app._dirty = False
    app_events.dispatch_mouse_release(app, 200, 200)
    assert PointerEventType.RELEASE in w.events
    assert app._pressed_target is None
    assert app._dirty is True


def test_mouse_press_bubbles_to_parent_widget():
    class ParentWidget(Widget):
        def __init__(self):
            super().__init__()
            self.events = []

        def on_pointer_event(self, event: PointerEvent) -> bool:
            self.events.append(event.type)
            return event.type is PointerEventType.PRESS

    class ChildWidget(Widget):
        def __init__(self):
            super().__init__()
            self.events = []

        def on_pointer_event(self, event: PointerEvent) -> bool:
            self.events.append(event.type)
            return False

    app = DummyApp()
    parent = ParentWidget()
    child = ChildWidget()
    parent.add_child(child)
    parent.set_layout_rect(0, 0, 100, 100)
    child.set_layout_rect(0, 0, 100, 100)
    app.root = parent
    app._dirty = False

    app_events.dispatch_mouse_press(app, 10, 10)

    assert child.events == [PointerEventType.PRESS]
    assert parent.events == [PointerEventType.PRESS]
    assert app._pressed_target is parent
    assert app._dirty is True


def test_mouse_scroll_bubbles_to_parent_widget():
    class ParentWidget(Widget):
        def __init__(self):
            super().__init__()
            self.scroll_events = []

        def on_pointer_event(self, event: PointerEvent) -> bool:
            if event.type is PointerEventType.SCROLL:
                self.scroll_events.append(event)
                return True
            return False

    class ChildWidget(Widget):
        def __init__(self):
            super().__init__()

        def on_pointer_event(self, event: PointerEvent) -> bool:
            return False

    app = DummyApp()
    parent = ParentWidget()
    child = ChildWidget()
    parent.add_child(child)
    parent.set_layout_rect(0, 0, 200, 200)
    child.set_layout_rect(0, 0, 200, 200)
    app.root = parent
    app._dirty = False

    app_events.dispatch_mouse_scroll(app, 50, 50, 0, -1)

    assert len(parent.scroll_events) == 1
    assert app._dirty is True


def test_file_drop_delivered_to_innermost_acceptor():
    """A drop lands on the widget under the point, not on its ancestors (#599)."""
    from pathlib import Path

    from nuiitivet.input.events import FileDropEvent

    class DropWidget(Widget):
        def __init__(self):
            super().__init__()
            self.drops = []

        # Override so hit_test treats the widget as interactive.
        def on_pointer_event(self, event: PointerEvent) -> bool:
            return False

        def on_file_drop_event(self, event: FileDropEvent) -> bool:
            self.drops.append(event)
            return True

    app = DummyApp()
    parent = DropWidget()
    child = DropWidget()
    parent.add_child(child)
    parent.set_layout_rect(0, 0, 100, 100)
    child.set_layout_rect(0, 0, 100, 100)
    app.root = parent
    app._dirty = False

    handler = app_events.dispatch_file_drop(app, 10, 10, ["/tmp/a.txt", "/tmp/b.txt"])

    assert handler is child
    assert parent.drops == []
    assert len(child.drops) == 1
    event = child.drops[0]
    assert event.paths == (Path("/tmp/a.txt"), Path("/tmp/b.txt"))
    assert (event.x, event.y) == (10.0, 10.0)
    assert app._dirty is True


def test_file_drop_bubbles_to_accepting_ancestor():
    from nuiitivet.input.events import FileDropEvent

    class AcceptingParent(Widget):
        def __init__(self):
            super().__init__()
            self.drops = []

        def on_file_drop_event(self, event: FileDropEvent) -> bool:
            self.drops.append(event)
            return True

    class InertChild(Widget):
        # Interactive for hit-testing but does not accept drops.
        def on_pointer_event(self, event: PointerEvent) -> bool:
            return False

    app = DummyApp()
    parent = AcceptingParent()
    child = InertChild()
    parent.add_child(child)
    parent.set_layout_rect(0, 0, 100, 100)
    child.set_layout_rect(0, 0, 100, 100)
    app.root = parent

    handler = app_events.dispatch_file_drop(app, 10, 10, ["/tmp/a.txt"])

    assert handler is parent
    assert len(parent.drops) == 1


def test_file_drop_without_acceptor_is_discarded():
    class InertWidget(Widget):
        def on_pointer_event(self, event: PointerEvent) -> bool:
            return False

    app = DummyApp()
    root = InertWidget()
    root.set_layout_rect(0, 0, 100, 100)
    app.root = root
    app._dirty = False

    handler = app_events.dispatch_file_drop(app, 10, 10, ["/tmp/a.txt"])

    assert handler is None
    assert app._dirty is False


def test_file_drop_outside_any_widget_returns_none():
    app = DummyApp()  # FakeRoot.hit_test returns None

    handler = app_events.dispatch_file_drop(app, 10, 10, ["/tmp/a.txt"])

    assert handler is None
