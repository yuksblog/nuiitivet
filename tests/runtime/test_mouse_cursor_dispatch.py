"""The window shows the cursor of the widget under the pointer.

Covers the resolution ``app_events`` runs after every pointer dispatch: the
hovered widget's own answer, else its nearest ancestor's, else the arrow; the
capture owner's during a drag; and that an unchanged shape is not re-sent.
"""

from __future__ import annotations

from nuiitivet.input.codes import BUTTON_LEFT
from nuiitivet.input.cursor import MouseCursor
from nuiitivet.modifiers.cursor import cursor
from nuiitivet.runtime import app_events
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.runtime.window import Window
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.clickable import Clickable
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.widgets.text import TextBase as Text


class _Root:
    """A root whose hit test answers by x: each entry is ``(x_max, widget)``."""

    def __init__(self, bands):
        self._bands = bands

    def hit_test(self, x, y):
        for x_max, widget in self._bands:
            if x < x_max:
                return widget
        return None

    def unmount(self):
        pass


class _FakeApp:
    _apply_mouse_cursor = Window._apply_mouse_cursor

    def __init__(self, root):
        self.root = root
        self._last_hover_target = None
        self._pressed_target = None
        self._focused_node = None
        self._pointer_capture_manager = PointerCaptureManager()
        self._mouse_cursor = MouseCursor.DEFAULT
        self.shown: list[MouseCursor] = []
        self._mouse_cursor_sink = self.shown.append

    def invalidate(self, immediate: bool = False) -> None:
        del immediate

    def request_focus(self, node, source=None):
        self._focused_node = node


def _sized(widget):
    widget.set_layout_rect(0, 0, 100, 50)
    return widget


def test_a_clickable_shows_the_pointer_and_empty_space_the_arrow():
    button = _sized(Clickable(on_click=lambda: None))
    app = _FakeApp(_Root([(100, button)]))

    app_events.dispatch_mouse_motion(app, 10, 10)
    assert app.shown == [MouseCursor.POINTER]

    app_events.dispatch_mouse_motion(app, 200, 10)
    assert app.shown == [MouseCursor.POINTER, MouseCursor.DEFAULT]


def test_the_same_shape_reaches_the_backend_once():
    button = _sized(Clickable(on_click=lambda: None))
    app = _FakeApp(_Root([(100, button)]))

    app_events.dispatch_mouse_motion(app, 10, 10)
    app_events.dispatch_mouse_motion(app, 20, 10)
    app_events.dispatch_mouse_press(app, 20, 10, button=BUTTON_LEFT)
    app_events.dispatch_mouse_release(app, 20, 10, button=BUTTON_LEFT)
    assert app.shown == [MouseCursor.POINTER]


def test_moving_between_adjacent_widgets_switches_the_shape():
    button = _sized(Clickable(on_click=lambda: None))
    field = _sized(EditableText())
    app = _FakeApp(_Root([(100, button), (200, field)]))

    app_events.dispatch_mouse_motion(app, 50, 10)
    app_events.dispatch_mouse_motion(app, 150, 10)
    assert app.shown == [MouseCursor.POINTER, MouseCursor.TEXT]


def test_a_disabled_clickable_shows_the_arrow():
    button = _sized(Clickable(on_click=lambda: None, disabled=True))
    app = _FakeApp(_Root([(100, button)]))
    app._mouse_cursor = MouseCursor.POINTER

    app_events.dispatch_mouse_motion(app, 10, 10)
    assert app.shown == [MouseCursor.DEFAULT]


def test_a_widget_without_an_answer_takes_its_ancestors():
    label = Text("Open")
    button = _sized(Clickable(child=label, on_click=lambda: None))
    app = _FakeApp(_Root([(100, label)]))

    app_events.dispatch_mouse_motion(app, 10, 10)
    assert label.parent is button
    assert app.shown == [MouseCursor.POINTER]


def test_the_innermost_answer_wins():
    inner = Clickable(on_click=lambda: None)
    outer = _sized(Box(child=inner).modifier(cursor(MouseCursor.DEFAULT)))
    outer.mouse_cursor = MouseCursor.CROSSHAIR
    app = _FakeApp(_Root([(50, inner), (100, outer)]))

    app_events.dispatch_mouse_motion(app, 10, 10)
    app_events.dispatch_mouse_motion(app, 75, 10)
    assert app.shown == [MouseCursor.POINTER, MouseCursor.CROSSHAIR]


def test_a_drag_keeps_the_capture_owners_shape():
    handle = _sized(Clickable(on_press=lambda e: None, on_release=lambda e: None))
    handle.mouse_cursor = MouseCursor.RESIZE_LEFT_RIGHT
    app = _FakeApp(_Root([(100, handle)]))

    app_events.dispatch_mouse_motion(app, 10, 10)
    app_events.dispatch_mouse_press(app, 10, 10, button=BUTTON_LEFT)
    assert app._pointer_capture_manager.owner_of(1) is handle
    # Dragged far outside the handle: the pointer is captured, so the shape stays.
    app_events.dispatch_mouse_motion(app, 500, 500, buttons=BUTTON_LEFT)
    assert app.shown == [MouseCursor.RESIZE_LEFT_RIGHT]

    app_events.dispatch_mouse_release(app, 500, 500, button=BUTTON_LEFT)
    assert app.shown == [MouseCursor.RESIZE_LEFT_RIGHT, MouseCursor.DEFAULT]


def test_resolution_stops_at_a_cycle():
    class _Loop:
        mouse_cursor = None

        def __init__(self):
            self._parent = self

    assert app_events.resolve_mouse_cursor(_Loop()) is MouseCursor.DEFAULT


def test_a_sink_that_raises_does_not_break_dispatch():
    button = _sized(Clickable(on_click=lambda: None))
    app = _FakeApp(_Root([(100, button)]))

    def _broken(cursor):
        raise RuntimeError("no window")

    app._mouse_cursor_sink = _broken
    app_events.dispatch_mouse_motion(app, 10, 10)
    assert app._mouse_cursor is MouseCursor.POINTER


def test_a_window_without_an_os_window_remembers_the_shape():
    button = _sized(Clickable(on_click=lambda: None))
    app = _FakeApp(_Root([(100, button)]))
    app._mouse_cursor_sink = None

    app_events.dispatch_mouse_motion(app, 10, 10)
    assert app._mouse_cursor is MouseCursor.POINTER


class _SyncingWindow:
    """A window that records each re-resolution a host asks for."""

    def __init__(self):
        self.synced = 0

    def _sync_mouse_cursor(self):
        self.synced += 1


def test_a_write_on_a_mounted_host_reaches_its_window():
    from nuiitivet.runtime.window import WindowScope

    window = _SyncingWindow()
    button = Clickable(on_click=lambda: None)
    scope = WindowScope(window, button)  # the child links back weakly; keep the scope alive
    assert scope.window is window

    button.mouse_cursor = MouseCursor.NOT_ALLOWED
    button.mouse_cursor = MouseCursor.NOT_ALLOWED
    button.disabled = True
    assert window.synced == 2


def test_a_write_on_a_bare_host_is_kept_for_later():
    button = Clickable(on_click=lambda: None)
    button.mouse_cursor = MouseCursor.NOT_ALLOWED
    assert button.mouse_cursor is MouseCursor.NOT_ALLOWED
