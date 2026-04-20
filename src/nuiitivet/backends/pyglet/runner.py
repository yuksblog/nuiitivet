"""Pyglet interactive runner.

This module owns the pyglet dependency so the core package remains backend-agnostic.
"""

from __future__ import annotations

import io
import logging
import math
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


def run_app(app: Any, draw_fps: Optional[float] = None) -> None:
    """Run an interactive window for the given App-like object."""

    debug_keys = _env_flag("NUIITIVET_DEBUG_KEYS", default=False)
    debug_keys_filter_raw = os.environ.get("NUIITIVET_DEBUG_KEYS_FILTER", "").strip().lower()
    debug_keys_filter = {k.strip() for k in debug_keys_filter_raw.split(",") if k.strip()}

    esc_down = False
    gl_viewport_ok = True
    auto_force_gl_viewport = False
    auto_recreate_always = False
    auto_recreate_probe_used = False
    last_resize_raw = None
    last_resize_logical = None
    auto_recreate_on_draw_used = False
    auto_recreate_on_draw_hits = 0

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
        resizable=getattr(app, "resizable", True),
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

    def _recreate_gl_context(reason: str) -> None:
        nonlocal gr_context, gpu_enabled
        if skia is None or GL is None:
            return
        try:
            gr_context = skia.GrDirectContext.MakeGL()
            if gr_context is None:
                gr_context = skia.GrDirectContext.MakeGL(None)
            gpu_enabled = gr_context is not None and GL is not None
        except Exception:
            gpu_enabled = False
            exception_once(logger, "pyglet_recreate_gl_context_exc", "Failed to recreate GL context")

    def _should_auto_recreate(raw_w: int, raw_h: int, logical_w: int, logical_h: int, scale: float) -> bool:
        if scale <= 1.0:
            return False
        if last_resize_raw is None or last_resize_logical is None:
            return False
        prev_raw_w, prev_raw_h = last_resize_raw
        prev_log_w, prev_log_h = last_resize_logical
        if prev_raw_w <= 0 or prev_raw_h <= 0 or prev_log_w <= 0 or prev_log_h <= 0:
            return False
        RAW_GROW_THRESHOLD = 1.2
        LOGICAL_SHRINK_THRESHOLD = 0.85
        raw_area = raw_w * raw_h
        prev_raw_area = prev_raw_w * prev_raw_h
        logical_area = logical_w * logical_h
        prev_logical_area = prev_log_w * prev_log_h
        raw_grew = raw_area >= int(prev_raw_area * RAW_GROW_THRESHOLD)
        logical_shrank = logical_area <= int(prev_logical_area * LOGICAL_SHRINK_THRESHOLD)
        return raw_grew and logical_shrank

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

    def _get_windows_dpi_scale() -> float:
        if sys.platform != "win32":
            return 1.0
        try:
            hwnd = getattr(window, "_hwnd", None)
            if not hwnd:
                try:
                    user32 = ctypes.windll.user32
                    get_system_dpi = getattr(user32, "GetDpiForSystem", None)
                    if get_system_dpi is None:
                        return 1.0
                    dpi = int(get_system_dpi())
                    if dpi <= 0:
                        return 1.0
                    return max(1.0, float(dpi) / 96.0)
                except Exception:
                    return 1.0
            user32 = ctypes.windll.user32
            get_dpi = getattr(user32, "GetDpiForWindow", None)
            if get_dpi is not None:
                dpi = int(get_dpi(hwnd))
                if dpi > 0:
                    return max(1.0, float(dpi) / 96.0)

            try:
                monitor = user32.MonitorFromWindow(hwnd, 2)
            except Exception:
                monitor = None

            if monitor:
                try:
                    shcore = ctypes.windll.shcore
                    get_dpi_monitor = getattr(shcore, "GetDpiForMonitor", None)
                    if get_dpi_monitor is None:
                        return 1.0
                    dpi_x = ctypes.c_uint()
                    dpi_y = ctypes.c_uint()
                    MDT_EFFECTIVE_DPI = 0
                    res = int(get_dpi_monitor(monitor, MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x), ctypes.byref(dpi_y)))
                    if res == 0 and dpi_x.value > 0:
                        return max(1.0, float(dpi_x.value) / 96.0)
                except Exception:
                    return 1.0
                try:
                    get_scale_factor = getattr(shcore, "GetScaleFactorForMonitor", None)
                    if get_scale_factor is None:
                        return 1.0
                    scale_factor = ctypes.c_int()
                    res = int(get_scale_factor(monitor, ctypes.byref(scale_factor)))
                    if res == 0 and scale_factor.value > 0:
                        return max(1.0, float(scale_factor.value) / 100.0)
                except Exception:
                    return 1.0
            try:
                gdi32 = ctypes.windll.gdi32
                target_hwnd = hwnd if hwnd else 0
                hdc = user32.GetDC(target_hwnd)
                LOGPIXELSX = 88
                dpi = int(gdi32.GetDeviceCaps(hdc, LOGPIXELSX))
                user32.ReleaseDC(target_hwnd, hdc)
                if dpi > 0:
                    return max(1.0, float(dpi) / 96.0)
            except Exception:
                return 1.0
            return 1.0
        except Exception:
            return 1.0

    def _update_app_size_from_window(source: str, width: int, height: int) -> None:
        nonlocal last_resize_raw, last_resize_logical
        nonlocal auto_recreate_always, auto_recreate_probe_used
        try:
            # Get latest scale
            current_scale = 1.0
            try:
                current_scale = float(window.get_pixel_ratio())
            except Exception:
                pass

            dpi_scale = None
            if sys.platform == "win32":
                dpi_scale = _get_windows_dpi_scale()
                if current_scale <= 1.0 and dpi_scale and dpi_scale > 1.0:
                    current_scale = dpi_scale

            fb_w = None
            fb_h = None
            try:
                if hasattr(window, "get_framebuffer_size"):
                    fb_w, fb_h = window.get_framebuffer_size()
            except Exception:
                fb_w = None
                fb_h = None

            derived_scale = None
            if fb_w and fb_h and int(width) > 0 and int(height) > 0:
                try:
                    derived_scale = max(float(fb_w) / float(width), float(fb_h) / float(height))
                except Exception:
                    derived_scale = None

            scale = max(1.0, current_scale)
            if derived_scale and derived_scale > 1.0:
                if abs(derived_scale - current_scale) < 0.05:
                    scale = max(scale, derived_scale)

            # Ignore minimize/hidden 0-size events to avoid collapsing layout.
            if int(width) <= 0 or int(height) <= 0:
                return

            # Compute logical size. If framebuffer size is available, detect whether
            # width/height are already logical or physical.
            raw_w = int(width)
            raw_h = int(height)
            if scale > 1.0:
                div_w = int(math.ceil(width / scale))
                div_h = int(math.ceil(height / scale))
            else:
                div_w = int(round(width / scale))
                div_h = int(round(height / scale))

            logical_w = div_w
            logical_h = div_h

            if fb_w and fb_h and scale > 1.0:
                try:
                    phys_candidate = int(raw_w * scale)
                    # If framebuffer matches width, width is physical.
                    if abs(fb_w - raw_w) <= abs(fb_w - phys_candidate):
                        logical_w = div_w
                        logical_h = div_h
                    else:
                        logical_w = raw_w
                        logical_h = raw_h
                except Exception:
                    logical_w = div_w
                    logical_h = div_h
            elif sys.platform == "win32" and scale > 1.0:
                prev_w = int(getattr(app, "width", 0) or 0)
                prev_h = int(getattr(app, "height", 0) or 0)
                if prev_w > 0 and prev_h > 0:
                    raw_delta = abs(raw_w - prev_w) + abs(raw_h - prev_h)
                    div_delta = abs(div_w - prev_w) + abs(div_h - prev_h)
                    use_raw = raw_delta <= div_delta
                else:
                    use_raw = div_w < 200 or div_h < 200
                logical_w = raw_w if use_raw else div_w
                logical_h = raw_h if use_raw else div_h

            # Update app state
            app.width = int(max(1, logical_w))
            app.height = int(max(1, logical_h))
            setattr(app, "_scale", scale)

            if (
                not auto_recreate_always
                and gpu_enabled
                and _should_auto_recreate(raw_w, raw_h, logical_w, logical_h, scale)
            ):
                if auto_recreate_probe_used:
                    auto_recreate_always = True
                else:
                    auto_recreate_probe_used = True
                _recreate_gl_context("auto-resize")

            last_resize_raw = (raw_w, raw_h)
            last_resize_logical = (app.width, app.height)

        except Exception:
            exception_once(logger, "pyglet_on_resize_set_size_exc", "Failed to set app.width/app.height")

        try:
            app.invalidate(immediate=True)
        except Exception:
            exception_once(logger, "pyglet_on_resize_invalidate_exc", "app.invalidate raised")

    @window.event
    def on_draw():
        nonlocal gpu_enabled, auto_force_gl_viewport
        nonlocal auto_recreate_on_draw_used, auto_recreate_on_draw_hits, auto_recreate_always
        try:
            wx, wy = window.get_location()
            IMEManager.get().update_window_info(wx, wy, window.width, window.height)
        except Exception:
            exception_once(logger, "pyglet_on_draw_ime_update_exc", "IME window info update raised")

        try:
            win_w = int(getattr(window, "width", 0))
            win_h = int(getattr(window, "height", 0))
        except Exception:
            win_w = 0
            win_h = 0
        try:
            cur_scale = float(getattr(app, "_scale", 1.0))
        except Exception:
            cur_scale = 1.0
        scale_changed = False
        try:
            latest_scale = float(window.get_pixel_ratio())
            if abs(latest_scale - cur_scale) >= 0.01:
                scale_changed = True
        except Exception:
            scale_changed = False

        if (win_w and win_h) and (
            win_w != int(getattr(app, "width", 0)) or win_h != int(getattr(app, "height", 0)) or scale_changed
        ):
            _update_app_size_from_window("on_draw", win_w, win_h)

        if gpu_enabled and gr_context is not None and GL is not None:
            fb_w = 0
            fb_h = 0
            try:
                if hasattr(window, "get_framebuffer_size"):
                    fb_size = window.get_framebuffer_size()
                    if fb_size:
                        fb_w = int(fb_size[0])
                        fb_h = int(fb_size[1])
            except Exception:
                fb_w = 0
                fb_h = 0

            nonlocal gl_viewport_ok
            if fb_w > 0 and fb_h > 0 and gl_viewport_ok and auto_force_gl_viewport:
                try:
                    target_w = fb_w
                    target_h = fb_h
                    try:
                        if hasattr(GL, "glGetIntegerv") and hasattr(GL, "GL_MAX_VIEWPORT_DIMS"):
                            max_dims = GL.glGetIntegerv(GL.GL_MAX_VIEWPORT_DIMS)
                            if max_dims is not None and len(max_dims) >= 2:
                                max_w = int(max_dims[0])
                                max_h = int(max_dims[1])
                                if max_w > 0 and max_h > 0:
                                    target_w = min(target_w, max_w)
                                    target_h = min(target_h, max_h)
                    except Exception:
                        target_w = fb_w
                        target_h = fb_h

                    target_w = max(1, int(target_w))
                    target_h = max(1, int(target_h))
                    if hasattr(GL, "glViewport"):
                        GL.glViewport(0, 0, target_w, target_h)
                except Exception:
                    gl_viewport_ok = False
                    gpu_enabled = False
                    exception_once(logger, "pyglet_on_draw_gl_viewport_exc", "Failed to set GL viewport")

            if gpu_enabled:
                try:
                    if hasattr(GL, "glGetIntegerv") and hasattr(GL, "GL_VIEWPORT"):
                        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
                        if viewport is not None and len(viewport) >= 4:
                            vp_w = int(viewport[2])
                            vp_h = int(viewport[3])
                        else:
                            vp_w = None
                            vp_h = None
                    else:
                        vp_w = None
                        vp_h = None
                except Exception:
                    vp_w = None
                    vp_h = None

                if (vp_w is None or vp_h is None) and fb_w > 0 and fb_h > 0:
                    if not auto_force_gl_viewport:
                        auto_force_gl_viewport = True
                    if not auto_recreate_on_draw_used:
                        auto_recreate_on_draw_used = True
                        auto_recreate_on_draw_hits += 1
                        if not auto_recreate_always:
                            auto_recreate_always = True
                        _recreate_gl_context("auto-draw")
                if (vp_w is None or vp_h is None) and fb_w > 0 and fb_h > 0 and hasattr(GL, "glViewport"):
                    try:
                        GL.glViewport(0, 0, int(fb_w), int(fb_h))
                        vp_w = int(fb_w)
                        vp_h = int(fb_h)
                    except Exception:
                        pass

                if vp_w and vp_h and vp_w > 0 and vp_h > 0:
                    try:
                        win_w = int(getattr(window, "width", 0))
                        win_h = int(getattr(window, "height", 0))
                    except Exception:
                        win_w = 0
                        win_h = 0

                    if win_w > 0 and win_h > 0:
                        scale_from_vp = max(float(vp_w) / float(win_w), float(vp_h) / float(win_h))
                        logical_w = int(win_w)
                        logical_h = int(win_h)
                        if sys.platform == "win32" and scale_from_vp <= 1.0:
                            dpi_scale = _get_windows_dpi_scale()
                            if dpi_scale > 1.0:
                                scale_from_vp = dpi_scale
                                if scale_from_vp > 1.0:
                                    logical_w = int(max(1, math.ceil(win_w / scale_from_vp)))
                                    logical_h = int(max(1, math.ceil(win_h / scale_from_vp)))
                                else:
                                    logical_w = int(max(1, round(win_w / scale_from_vp)))
                                    logical_h = int(max(1, round(win_h / scale_from_vp)))
                        try:
                            if logical_w != int(getattr(app, "width", 0)) or logical_h != int(
                                getattr(app, "height", 0)
                            ):
                                app.width = int(logical_w)
                                app.height = int(logical_h)
                            if abs(float(getattr(app, "_scale", 1.0)) - scale_from_vp) >= 0.01:
                                setattr(app, "_scale", max(1.0, scale_from_vp))
                        except Exception:
                            exception_once(
                                logger, "pyglet_on_draw_gpu_viewport_sync_exc", "Failed to sync from viewport"
                            )

                try:
                    ok = bool(draw_gpu_frame(app, gr_context, GL, skia))
                except Exception:
                    exception_once(logger, "pyglet_on_draw_gpu_frame_exc", "draw_gpu_frame raised")
                    ok = False
                if ok:
                    return
                gpu_enabled = False

        if getattr(app, "_dirty", False) or getattr(app, "_last_image", None) is None:
            ok = _draw_raster_frame(app, skia)
            if not ok and getattr(app, "_last_image", None) is None:
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
    def on_show():
        try:
            setattr(app, "_last_image", None)
        except Exception:
            pass
        try:
            _update_app_size_from_window("on_show", window.width, window.height)
        except Exception:
            exception_once(logger, "pyglet_on_show_resize_exc", "Failed to sync size on show")

    @window.event
    def on_hide():
        pass

    @window.event
    def on_activate():
        try:
            setattr(app, "_last_image", None)
        except Exception:
            pass
        try:
            _update_app_size_from_window("on_activate", window.width, window.height)
        except Exception:
            exception_once(logger, "pyglet_on_activate_resize_exc", "Failed to sync size on activate")

    @window.event
    def on_deactivate():
        pass

    @window.event
    def on_resize(width, height):
        nonlocal last_resize_raw, auto_recreate_on_draw_used  # noqa: F824
        try:
            next_w = int(width)
            next_h = int(height)
        except Exception:
            next_w = 0
            next_h = 0
        if next_w > 0 and next_h > 0 and last_resize_raw is not None:
            prev_w, prev_h = last_resize_raw
            if int(prev_w) != next_w or int(prev_h) != next_h:
                auto_recreate_on_draw_used = False
        if auto_recreate_always and gpu_enabled:
            _recreate_gl_context("resize")
        _update_app_size_from_window("on_resize", width, height)

    def _to_logical(x: int, y: int) -> tuple[int, int]:
        scale = max(1.0, float(getattr(app, "_scale", 1.0)))
        x_log = int(x / scale)
        y_log = int(y / scale)
        y_conv = int(getattr(app, "height", 0)) - y_log
        return x_log, y_conv

    @window.event
    def on_mouse_press(x, y, button, modifiers):
        x_log, y_conv = _to_logical(x, y)
        try:
            app._dispatch_mouse_press(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_press_dispatch_exc", "Mouse press dispatch raised")

    @window.event
    def on_mouse_release(x, y, button, modifiers):
        x_log, y_conv = _to_logical(x, y)
        try:
            app._dispatch_mouse_release(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_release_dispatch_exc", "Mouse release dispatch raised")

    @window.event
    def on_mouse_motion(x, y, dx, dy):
        x_log, y_conv = _to_logical(x, y)
        try:
            app._dispatch_mouse_motion(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_motion_dispatch_exc", "Mouse motion dispatch raised")

    @window.event
    def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
        x_log, y_conv = _to_logical(x, y)
        try:
            app._dispatch_mouse_motion(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_drag_dispatch_exc", "Mouse drag dispatch raised")

    @window.event
    def on_mouse_scroll(x, y, scroll_x, scroll_y):
        x_log, y_conv = _to_logical(x, y)
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

    # IMPORTANT: align observable runtime clock with the actual event-loop clock
    # that is ticked in ResponsiveEventLoop.run()/run_async().
    try:
        set_clock(event_loop.clock)
    except Exception:
        exception_once(logger, "pyglet_set_event_loop_clock_exc", "set_clock(event_loop.clock) failed")

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
