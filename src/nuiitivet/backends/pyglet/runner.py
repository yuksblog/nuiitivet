"""Pyglet interactive runner.

This module owns the pyglet dependency so the core package remains backend-agnostic.
"""

from __future__ import annotations

import io
import logging
import os
import sys
import time
from typing import Any, Optional

import ctypes
import pyglet

from nuiitivet.platform import IMEManager
from nuiitivet.rendering.skia import get_skia

from nuiitivet.input.codes import (
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_DELETE,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_LEFT,
    TEXT_MOTION_RIGHT,
)

from .gpu_frame import draw_gpu_frame

from nuiitivet.observable.runtime import set_clock
from nuiitivet.common.logging_once import debug_once, exception_once


logger = logging.getLogger(__name__)


def run_app(app: Any, draw_fps: Optional[float] = None) -> None:
    """Run an interactive window for the given App-like object."""

    def _env_flag(name: str, default: bool = False) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        value = str(raw).strip().lower()
        if value in ("", "0", "false", "no", "off", "disable", "disabled"):
            return False
        if value in ("1", "true", "yes", "on", "enable", "enabled"):
            return True
        return True

    def _env_float(name: str, default: float) -> float:
        raw = os.environ.get(name)
        if raw is None:
            return float(default)
        try:
            return float(str(raw).strip())
        except Exception:
            return float(default)

    def _env_str(name: str, default: str = "") -> str:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return str(raw)

    debug_keys = _env_flag("NUIITIVET_DEBUG_KEYS", default=False)
    debug_keys_filter_raw = os.environ.get("NUIITIVET_DEBUG_KEYS_FILTER", "").strip().lower()
    debug_keys_filter = {k.strip() for k in debug_keys_filter_raw.split(",") if k.strip()}

    esc_down = False

    # Import here so unit tests can monkeypatch a minimal `pyglet` module
    # for raster-frame helpers without needing `pyglet.app.EventLoop`.
    from .event_loop import ResponsiveEventLoop

    if sys.platform == "win32":
        try:
            # Windows 8.1+ : PROCESS_PER_MONITOR_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                # Vista+ : PROCESS_DPI_UNAWARE (fallback if SetProcessDpiAwareness fails?)
                # Actually try SetProcessDPIAware for older Windows
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    try:
        set_clock(pyglet.clock)
    except Exception:
        exception_once(logger, "pyglet_set_clock_exc", "set_clock(pyglet.clock) failed")

    # Normalize root if available
    try:
        root = getattr(app, "root", None)
        if root is not None:
            from nuiitivet.widgeting.widget import ComposableWidget

            if isinstance(root, ComposableWidget):
                built = root.evaluate_build()
                if built is not None:
                    setattr(app, "root", built)
    except Exception:
        exception_once(logger, "pyglet_normalize_root_exc", "Failed to normalize app.root via evaluate_build")

    try:
        setattr(app, "_dirty", True)
        setattr(app, "_last_image", None)
    except Exception:
        exception_once(logger, "pyglet_init_app_state_exc", "Failed to initialize app state (_dirty/_last_image)")

    caption = None
    style = None
    try:
        title_bar = getattr(app, "title_bar", None)
        if title_bar:
            if hasattr(title_bar, "title") and title_bar.title:
                caption = str(title_bar.title)
            if type(title_bar).__name__ == "CustomTitleBar":
                style = pyglet.window.Window.WINDOW_STYLE_BORDERLESS
    except Exception:
        exception_once(logger, "pyglet_get_title_exc", "Failed to get window title")

    window = pyglet.window.Window(
        width=getattr(app, "width", 0),
        height=getattr(app, "height", 0),
        caption=caption,
        style=style,
        vsync=False,
    )

    # Check scale immediately and resize if needed
    try:
        scale = float(window.get_pixel_ratio())
        if scale > 1.0:
            log_w = getattr(app, "width", 800)
            log_h = getattr(app, "height", 600)
            phys_w = int(log_w * scale)
            phys_h = int(log_h * scale)

            if phys_w > window.width:
                window.set_size(phys_w, phys_h)

            setattr(app, "_scale", max(1.0, scale))
    except Exception:
        exception_once(logger, "pyglet_initial_resize_exc", "Failed to adjust initial window size for HiDPI")

    setattr(app, "_window", window)

    # Initial window positioning.
    try:
        pos = getattr(app, "window_position", None)
        if pos is not None:
            screens = None
            try:
                display = pyglet.canvas.get_display()
                screens = list(display.get_screens())
            except Exception:
                screens = None

            screen = None
            if screens:
                idx = int(getattr(pos, "screen_index", 0))
                if idx < 0:
                    idx = 0
                if idx >= len(screens):
                    idx = len(screens) - 1
                screen = screens[idx]
            else:
                screen = getattr(window, "screen", None)

            if screen is not None:
                key = str(getattr(pos, "alignment_key", "center")).strip().lower().replace("_", "-")
                dx, dy = getattr(pos, "offset", (0.0, 0.0))
                dx = float(dx)
                dy = float(dy)

                # Pyglet screen coordinates are bottom-left origin (+y is up).
                # Our UI offset uses +y down, so we invert dy when applying.
                sx = int(getattr(screen, "x", 0))
                sy = int(getattr(screen, "y", 0))
                sw = int(getattr(screen, "width", 0))
                sh = int(getattr(screen, "height", 0))
                ww = int(getattr(window, "width", 0))
                wh = int(getattr(window, "height", 0))

                if key == "center":
                    horiz = "center"
                    vert = "center"
                else:
                    parts = key.split("-")
                    vert = parts[0] if len(parts) >= 2 else "center"
                    horiz = parts[1] if len(parts) >= 2 else "center"

                if horiz == "left":
                    base_x = 0
                elif horiz == "right":
                    base_x = sw - ww
                else:
                    base_x = (sw - ww) // 2

                if vert == "bottom":
                    base_y = 0
                elif vert == "top":
                    base_y = sh - wh
                else:
                    base_y = (sh - wh) // 2

                x = sx + int(base_x + dx)
                y = sy + int(base_y - dy)
                window.set_location(int(x), int(y))
    except Exception:
        exception_once(logger, "pyglet_window_position_exc", "Failed to apply initial window position")

    if draw_fps is not None:
        try:
            app.set_draw_fps(draw_fps)
        except Exception:
            exception_once(logger, "pyglet_set_draw_fps_exc", "app.set_draw_fps raised")

    effective_draw_fps = getattr(app, "_preferred_draw_fps", None)

    # Mount root
    try:
        root = getattr(app, "root", None)
        if root is not None:
            root.mount(app)
    except Exception:
        exception_once(logger, "pyglet_root_mount_exc", "root.mount(app) raised")

    # Skia / GL setup
    gpu_enabled = False
    gr_context = None
    GL = None
    skia = get_skia(raise_if_missing=False)
    if skia is not None:
        try:
            from OpenGL import GL as _GL  # type: ignore

            GL = _GL
        except Exception:
            debug_once(logger, "pyglet_opengl_import_exc", "Failed to import OpenGL.GL")
            GL = None

        try:
            gr_context = skia.GrDirectContext.MakeGL()
        except Exception:
            debug_once(logger, "pyglet_grdirectcontext_makegl_exc", "GrDirectContext.MakeGL() failed")
            gr_context = None
        if gr_context is None:
            try:
                gr_context = skia.GrDirectContext.MakeGL(None)
            except Exception:
                debug_once(logger, "pyglet_grdirectcontext_makegl_none_exc", "GrDirectContext.MakeGL(None) failed")
                gr_context = None

        gpu_enabled = gr_context is not None and GL is not None

    # HiDPI scale
    try:
        scale = float(window.get_pixel_ratio())
    except Exception:
        debug_once(logger, "pyglet_window_pixel_ratio_exc", "window.get_pixel_ratio() failed")
        scale = 1.0
    try:
        setattr(app, "_scale", max(1.0, scale))
    except Exception:
        exception_once(logger, "pyglet_set_app_scale_exc", "Failed to set app._scale")

    _patch_pyglet_cocoa_view()
    _install_ime_patch(window)

    @window.event
    def on_draw():
        try:
            wx, wy = window.get_location()
            IMEManager.get().update_window_info(wx, wy, window.width, window.height)
        except Exception:
            exception_once(logger, "pyglet_on_draw_ime_update_exc", "IME window info update raised")

        nonlocal gpu_enabled
        if gpu_enabled and gr_context is not None and GL is not None:
            try:
                ok = bool(draw_gpu_frame(app, gr_context, GL, skia))
            except Exception:
                exception_once(logger, "pyglet_on_draw_gpu_frame_exc", "draw_gpu_frame raised")
                ok = False
            if ok:
                return
            gpu_enabled = False

        if getattr(app, "_dirty", False) or getattr(app, "_last_image", None) is None:
            if not _draw_raster_frame(app, skia):
                return

        try:
            window.clear()
        except Exception:
            exception_once(logger, "pyglet_on_draw_window_clear_exc", "window.clear raised")

        img = getattr(app, "_last_image", None)
        if img is not None:
            try:
                img.blit(0, 0)
            except Exception:
                exception_once(logger, "pyglet_on_draw_image_blit_exc", "image.blit raised")

    @window.event
    def on_expose():
        try:
            app.invalidate(immediate=True)
        except Exception:
            exception_once(logger, "pyglet_on_expose_invalidate_exc", "app.invalidate raised")

    @window.event
    def on_resize(width, height):
        try:
            # width/height from pyglet are physical pixels (if DPI aware)
            # app.width/app.height should be logical pixels.

            # Get latest scale
            current_scale = 1.0
            try:
                current_scale = float(window.get_pixel_ratio())
            except Exception:
                pass

            scale = max(1.0, current_scale)

            # Update app state
            app.width = int(width / scale)
            app.height = int(height / scale)
            setattr(app, "_scale", scale)

        except Exception:
            exception_once(logger, "pyglet_on_resize_set_size_exc", "Failed to set app.width/app.height")

        try:
            app.invalidate(immediate=True)
        except Exception:
            exception_once(logger, "pyglet_on_resize_invalidate_exc", "app.invalidate raised")

    @window.event
    def on_mouse_press(x, y, button, modifiers):
        scale = max(1.0, float(getattr(app, "_scale", 1.0)))
        x_log = int(x / scale)
        y_log = int(y / scale)
        y_conv = int(getattr(app, "height", 0)) - y_log
        try:
            app._dispatch_mouse_press(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_press_dispatch_exc", "Mouse press dispatch raised")

    @window.event
    def on_mouse_release(x, y, button, modifiers):
        scale = max(1.0, float(getattr(app, "_scale", 1.0)))
        x_log = int(x / scale)
        y_log = int(y / scale)
        y_conv = int(getattr(app, "height", 0)) - y_log
        try:
            app._dispatch_mouse_release(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_release_dispatch_exc", "Mouse release dispatch raised")

    @window.event
    def on_mouse_motion(x, y, dx, dy):
        scale = max(1.0, float(getattr(app, "_scale", 1.0)))
        x_log = int(x / scale)
        y_log = int(y / scale)
        y_conv = int(getattr(app, "height", 0)) - y_log
        try:
            app._dispatch_mouse_motion(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_motion_dispatch_exc", "Mouse motion dispatch raised")

    @window.event
    def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
        scale = max(1.0, float(getattr(app, "_scale", 1.0)))
        x_log = int(x / scale)
        y_log = int(y / scale)
        y_conv = int(getattr(app, "height", 0)) - y_log
        try:
            app._dispatch_mouse_motion(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_drag_dispatch_exc", "Mouse drag dispatch raised")

    @window.event
    def on_mouse_scroll(x, y, scroll_x, scroll_y):
        scale = max(1.0, float(getattr(app, "_scale", 1.0)))
        x_log = int(x / scale)
        y_log = int(y / scale)
        y_conv = int(getattr(app, "height", 0)) - y_log
        try:
            app._dispatch_mouse_scroll(x_log, y_conv, scroll_x, scroll_y)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_scroll_dispatch_exc", "Mouse scroll dispatch raised")

    @window.event
    def on_key_press(symbol, modifiers):
        key_name, norm_mods = _normalize_key(symbol, modifiers)

        nonlocal esc_down
        if str(key_name).strip().lower() == "escape":
            can_handle = False
            probe = getattr(app, "can_handle_back_event", None)
            if callable(probe):
                try:
                    can_handle = bool(probe())
                except Exception:
                    exception_once(logger, "pyglet_can_handle_back_event_exc", "can_handle_back_event raised")
                    can_handle = False

            if not can_handle:
                esc_down = False
                if debug_keys:
                    kn = "escape"
                    if not debug_keys_filter or kn in debug_keys_filter:
                        ts = time.perf_counter()
                        print(f"[nuiitivet] key_press t={ts:.6f} key={kn} mods={norm_mods} handled=False")
                # Let pyglet's default ESC handling run (e.g. close window).
                return False

            esc_down = True
            if debug_keys:
                kn = "escape"
                if not debug_keys_filter or kn in debug_keys_filter:
                    ts = time.perf_counter()
                    print(f"[nuiitivet] key_press t={ts:.6f} key={kn} mods={norm_mods} handled=True")
            # Handle ESC on key release to avoid OS key-repeat glitches and to
            # align with "keyup triggers back" semantics.
            return True

        try:
            handled = bool(app._dispatch_key_press(key_name, norm_mods))
        except Exception:
            exception_once(logger, "pyglet_on_key_press_dispatch_exc", "Key press dispatch raised")
            handled = False

        if debug_keys:
            kn = str(key_name).strip().lower()
            if not debug_keys_filter or kn in debug_keys_filter:
                ts = time.perf_counter()
                print(f"[nuiitivet] key_press t={ts:.6f} key={kn} mods={norm_mods} handled={handled}")

        if handled:
            try:
                app.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_key_press_invalidate_exc", "app.invalidate raised")
            # Tell pyglet the event was handled so default handlers (e.g. ESC-to-exit)
            # do not run.
            return True
        return False

    @window.event
    def on_key_release(symbol, modifiers):
        key_name, norm_mods = _normalize_key(symbol, modifiers)

        nonlocal esc_down
        if str(key_name).strip().lower() != "escape":
            return False
        if not esc_down:
            return True
        esc_down = False

        handler = getattr(app, "handle_back_event", None)
        if callable(handler):
            try:
                handled = bool(handler())
            except Exception:
                exception_once(logger, "pyglet_on_key_release_back_handler_exc", "Back handler raised")
                handled = False
        else:
            try:
                handled = bool(app._dispatch_key_press("escape", norm_mods))
            except Exception:
                exception_once(logger, "pyglet_on_key_release_dispatch_exc", "Key release dispatch raised")
                handled = False

        if debug_keys:
            kn = "escape"
            if not debug_keys_filter or kn in debug_keys_filter:
                ts = time.perf_counter()
                print(f"[nuiitivet] key_release t={ts:.6f} key={kn} mods={norm_mods} handled={handled}")

        if handled:
            try:
                app.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_key_release_invalidate_exc", "app.invalidate raised")
            return True
        return False

    @window.event
    def on_text(text):
        try:
            handled = bool(app._dispatch_text(text))
        except Exception:
            exception_once(logger, "pyglet_on_text_dispatch_exc", "Text dispatch raised")
            handled = False
        if handled:
            try:
                app.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_text_invalidate_exc", "app.invalidate raised")

    @window.event
    def on_text_motion(motion):
        motion_code = _normalize_text_motion(motion)
        try:
            handled = bool(app._dispatch_text_motion(motion_code, select=False))
        except Exception:
            exception_once(logger, "pyglet_on_text_motion_dispatch_exc", "Text motion dispatch raised")
            handled = False
        if handled:
            try:
                app.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_text_motion_invalidate_exc", "app.invalidate raised")

    @window.event
    def on_text_motion_select(motion):
        motion_code = _normalize_text_motion(motion)
        try:
            handled = bool(app._dispatch_text_motion(motion_code, select=True))
        except Exception:
            exception_once(logger, "pyglet_on_text_motion_select_dispatch_exc", "Text motion select dispatch raised")
            handled = False
        if handled:
            try:
                app.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_text_motion_select_invalidate_exc", "app.invalidate raised")

    @window.event
    def on_ime_composition(text, start, length):
        try:
            handled = bool(app._dispatch_ime_composition(text, start, length))
        except Exception:
            exception_once(logger, "pyglet_on_ime_composition_dispatch_exc", "IME composition dispatch raised")
            handled = False
        if handled:
            try:
                app.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_ime_composition_invalidate_exc", "app.invalidate raised")

    @window.event
    def on_close():
        try:
            app._dispatch_close()
        except Exception:
            exception_once(logger, "pyglet_on_close_dispatch_exc", "app._dispatch_close raised")
        try:
            pyglet.app.exit()
        except Exception:
            exception_once(logger, "pyglet_on_close_exit_exc", "pyglet.app.exit raised")

    previous_loop = getattr(pyglet.app, "event_loop", None)
    event_loop = ResponsiveEventLoop(window, app._render_frame, effective_draw_fps)
    setattr(app, "_event_loop", event_loop)

    try:
        event_loop.run()
    finally:
        try:
            setattr(app, "_event_loop", None)
            setattr(app, "_window", None)
        except Exception:
            exception_once(logger, "pyglet_cleanup_app_state_exc", "Failed to clear app._event_loop/_window")

        try:
            if previous_loop is not None and previous_loop is not event_loop:
                pyglet.app.event_loop = previous_loop
            else:
                from pyglet.app.base import EventLoop as _DefaultEventLoop

                pyglet.app.event_loop = _DefaultEventLoop()
        except Exception:
            exception_once(logger, "pyglet_restore_event_loop_exc", "Failed to restore pyglet.app.event_loop")


def _draw_raster_frame(app: Any, skia: Any) -> bool:
    try:
        img: Any
        render_snapshot = getattr(app, "_render_snapshot", None)
        if callable(render_snapshot):
            scale = max(1.0, float(getattr(app, "_scale", 1.0)))
            snapshot = render_snapshot(scale=scale)

            # Fast path: avoid PNG encode/decode and upload raw pixels directly.
            # skia.Image.tobytes() returns RGBA (top-to-bottom).
            if hasattr(snapshot, "tobytes") and callable(getattr(snapshot, "tobytes")):
                rgba = snapshot.tobytes()
                width = int(snapshot.width())
                height = int(snapshot.height())
                pitch = -width * 4
                img = pyglet.image.ImageData(width, height, "RGBA", rgba, pitch=pitch)
            else:
                png_bytes = app._render_to_png_bytes()
                buf = io.BytesIO(png_bytes)
                img = pyglet.image.load("", file=buf)
        else:
            png_bytes = app._render_to_png_bytes()
            buf = io.BytesIO(png_bytes)
            img = pyglet.image.load("", file=buf)

        setattr(app, "_last_image", img)
        setattr(app, "_dirty", False)
        return True
    except Exception:
        exception_once(logger, "pyglet_draw_raster_frame_exc", "Failed to draw raster frame")
        return False


def _install_ime_patch(window: object) -> None:
    try:
        import sys

        if sys.platform == "darwin":
            from .ime.macos import install_patch

            install_patch(window)
        elif sys.platform == "win32":
            from .ime.windows import install_patch

            install_patch(window)
        elif sys.platform == "linux":
            from .ime.linux import install_patch

            install_patch(window)
    except Exception:
        exception_once(logger, "pyglet_install_ime_patch_exc", "Failed to install IME patch")


def _patch_pyglet_cocoa_view() -> None:
    try:
        import sys

        if sys.platform != "darwin":
            return

        from pyglet.window.cocoa import pyglet_view
        from pyglet.libs.darwin.cocoapy import runtime

        # Patch ObjCInstance.__getattr__ to handle missing _window on PygletView
        # This is needed because ToggleFullScreen (and other window ops) can cause
        # PygletView to receive events while temporarily detached or recreated,
        # leading to missing _window attribute on the ObjCInstance wrapper.
        if not getattr(runtime, "_nuiitivet_getattr_patched", False):
            original_getattr = runtime.ObjCInstance.__getattr__

            class DummyWindow:
                def __setattr__(self, key, value):
                    pass

                def __getattr__(self, key):
                    # Return a dummy callable that does nothing, to handle method calls
                    return lambda *args, **kwargs: None

            dummy_window = DummyWindow()

            def safe_getattr(self, name):
                try:
                    return original_getattr(self, name)
                except AttributeError:
                    if name == "_window":
                        try:
                            if self.objc_class.name == b"PygletView":
                                return dummy_window
                        except Exception:
                            pass
                    raise

            runtime.ObjCInstance.__getattr__ = safe_getattr  # type: ignore[method-assign]
            setattr(runtime, "_nuiitivet_getattr_patched", True)

        if getattr(pyglet_view, "_nuiitivet_patched", False):
            return

        original_getMousePosition = pyglet_view.getMousePosition

        def safe_getMousePosition(self, nsevent):
            # Check for _window. If patched getattr returns dummy, check if it's the dummy.
            # Or just let it proceed, as dummy.context will be None and getMousePosition handles that.
            if not hasattr(self, "_window"):
                return 0, 0
            return original_getMousePosition(self, nsevent)

        pyglet_view.getMousePosition = safe_getMousePosition
        setattr(pyglet_view, "_nuiitivet_patched", True)

    except ImportError:
        pass
    except Exception:
        exception_once(logger, "pyglet_cocoa_view_patch_exc", "Failed to patch pyglet cocoa view")


def _normalize_key(symbol: int, modifiers: int) -> tuple[str, int]:
    try:
        keymod = pyglet.window.key

        norm_mods = 0
        if modifiers & keymod.MOD_SHIFT:
            norm_mods |= MOD_SHIFT
        if modifiers & keymod.MOD_CTRL:
            norm_mods |= MOD_CTRL
        if modifiers & keymod.MOD_ALT:
            norm_mods |= MOD_ALT
        # Map Command to META on macOS
        if modifiers & getattr(keymod, "MOD_COMMAND", 0):
            norm_mods |= MOD_META

        if symbol == keymod.TAB:
            return "tab", norm_mods
        if symbol == keymod.SPACE:
            return "space", norm_mods
        if symbol in (keymod.ENTER, keymod.RETURN):
            return "enter", norm_mods
    except Exception:
        exception_once(logger, "pyglet_normalize_key_map_exc", "Failed to normalize key/modifier mapping")

    try:
        keymod = pyglet.window.key
        name = keymod.symbol_string(symbol)
        return name.lower(), 0
    except Exception:
        exception_once(logger, "pyglet_normalize_key_symbol_string_exc", "key.symbol_string failed")
        return "", 0


def _normalize_text_motion(motion: int) -> int:
    try:
        keymod = pyglet.window.key

        if motion == keymod.MOTION_BACKSPACE:
            return TEXT_MOTION_BACKSPACE
        if motion == keymod.MOTION_DELETE:
            return TEXT_MOTION_DELETE
        if motion == keymod.MOTION_LEFT:
            return TEXT_MOTION_LEFT
        if motion == keymod.MOTION_RIGHT:
            return TEXT_MOTION_RIGHT
        if motion == keymod.MOTION_HOME:
            return TEXT_MOTION_HOME
        if motion == keymod.MOTION_END:
            return TEXT_MOTION_END
    except Exception:
        exception_once(logger, "pyglet_normalize_text_motion_exc", "Failed to normalize text motion")
    return int(motion)
