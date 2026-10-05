"""Run an App in a browser: one canvas, driven by the browser's event loop."""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

import js
from pyodide.ffi import create_proxy

from nuiitivet.backends.web import skia
from nuiitivet.backends.web.clock import BrowserClock
from nuiitivet.backends.web.input import button_code, buttons_mask, key_name, wheel_steps
from nuiitivet.common.logging_once import exception_once, warning_once
from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT, text_motion_for_key
from nuiitivet.observable.runtime import set_clock
from nuiitivet.platform.clipboard import BrowserClipboard, get_system_clipboard
from nuiitivet.rendering.skia.color import rgba_to_skia_color
from nuiitivet.runtime.threading import set_ui_thread

logger = logging.getLogger(__name__)


class _Loop:
    """The frame loop, and what App and Window see as the event loop.

    A frame runs only when one was asked for: by an invalidation, by a resize,
    or by the clock for a callback that is due.
    """

    def __init__(self) -> None:
        self._host = js.NV_HOST
        self._on_frame = create_proxy(self._frame)
        self._on_timer = create_proxy(self._tick)
        self._frame_pending = False
        self._draw_wanted = False
        self._window: Any = None
        self._surface: Optional[skia.Surface] = None
        self._size: Optional[tuple[int, int, float]] = None
        self.clock = BrowserClock(
            request_frame=self._request_frame,
            set_timeout=lambda ms: js.setTimeout(self._on_timer, ms),
            clear_timeout=js.clearTimeout,
        )
        self._escape_down = False
        self._host.onResize = create_proxy(self.request_draw)
        self._host.onPointer = create_proxy(self._pointer)
        self._host.onWheel = create_proxy(self._wheel)
        self._host.onKey = create_proxy(self._key)
        self._host.onText = create_proxy(self._text)
        self._host.onCompose = create_proxy(self._compose)
        self._host.onPaste = create_proxy(self._paste)
        self._input_place: Optional[tuple[float, float, float, bool]] = None
        clipboard = get_system_clipboard()
        if isinstance(clipboard, BrowserClipboard):
            clipboard.on_copy = self._host.writeClipboard

    def request_draw(self, immediate: bool = False) -> None:
        self._draw_wanted = True
        self._request_frame()

    def set_draw_fps(self, fps: Optional[float]) -> None:
        """Accepted for the desktop API. The browser paces frames to the display."""

    def attach(self, window: Any) -> None:
        self._window = window
        self.request_draw()

    def _request_frame(self) -> None:
        if not self._frame_pending:
            self._frame_pending = True
            js.requestAnimationFrame(self._on_frame)

    def _tick(self, *_args: Any) -> None:
        self.clock.tick()

    def _frame(self, _timestamp: float) -> None:
        self._frame_pending = False
        self.clock.tick()
        if not self._draw_wanted or self._window is None:
            return
        self._draw_wanted = False
        try:
            self._draw(self._window)
        except Exception:
            exception_once(logger, "web_frame_exc", "Drawing a frame raised")

    def _pointer(self, kind: str, x: float, y: float, button: int, buttons: int, modifier_keys: int) -> None:
        win = self._window
        if win is None:
            return
        try:
            if kind == "move":
                win._dispatch_mouse_motion(int(x), int(y), buttons=buttons_mask(buttons), modifier_keys=modifier_keys)
            elif kind == "down":
                win._dispatch_mouse_press(int(x), int(y), button=button_code(button), modifier_keys=modifier_keys)
            else:
                win._dispatch_mouse_release(int(x), int(y), button=button_code(button), modifier_keys=modifier_keys)
        except Exception:
            exception_once(logger, "web_pointer_exc", "Pointer dispatch raised")

    def _wheel(self, x: float, y: float, delta_x: float, delta_y: float, delta_mode: int) -> None:
        win = self._window
        if win is None:
            return
        try:
            steps_x, steps_y = wheel_steps(delta_x, delta_mode), wheel_steps(delta_y, delta_mode)
            win._dispatch_mouse_scroll(int(x), int(y), steps_x, steps_y)
        except Exception:
            exception_once(logger, "web_wheel_exc", "Wheel dispatch raised")

    def _key(self, down: bool, key: str, code: str, modifier_keys: int, repeat: bool) -> bool:
        """Dispatch a key. ``True`` keeps the browser from acting on it as well.

        A held key repeats only as a text motion, as on the desktop.
        """
        win = self._window
        if win is None:
            return False
        try:
            name = key_name(key, code)
            win._set_modifier_keys(modifier_keys)
            if name == "escape":
                # Back navigation fires on the release, and only after a press that could be handled.
                if down:
                    self._escape_down = bool(win.can_handle_back_event())
                    return self._escape_down
                if not self._escape_down:
                    return False
                self._escape_down = False
            handled = False
            if not repeat:
                dispatch = win._dispatch_key_press if down else win._dispatch_key_release
                handled = bool(dispatch(name, modifier_keys))
            motion = text_motion_for_key(name) if down else None
            if motion is not None and not modifier_keys & (MOD_CTRL | MOD_ALT | MOD_META):
                handled = bool(win._dispatch_text_motion(motion, select=bool(modifier_keys & MOD_SHIFT))) or handled
            if handled:
                win.invalidate()
            return handled
        except Exception:
            exception_once(logger, "web_key_exc", "Key dispatch raised")
            return False

    def _text(self, text: str) -> None:
        self._edit("web_text_exc", lambda win: win._dispatch_text(text))

    def _compose(self, text: str) -> None:
        # The browser does not report a selection inside the composition, so the caret sits at its end.
        self._edit("web_compose_exc", lambda win: win._dispatch_ime_composition(text, len(text), 0))

    def _paste(self, text: str) -> None:
        clipboard = get_system_clipboard()
        if isinstance(clipboard, BrowserClipboard):
            clipboard.receive(text)
        self._edit("web_paste_exc", lambda win: win._dispatch_key_press("v", MOD_CTRL))

    def _edit(self, key: str, dispatch: Any) -> None:
        win = self._window
        if win is None:
            return
        try:
            if dispatch(win):
                win.invalidate()
        except Exception:
            exception_once(logger, key, "Text input dispatch raised")

    def _place_input(self, win: Any) -> None:
        rect = win.ime.cursor_rect
        place = (rect.x, rect.y, rect.height, win.ime.has_cursor_source)
        if place != self._input_place:
            self._input_place = place
            self._host.placeInput(*place)

    def _draw(self, win: Any) -> None:
        handle = self._host.frame()
        size = (int(self._host.width), int(self._host.height), float(self._host.dpr))
        if size != self._size or self._surface is None:
            self._size = size
            self._surface = skia.Surface(int(self._host.pixelWidth), int(self._host.pixelHeight), handle)
            win.width, win.height, win._scale = size
        if not win._visible_obs.value:
            return
        win._flush_frame_queues()

        width, height, scale = size
        canvas = self._surface.getCanvas()
        canvas.save()
        canvas.scale(scale, scale)
        canvas.clear(rgba_to_skia_color(win._background_clear_color()))
        root = win.root
        if root is not None:
            if root.needs_layout or win._last_layout_size != (width, height):
                root.layout(width, height)
                win._last_layout_size = (width, height)
                root.clear_needs_layout()
            root.paint(canvas, 0, 0, width, height)
        canvas.restore()
        self._surface.flush()
        self._place_input(win)
        win._dirty = False
        win._paint_dirty = False


_loop: Optional[_Loop] = None
# The page returns from App.run() at once, so the module keeps the app alive.
_app: Any = None


def prepare() -> None:
    """Install the CanvasKit adapter as ``skia``, the UI thread and the browser clock.

    The page calls this before it runs the app module. A widget mounted while
    the App is constructed arms its timers at once, and the fallback clock
    would start a thread for them, which a browser refuses.
    """
    global _loop
    if _loop is None:
        _loop = _Loop()
        sys.modules["skia"] = skia
        set_ui_thread()
        set_clock(_loop.clock)


def run_app(app: Any, draw_fps: Optional[float] = None) -> None:
    """Start drawing ``app`` onto the page's canvas, and return.

    The main window fills the canvas and follows its size. The browser has no
    second window, so any other window stays unrealized.
    """
    global _app
    prepare()
    assert _loop is not None
    loop = _loop
    _app = app
    main = app.main_window

    def realize(win: Any) -> None:
        if win is not main:
            warning_once(logger, "web_extra_window", "A browser shows one window; a second one is not shown")
            return
        from nuiitivet.widgeting.widget import ComposableWidget

        if isinstance(win.root, ComposableWidget):
            built = win.root.evaluate_build()
            if built is not None:
                win.root = built
        title = getattr(win._title_value, "value", win._title_value)
        if title is not None:
            js.document.title = str(title)
        win._event_loop = loop
        loop.attach(win)

    app._event_loop = loop
    app._realize_window_hook = realize
    for win in list(app.windows):
        realize(win)


__all__ = ["prepare", "run_app"]
