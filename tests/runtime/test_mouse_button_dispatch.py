"""End-to-end dispatch of mouse button / modifiers through app_events.

Covers that ``button``/``modifier_keys`` reach the delivered ``PointerEvent``,
that a secondary (right/middle) press neither activates nor blurs focus, and
that a wheel event from a backend that reports no modifiers carries the keys
the window holds.
"""

from nuiitivet.layout.container import Container
from nuiitivet.modifiers.pointer_input import pointer_input
from nuiitivet.runtime import app_events
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.input.codes import BUTTON_LEFT, BUTTON_RIGHT, MOD_ALT, MOD_CTRL, MOD_SHIFT
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.widgeting.widget import Widget


class _RecordWidget(Widget):
    def __init__(self):
        super().__init__()
        self.events = []

    def on_pointer_event(self, event: PointerEvent) -> bool:
        self.events.append(event)
        return True

    def paint(self, canvas, x, y, w, h):
        pass


class _Root:
    def __init__(self, widget, *, hit=True):
        self._w = widget
        self._hit = hit

    def hit_test(self, x, y):
        return self._w if self._hit else None

    def unmount(self):
        pass


class _FakeApp:
    def __init__(self, root):
        self.root = root
        self._dirty = False
        self._last_hover_target = None
        self._pressed_target = None
        self._focused_node = None
        self._pointer_capture_manager = PointerCaptureManager()
        self.focus_requests = []

    def invalidate(self):
        self._dirty = True

    def request_focus(self, node):
        self.focus_requests.append(node)
        self._focused_node = node


def test_press_delivers_button_and_modifiers():
    w = _RecordWidget()
    app = _FakeApp(_Root(w))

    app_events.dispatch_mouse_press(app, 5, 5, button=BUTTON_RIGHT, modifier_keys=MOD_SHIFT)

    press = next(e for e in w.events if e.type is PointerEventType.PRESS)
    assert press.button == BUTTON_RIGHT
    assert press.modifier_keys == MOD_SHIFT


def test_release_delivers_button_and_modifiers():
    w = _RecordWidget()
    app = _FakeApp(_Root(w))

    app_events.dispatch_mouse_release(app, 5, 5, button=BUTTON_LEFT, modifier_keys=MOD_SHIFT)

    release = next(e for e in w.events if e.type is PointerEventType.RELEASE)
    assert release.button == BUTTON_LEFT
    assert release.modifier_keys == MOD_SHIFT


def test_right_press_on_empty_area_does_not_blur():
    w = _RecordWidget()
    app = _FakeApp(_Root(w, hit=False))
    sentinel = object()
    app._focused_node = sentinel

    app_events.dispatch_mouse_press(app, 5, 5, button=BUTTON_RIGHT)

    assert app.focus_requests == []
    assert app._focused_node is sentinel


def test_left_press_on_empty_area_blurs():
    w = _RecordWidget()
    app = _FakeApp(_Root(w, hit=False))
    app._focused_node = object()

    app_events.dispatch_mouse_press(app, 5, 5, button=BUTTON_LEFT)

    assert app.focus_requests == [None]


def test_motion_carries_held_buttons_during_capture():
    w = _RecordWidget()
    app = _FakeApp(_Root(w))
    # Capture the pointer so motion routes to the owner as a drag MOVE.
    app._pointer_capture_manager.capture(w, PointerEvent.mouse_event(1, PointerEventType.PRESS, 0, 0))

    app_events.dispatch_mouse_motion(app, 20, 20, buttons=BUTTON_LEFT, modifier_keys=MOD_SHIFT)

    move = next(e for e in w.events if e.type is PointerEventType.MOVE)
    assert move.buttons == BUTTON_LEFT
    assert move.modifier_keys == MOD_SHIFT


def test_scroll_delivers_modifiers():
    w = _RecordWidget()
    app = _FakeApp(_Root(w))

    app_events.dispatch_mouse_scroll(app, 5, 5, 0.0, 1.0, modifier_keys=MOD_CTRL)
    app_events.dispatch_mouse_scroll(app, 5, 5, 0.0, 1.0)

    assert [e.type for e in w.events] == [PointerEventType.SCROLL, PointerEventType.SCROLL]
    assert [e.modifier_keys for e in w.events] == [MOD_CTRL, 0]


def _wheel_surface(nuiitivet_app):
    """A window filled by a ``pointer_input`` surface, and the masks its ``on_scroll`` received."""
    seen: list[int] = []
    surface = Container(width=200, height=200).modifier(
        pointer_input(on_scroll=lambda e: seen.append(e.modifier_keys))
    )
    return nuiitivet_app(surface, size=(200, 200)).window, seen


def test_a_wheel_without_modifiers_carries_the_keys_the_window_holds(nuiitivet_app):
    """The pyglet path: the key events set the window's mask, the wheel event reports none."""
    window, seen = _wheel_surface(nuiitivet_app)

    for held in (MOD_CTRL, MOD_SHIFT, MOD_ALT, MOD_CTRL | MOD_SHIFT, 0):
        window._set_modifier_keys(held)
        window._dispatch_mouse_scroll(100, 100, 0.0, 1.0)

    assert seen == [MOD_CTRL, MOD_SHIFT, MOD_ALT, MOD_CTRL | MOD_SHIFT, 0]


def test_a_wheel_with_its_own_modifiers_ignores_the_keys_the_window_holds(nuiitivet_app):
    """The web and dev bridge paths: the wheel event reports its own modifiers."""
    window, seen = _wheel_surface(nuiitivet_app)

    window._dispatch_mouse_scroll(100, 100, 0.0, 1.0, modifier_keys=MOD_CTRL)
    window._set_modifier_keys(MOD_SHIFT)
    window._dispatch_mouse_scroll(100, 100, 0.0, 1.0, modifier_keys=0)

    assert seen == [MOD_CTRL, 0]
