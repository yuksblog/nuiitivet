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

from nuiitivet.rendering.skia import get_skia

from nuiitivet.input.codes import (
    BUTTON_LEFT,
    BUTTON_MIDDLE,
    BUTTON_RIGHT,
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
from nuiitivet.runtime.threading import set_ui_thread
from nuiitivet.common.logging_once import debug_once, exception_once, warning_once
from nuiitivet.runtime.renderer import RendererMode

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


def _inspect_consumed(app: Any, hook: str, *args: Any) -> bool:
    """Offer an input event to the dev-only inspect mode; ``True`` if it took it.

    Absent -- production, or any run without the dev runner -- this is a single
    ``getattr`` returning ``None``, so the input path pays nothing for it. A
    failure inside the mode must never swallow the human's input, so it degrades
    to "not consumed" and the event continues to the app (#591).
    """
    mode = getattr(app, "_inspect_mode", None)
    if mode is None:
        return False
    try:
        return bool(getattr(mode, hook)(*args))
    except Exception:
        exception_once(logger, "pyglet_inspect_mode_exc", "Inspect mode hook raised")
        return False


def run_app(app: Any, draw_fps: Optional[float] = None, renderer: RendererMode = "auto") -> None:
    """Run an interactive window for the given App-like object.

    ``renderer`` selects the drawing backend: ``"auto"`` (GPU with raster
    fallback), ``"gpu"`` (require GPU; raise on failure), or ``"cpu"`` (always
    raster). See :class:`nuiitivet.runtime.renderer.RendererMode`.
    """

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
        # The thread that installs the clock is the thread its callbacks fire
        # on, which is what "the UI thread" has to mean for a marshalled
        # observable write to land somewhere safe.
        set_ui_thread()
        set_clock(pyglet.clock)
    except Exception:
        exception_once(logger, "pyglet_set_clock_exc", "set_clock(pyglet.clock) failed")

    _patch_pyglet_cocoa_view()

    if draw_fps is not None:
        try:
            app.set_draw_fps(draw_fps)
        except Exception:
            exception_once(logger, "pyglet_set_draw_fps_exc", "app.set_draw_fps raised")

    effective_draw_fps = getattr(app, "_preferred_draw_fps", None)

    def _draw_windows(dt: float) -> None:
        for win in list(getattr(app, "windows", ()) or ()):
            render = getattr(win, "_render_frame", None)
            if callable(render):
                try:
                    render(dt)
                except Exception:
                    exception_once(logger, "pyglet_draw_window_exc", "Window._render_frame raised")

    def _keep_running_without_windows() -> bool:
        from nuiitivet.runtime.app import ExitPolicy

        return getattr(app, "exit_policy", None) is ExitPolicy.EXPLICIT

    previous_loop = getattr(pyglet.app, "event_loop", None)
    event_loop = ResponsiveEventLoop(
        _draw_windows,
        effective_draw_fps,
        keep_running_without_windows=_keep_running_without_windows,
    )
    setattr(app, "_event_loop", event_loop)

    # IMPORTANT: align observable runtime clock with the actual event-loop clock
    # that is ticked in ResponsiveEventLoop.run()/run_async().
    try:
        set_clock(event_loop.clock)
    except Exception:
        exception_once(logger, "pyglet_set_event_loop_clock_exc", "set_clock(event_loop.clock) failed")

    def _realize(win: Any) -> None:
        _realize_window(app, win, event_loop, renderer)

    # Windows opened while the loop runs are realized immediately through this
    # hook; the ones already open (the main window, and any opened before
    # run()) are realized here, in open order.
    setattr(app, "_realize_window_hook", _realize)
    for win in list(getattr(app, "windows", ()) or ()):
        _realize(win)

    try:
        install_tray = getattr(app, "_install_tray", None)
        if callable(install_tray):
            install_tray()
    except Exception:
        exception_once(logger, "pyglet_install_tray_exc", "Tray icon install raised")

    try:
        event_loop.run()
    finally:
        try:
            uninstall_tray = getattr(app, "_uninstall_tray", None)
            if callable(uninstall_tray):
                uninstall_tray()
        except Exception:
            exception_once(logger, "pyglet_uninstall_tray_exc", "Tray icon uninstall raised")
        try:
            setattr(app, "_realize_window_hook", None)
            setattr(app, "_event_loop", None)
            for win in list(getattr(app, "windows", ()) or ()):
                setattr(win, "_event_loop", None)
                setattr(win, "_window", None)
        except Exception:
            exception_once(logger, "pyglet_cleanup_app_state_exc", "Failed to clear event-loop/window state")

        try:
            if previous_loop is not None and previous_loop is not event_loop:
                pyglet.app.event_loop = previous_loop
            else:
                from pyglet.app.base import EventLoop as _DefaultEventLoop

                pyglet.app.event_loop = _DefaultEventLoop()
        except Exception:
            exception_once(logger, "pyglet_restore_event_loop_exc", "Failed to restore pyglet.app.event_loop")


def _realize_window(owner_app: Any, win: Any, event_loop: Any, renderer: RendererMode = "auto") -> None:
    """Create and wire the OS window for one open ``Window``.

    Everything window-scoped lives here: the pyglet window and its event
    handlers, the per-window GPU state, HiDPI tracking, and the IME patch.
    Called once per ``Window`` — for windows already open when ``run_app``
    starts, and through ``app._realize_window_hook`` for windows opened while
    the loop is running.
    """
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
    # Normalize root if available
    try:
        root = getattr(win, "root", None)
        if root is not None:
            from nuiitivet.widgeting.widget import ComposableWidget

            if isinstance(root, ComposableWidget):
                built = root.evaluate_build()
                if built is not None:
                    setattr(win, "root", built)
    except Exception:
        exception_once(logger, "pyglet_normalize_root_exc", "Failed to normalize win.root via evaluate_build")

    try:
        setattr(win, "_dirty", True)
        setattr(win, "_last_image", None)
    except Exception:
        exception_once(logger, "pyglet_init_app_state_exc", "Failed to initialize win state (_dirty/_last_image)")

    caption = None
    style = None
    try:
        title_val = getattr(win, "_title_value", None)
        if isinstance(title_val, str):
            caption = title_val
        elif title_val is not None and hasattr(title_val, "value"):
            v = title_val.value
            if v is not None:
                caption = str(v)
    except Exception:
        exception_once(logger, "pyglet_get_title_exc", "Failed to get window title")

    try:
        chrome = getattr(win, "chrome", None)
        if chrome is None:
            # chrome=None → bare borderless
            style = pyglet.window.Window.WINDOW_STYLE_BORDERLESS
        else:
            chrome_type = type(chrome).__name__
            if chrome_type == "OSChrome":
                variant = getattr(chrome, "variant", "default")
                _variant_map = {
                    "dialog": pyglet.window.Window.WINDOW_STYLE_DIALOG,
                    "tool": pyglet.window.Window.WINDOW_STYLE_TOOL,
                    "borderless": pyglet.window.Window.WINDOW_STYLE_BORDERLESS,
                    "transparent": pyglet.window.Window.WINDOW_STYLE_TRANSPARENT,
                }
                style = _variant_map.get(variant)  # None → OS default
            elif chrome_type == "CustomChrome":
                # Always borderless for custom chrome — WINDOW_STYLE_TRANSPARENT
                # restores OS decorations on macOS and is not needed here.
                # Corner rounding is applied in the render layer (gpu_frame.py).
                style = pyglet.window.Window.WINDOW_STYLE_BORDERLESS
    except Exception:
        exception_once(logger, "pyglet_get_chrome_exc", "Failed to determine window style from chrome")

    try:
        visible_obs = getattr(win, "_visible_obs", None)
        window = pyglet.window.Window(
            width=getattr(win, "width", 0),
            height=getattr(win, "height", 0),
            caption=caption,
            style=style,
            vsync=False,
            resizable=getattr(win, "resizable", True),
            file_drops=True,
            # A window hidden before realization starts hidden (start-in-tray)
            # instead of flashing on screen.
            visible=True if visible_obs is None else bool(visible_obs.value),
        )
    except Exception:
        logger.error(
            "Failed to create the application window. App.run() requires a display; "
            "headless environments cannot run an interactive window and should render "
            "offscreen via App.render_to_png() instead.",
            exc_info=True,
        )
        raise

    # Check scale immediately and resize if needed
    try:
        scale = float(window.get_pixel_ratio())
        if scale > 1.0:
            log_w = getattr(win, "width", 800)
            log_h = getattr(win, "height", 600)
            phys_w = int(log_w * scale)
            phys_h = int(log_h * scale)

            if phys_w > window.width:
                window.set_size(phys_w, phys_h)

            setattr(win, "_scale", max(1.0, scale))
    except Exception:
        exception_once(logger, "pyglet_initial_resize_exc", "Failed to adjust initial window size for HiDPI")

    setattr(win, "_window", window)
    setattr(win, "_event_loop", event_loop)

    # The window (and on macOS the NSApplication) now exists: give the App a
    # chance to attach platform integrations that need it (the menu bar's
    # NSMenu bridge).
    try:
        notify_window_created = getattr(win, "_on_window_created", None)
        if callable(notify_window_created):
            notify_window_created()
    except Exception:
        exception_once(logger, "pyglet_on_window_created_exc", "App._on_window_created raised")

    # Apply Observable title now that the window exists
    try:
        title_val = getattr(win, "_title_value", None)
        if title_val is not None and hasattr(title_val, "value"):
            v = title_val.value
            window.set_caption(str(v) if v is not None else "")
    except Exception:
        exception_once(logger, "pyglet_apply_obs_title_exc", "Failed to apply Observable title to window")

    # Initial window positioning.
    try:
        pos = getattr(win, "window_position", None)
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

    # Skia / GL setup
    gpu_enabled = False
    gr_context = None
    GL = None
    skia = get_skia(raise_if_missing=False)
    if renderer == "cpu":
        # Software/raster renderer requested: skip GPU initialization entirely.
        logger.info("renderer='cpu': using software (raster) rendering")
    elif skia is None:
        if renderer == "gpu":
            raise RuntimeError("renderer='gpu' was requested but the Skia backend is unavailable.")
        warning_once(
            logger,
            "pyglet_renderer_skia_unavailable",
            "Skia unavailable; using software (raster) rendering",
        )
    else:
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
        if not gpu_enabled:
            if renderer == "gpu":
                raise RuntimeError(
                    "renderer='gpu' was requested but the GPU backend could not be initialized "
                    "(GrDirectContext.MakeGL failed or OpenGL is unavailable). This environment "
                    "may lack a usable GPU or OpenGL context."
                )
            # renderer == "auto": degrade to software rendering.
            warning_once(
                logger,
                "pyglet_renderer_auto_gpu_unavailable",
                "GPU renderer unavailable; falling back to software (raster) rendering",
            )

    def _recreate_gl_context(reason: str) -> None:
        nonlocal gr_context, gpu_enabled
        if skia is None or GL is None:
            return
        try:
            gr_context = skia.GrDirectContext.MakeGL()
            if gr_context is None:
                gr_context = skia.GrDirectContext.MakeGL(None)
            gpu_enabled = gr_context is not None and GL is not None
            # The cached full frame is a GPU image bound to the old context; it is
            # invalid on the new one. Drop it and force a fresh full paint so the
            # next frame re-snapshots against the recreated context.
            setattr(win, "_gpu_frame_cache", None)
            setattr(win, "_gpu_frame_cache_size", None)
            setattr(win, "_paint_dirty", True)
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
        setattr(win, "_scale", max(1.0, scale))
    except Exception:
        exception_once(logger, "pyglet_set_app_scale_exc", "Failed to set win._scale")

    _install_ime_patch(window, win)
    _install_first_mouse_patch(window, win)

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
                prev_w = int(getattr(win, "width", 0) or 0)
                prev_h = int(getattr(win, "height", 0) or 0)
                if prev_w > 0 and prev_h > 0:
                    raw_delta = abs(raw_w - prev_w) + abs(raw_h - prev_h)
                    div_delta = abs(div_w - prev_w) + abs(div_h - prev_h)
                    use_raw = raw_delta <= div_delta
                else:
                    use_raw = div_w < 200 or div_h < 200
                logical_w = raw_w if use_raw else div_w
                logical_h = raw_h if use_raw else div_h

            # Update win state
            win.width = int(max(1, logical_w))
            win.height = int(max(1, logical_h))
            setattr(win, "_scale", scale)

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
            last_resize_logical = (win.width, win.height)

        except Exception:
            exception_once(logger, "pyglet_on_resize_set_size_exc", "Failed to set win.width/win.height")

        try:
            win.invalidate(immediate=True)
        except Exception:
            exception_once(logger, "pyglet_on_resize_invalidate_exc", "win.invalidate raised")

    @window.event
    def on_draw():
        nonlocal gpu_enabled, auto_force_gl_viewport
        nonlocal auto_recreate_on_draw_used, auto_recreate_on_draw_hits, auto_recreate_always
        try:
            # IME state is per window: each window publishes its own geometry
            # into its own IMEManager, focused or not.
            wx, wy = window.get_location()
            win.ime.update_window_info(wx, wy, window.width, window.height)
        except Exception:
            exception_once(logger, "pyglet_on_draw_ime_update_exc", "IME window info update raised")

        try:
            win_w = int(getattr(window, "width", 0))
            win_h = int(getattr(window, "height", 0))
        except Exception:
            win_w = 0
            win_h = 0
        try:
            cur_scale = float(getattr(win, "_scale", 1.0))
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
            win_w != int(getattr(win, "width", 0)) or win_h != int(getattr(win, "height", 0)) or scale_changed
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
                            if logical_w != int(getattr(win, "width", 0)) or logical_h != int(
                                getattr(win, "height", 0)
                            ):
                                win.width = int(logical_w)
                                win.height = int(logical_h)
                            if abs(float(getattr(win, "_scale", 1.0)) - scale_from_vp) >= 0.01:
                                setattr(win, "_scale", max(1.0, scale_from_vp))
                        except Exception:
                            exception_once(
                                logger, "pyglet_on_draw_gpu_viewport_sync_exc", "Failed to sync from viewport"
                            )

                try:
                    ok = bool(draw_gpu_frame(win, gr_context, GL, skia))
                except Exception:
                    exception_once(logger, "pyglet_on_draw_gpu_frame_exc", "draw_gpu_frame raised")
                    ok = False
                if ok:
                    return
                if renderer == "gpu":
                    logger.error("renderer='gpu': GPU frame rendering failed")
                    raise RuntimeError("renderer='gpu' was requested but GPU frame rendering failed.")
                gpu_enabled = False

        if getattr(win, "_dirty", False) or getattr(win, "_last_image", None) is None:
            ok = _draw_raster_frame(win, skia)
            if not ok and getattr(win, "_last_image", None) is None:
                return

        try:
            window.clear()
        except Exception:
            exception_once(logger, "pyglet_on_draw_window_clear_exc", "window.clear raised")

        img = getattr(win, "_last_image", None)
        if img is not None:
            try:
                img.blit(0, 0)
            except Exception:
                exception_once(logger, "pyglet_on_draw_image_blit_exc", "image.blit raised")

    @window.event
    def on_show():
        try:
            setattr(win, "_last_image", None)
        except Exception:
            pass
        try:
            _update_app_size_from_window("on_show", window.width, window.height)
        except Exception:
            exception_once(logger, "pyglet_on_show_resize_exc", "Failed to sync size on show")
        # On-demand drawing skips frames while clean, so a newly shown window
        # (which may have a discarded/undefined back buffer) must explicitly
        # request a repaint rather than relying on a cadence frame arriving.
        # The tree content is unchanged, so the GPU path may re-blit its cached
        # full frame (content=False) instead of re-walking the tree.
        try:
            win.invalidate(immediate=True, content=False)
        except Exception:
            exception_once(logger, "pyglet_on_show_invalidate_exc", "win.invalidate raised")

    @window.event
    def on_hide():
        pass

    @window.event
    def on_activate():
        try:
            win._set_os_active(True)
        except Exception:
            exception_once(logger, "pyglet_on_activate_os_active_exc", "OS-active focus hook raised")
        # Best-effort keep-above: a parent activated while a modal child is
        # open hands the OS focus back to the child (the parent's input is
        # blocked anyway).
        try:
            modal_child = win._modal_child()
            if modal_child is not None:
                child_os = getattr(modal_child, "_window", None)
                if child_os is not None and hasattr(child_os, "activate"):
                    child_os.activate()
        except Exception:
            exception_once(logger, "pyglet_on_activate_modal_child_exc", "Modal child activate raised")
        try:
            setattr(win, "_last_image", None)
        except Exception:
            pass
        try:
            _update_app_size_from_window("on_activate", window.width, window.height)
        except Exception:
            exception_once(logger, "pyglet_on_activate_resize_exc", "Failed to sync size on activate")
        # Regaining focus can follow the compositor discarding our surface; force
        # a repaint so on-demand drawing does not leave a stale frame on screen.
        # The tree content is unchanged, so the GPU path may re-blit its cached
        # full frame (content=False) instead of re-walking the tree.
        try:
            win.invalidate(immediate=True, content=False)
        except Exception:
            exception_once(logger, "pyglet_on_activate_invalidate_exc", "win.invalidate raised")

    @window.event
    def on_deactivate():
        # Focus left the window, so key-up events for anything currently held
        # will be delivered to another win and never reach us. Clear the
        # authoritative modifier-key mask and the Escape latch so a key released
        # while inactive cannot leave permanently-wrong state behind.
        nonlocal esc_down
        esc_down = False
        try:
            win._set_os_active(False)
        except Exception:
            exception_once(logger, "pyglet_on_deactivate_os_active_exc", "OS-active focus hook raised")
        # After the model committed its pending composition (in _set_os_active):
        # drop the OS input method's conversation for this window, so refocusing
        # it later cannot resume marked text the widget no longer holds.
        _discard_ime_conversation(window)
        try:
            win._clear_modifier_keys()
        except Exception:
            exception_once(logger, "pyglet_on_deactivate_clear_modifier_keys_exc", "Failed to clear modifier-key mask")

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
        scale = max(1.0, float(getattr(win, "_scale", 1.0)))
        x_log = int(x / scale)
        y_log = int(y / scale)
        y_conv = int(getattr(win, "height", 0)) - y_log
        return x_log, y_conv

    def _normalize_scroll_delta(scroll_x: float, scroll_y: float) -> tuple[float, float]:
        """Normalize Pyglet raw scroll values to the win convention.

        Convention: positive scroll_y = move content downward (offset increases),
        positive scroll_x = move content rightward (offset increases).

        On macOS, Pyglet negates AppKit's ``deltaY`` so vertical values already
        match the win convention, but ``deltaX`` is passed through with AppKit's
        native sign, which is opposite to the win convention.  Negate scroll_x to
        compensate while leaving scroll_y unchanged.  On Windows and Linux,
        Pyglet reports scroll_y > 0 for wheel-forward (up), which is opposite to
        the win convention, so both axes are negated.
        """
        if sys.platform == "darwin":
            return -scroll_x, scroll_y
        # Windows and Linux: negate to match win convention
        return -scroll_x, -scroll_y

    @window.event
    def on_mouse_press(x, y, button, modifiers):
        x_log, y_conv = _to_logical(x, y)
        button_n = _normalize_mouse_button(button)
        modifier_keys = _normalize_modifiers(modifiers)
        # Dev-only: while inspect mode is latched, a press is the human aiming a
        # designation, not an interaction. It is consumed *before* dispatch --
        # letting it through would fire the button they were merely pointing at
        # (#591).
        if _inspect_consumed(win, "on_mouse_press", win, x_log, y_conv, modifier_keys):
            return True
        try:
            win._dispatch_mouse_press(x_log, y_conv, button=button_n, modifier_keys=modifier_keys)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_press_dispatch_exc", "Mouse press dispatch raised")
        # Dev-only: record the human's click for the interaction journal (#390).
        # Only the real input path reaches here; the assistant's synthesized
        # clicks enter below at ``_dispatch_*``, so this captures the human alone.
        recorder = getattr(win, "_interaction_recorder", None)
        if recorder is not None:
            try:
                recorder.on_mouse_press(win, x_log, y_conv)
            except Exception:
                exception_once(logger, "pyglet_on_mouse_press_record_exc", "Interaction record raised")

    @window.event
    def on_mouse_release(x, y, button, modifiers):
        x_log, y_conv = _to_logical(x, y)
        button_n = _normalize_mouse_button(button)
        modifier_keys = _normalize_modifiers(modifiers)
        # Dev-only: release is where a designation resolves -- travel distance
        # tells a click (pick a widget) from a drag (#591), and the accelerator
        # turns the click into a jump to the widget's source instead (#593).
        # Modifiers are read here, not on press, so the two decisions are made at
        # the same moment from the same event.
        if _inspect_consumed(win, "on_mouse_release", win, x_log, y_conv, modifier_keys):
            return True
        try:
            win._dispatch_mouse_release(x_log, y_conv, button=button_n, modifier_keys=modifier_keys)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_release_dispatch_exc", "Mouse release dispatch raised")

    @window.event
    def on_mouse_motion(x, y, dx, dy):
        x_log, y_conv = _to_logical(x, y)
        # Dev-only: tracks the pick candidate under the cursor for the overlay's
        # hover highlight (#591).
        if _inspect_consumed(win, "on_mouse_motion", win, x_log, y_conv):
            return True
        try:
            win._dispatch_mouse_motion(x_log, y_conv)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_motion_dispatch_exc", "Mouse motion dispatch raised")

    @window.event
    def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
        x_log, y_conv = _to_logical(x, y)
        buttons_n = _normalize_mouse_buttons(buttons)
        modifier_keys = _normalize_modifiers(modifiers)
        # Dev-only: a drag mid-designation is the human sweeping out a region.
        # Routed to the same hook as a plain move, which tells the two apart by
        # whether a press is outstanding (#591).
        if _inspect_consumed(win, "on_mouse_motion", win, x_log, y_conv, modifier_keys):
            return True
        try:
            win._dispatch_mouse_motion(x_log, y_conv, buttons=buttons_n, modifier_keys=modifier_keys)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_drag_dispatch_exc", "Mouse drag dispatch raised")

    @window.event
    def on_mouse_scroll(x, y, scroll_x, scroll_y):
        x_log, y_conv = _to_logical(x, y)
        scroll_x_n, scroll_y_n = _normalize_scroll_delta(scroll_x, scroll_y)
        handler = None
        try:
            handler = win._dispatch_mouse_scroll(x_log, y_conv, scroll_x_n, scroll_y_n)
        except Exception:
            exception_once(logger, "pyglet_on_mouse_scroll_dispatch_exc", "Mouse scroll dispatch raised")
        # Dev-only: record the human's scroll for the interaction journal (#498).
        # The recorder takes the *consuming region* the dispatch returned, so a
        # wheel event no region took is dropped -- nothing moved to report.
        recorder = getattr(win, "_interaction_recorder", None)
        if recorder is not None:
            try:
                recorder.on_mouse_scroll(handler, scroll_x_n, scroll_y_n)
            except Exception:
                exception_once(logger, "pyglet_on_mouse_scroll_record_exc", "Interaction record raised")

    @window.event
    def on_file_drop(x, y, paths):
        x_log, y_conv = _to_logical(x, y)
        try:
            win._dispatch_file_drop(x_log, y_conv, paths)
        except Exception:
            exception_once(logger, "pyglet_on_file_drop_dispatch_exc", "File drop dispatch raised")

    @window.event
    def on_key_press(symbol, modifiers):
        key_name, modifier_keys = _normalize_key(symbol, modifiers)

        try:
            win._set_modifier_keys(modifier_keys)
        except Exception:
            exception_once(logger, "pyglet_on_key_press_set_modifier_keys_exc", "Failed to update modifier-key mask")

        # Dev-only: inspect mode owns Ctrl+Shift+C, and every key while it is
        # latched. Checked before the recorder and the escape latch so its own
        # exit key reaches it rather than closing a dialog behind it (#591).
        #
        # Returning ``True`` is load-bearing, not tidiness: pyglet treats a falsy
        # return as "not handled" and runs the next handler in the stack, whose
        # default ESC behaviour closes the window -- exactly what the latch below
        # relies on with its explicit ``return False``. Falling out of here
        # without a value would quit the win on the mode's own exit key.
        if _inspect_consumed(win, "on_key_press", win, key_name, modifier_keys):
            return True

        # Dev-only: record semantic keys (shortcuts / navigation) for the
        # interaction journal (#390). Recorded here -- before the escape latch and
        # dispatch -- so escape is captured too; bare typing is dropped inside the
        # recorder so field content never enters the journal.
        recorder = getattr(win, "_interaction_recorder", None)
        if recorder is not None:
            try:
                recorder.on_key_press(key_name, modifier_keys)
            except Exception:
                exception_once(logger, "pyglet_on_key_press_record_exc", "Interaction record raised")

        nonlocal esc_down
        if str(key_name).strip().lower() == "escape":
            can_handle = False
            probe = getattr(win, "can_handle_back_event", None)
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
                        print(f"[nuiitivet] key_press t={ts:.6f} key={kn} mods={modifier_keys} handled=False")
                # Let pyglet's default ESC handling run (e.g. close window).
                return False

            esc_down = True
            if debug_keys:
                kn = "escape"
                if not debug_keys_filter or kn in debug_keys_filter:
                    ts = time.perf_counter()
                    print(f"[nuiitivet] key_press t={ts:.6f} key={kn} mods={modifier_keys} handled=True")
            # Handle ESC on key release to avoid OS key-repeat glitches and to
            # align with "keyup triggers back" semantics.
            return True

        try:
            handled = bool(win._dispatch_key_press(key_name, modifier_keys))
        except Exception:
            exception_once(logger, "pyglet_on_key_press_dispatch_exc", "Key press dispatch raised")
            handled = False

        if debug_keys:
            kn = str(key_name).strip().lower()
            if not debug_keys_filter or kn in debug_keys_filter:
                ts = time.perf_counter()
                print(f"[nuiitivet] key_press t={ts:.6f} key={kn} mods={modifier_keys} handled={handled}")

        if handled:
            try:
                win.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_key_press_invalidate_exc", "win.invalidate raised")
            # Tell pyglet the event was handled so default handlers (e.g. ESC-to-exit)
            # do not run.
            return True
        return False

    @window.event
    def on_key_release(symbol, modifiers):
        key_name, modifier_keys = _normalize_key(symbol, modifiers)

        try:
            win._set_modifier_keys(modifier_keys)
        except Exception:
            exception_once(logger, "pyglet_on_key_release_set_modifier_keys_exc", "Failed to update modifier-key mask")

        # Dev-only: inspect mode consumed the press, so its release must not
        # reach the focused widget on its own (#591).
        if _inspect_consumed(win, "on_key_release", win, key_name, modifier_keys):
            return True

        nonlocal esc_down
        if str(key_name).strip().lower() == "escape":
            # Back-navigation fires on the Escape release, gated by the press
            # latch: a release without a matching press (e.g. focus returned
            # mid-tap) must not trigger it.
            if not esc_down:
                return True
            esc_down = False

        try:
            # Escape is routed to handle_back_event inside _dispatch_key_release;
            # every other key is delivered to the focused node as a release. No
            # press is ever synthesized from a release.
            handled = bool(win._dispatch_key_release(key_name, modifier_keys))
        except Exception:
            exception_once(logger, "pyglet_on_key_release_dispatch_exc", "Key release dispatch raised")
            handled = False

        if debug_keys:
            kn = str(key_name).strip().lower()
            if not debug_keys_filter or kn in debug_keys_filter:
                ts = time.perf_counter()
                print(f"[nuiitivet] key_release t={ts:.6f} key={kn} mods={modifier_keys} handled={handled}")

        if handled:
            try:
                win.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_key_release_invalidate_exc", "win.invalidate raised")
            return True
        return False

    @window.event
    def on_text(text):
        try:
            handled = bool(win._dispatch_text(text))
        except Exception:
            exception_once(logger, "pyglet_on_text_dispatch_exc", "Text dispatch raised")
            handled = False
        # Dev-only: record a content-free "typed here" marker (#390). Only the
        # printable/non-control payload counts as typing -- Enter/Tab emit control
        # characters (\r, \t) through on_text on some platforms, which would leave
        # a phantom "text" marker beside every commit. The text itself is never
        # passed to the recorder, so field values never leak; we branch on it only
        # to tell real typing from a control key.
        recorder = getattr(win, "_interaction_recorder", None)
        if recorder is not None and any(ch.isprintable() for ch in text):
            try:
                recorder.on_text()
            except Exception:
                exception_once(logger, "pyglet_on_text_record_exc", "Interaction record raised")
        if handled:
            try:
                win.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_text_invalidate_exc", "win.invalidate raised")

    @window.event
    def on_text_motion(motion):
        motion_code = _normalize_text_motion(motion)
        try:
            handled = bool(win._dispatch_text_motion(motion_code, select=False))
        except Exception:
            exception_once(logger, "pyglet_on_text_motion_dispatch_exc", "Text motion dispatch raised")
            handled = False
        if handled:
            try:
                win.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_text_motion_invalidate_exc", "win.invalidate raised")

    @window.event
    def on_text_motion_select(motion):
        motion_code = _normalize_text_motion(motion)
        try:
            handled = bool(win._dispatch_text_motion(motion_code, select=True))
        except Exception:
            exception_once(logger, "pyglet_on_text_motion_select_dispatch_exc", "Text motion select dispatch raised")
            handled = False
        if handled:
            try:
                win.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_text_motion_select_invalidate_exc", "win.invalidate raised")

    @window.event
    def on_ime_composition(text, start, length):
        try:
            handled = bool(win._dispatch_ime_composition(text, start, length))
        except Exception:
            exception_once(logger, "pyglet_on_ime_composition_dispatch_exc", "IME composition dispatch raised")
            handled = False
        if handled:
            try:
                win.invalidate()
            except Exception:
                exception_once(logger, "pyglet_on_ime_composition_invalidate_exc", "win.invalidate raised")

    @window.event
    def on_close():
        # The OS close button routes through the Window's close_action policy
        # ("close" | "hide"); the App's exit policy decides whether the app
        # exits after an actual close.
        try:
            win._handle_close_request()
        except Exception:
            exception_once(logger, "pyglet_on_close_exc", "Window close request raised")
        return True


def _draw_raster_frame(app: Any, skia: Any) -> bool:
    try:
        img: Any
        render_snapshot = getattr(app, "_render_snapshot", None)
        if callable(render_snapshot):
            scale = max(1.0, float(getattr(app, "_scale", 1.0)))
            snapshot = render_snapshot(scale=scale, for_display=True)

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


def _install_ime_patch(window: object, win: object) -> None:
    """Install the platform IME hook for one OS window.

    ``window`` is the pyglet window, ``win`` the nuiitivet Window model whose
    per-window :class:`~nuiitivet.platform.ime.IMEManager` the hook reads.
    """
    try:
        import sys

        if sys.platform == "darwin":
            from .ime.macos import install_patch

            install_patch(window, win)
        elif sys.platform == "win32":
            from .ime.windows import install_patch

            install_patch(window, win)
        elif sys.platform == "linux":
            from .ime.linux import install_patch

            install_patch(window, win)
    except Exception:
        exception_once(logger, "pyglet_install_ime_patch_exc", "Failed to install IME patch")


def _discard_ime_conversation(window: object) -> None:
    """Drop the OS input method's pending conversation for ``window``.

    Called on OS focus loss, after the model side committed the composition:
    without this, refocusing the window can resume marked text that the
    widget already turned into committed text. No-op on platforms without an
    implementation.
    """
    try:
        import sys

        if sys.platform == "darwin":
            from .ime.macos import discard_conversation

            discard_conversation(window)
        elif sys.platform == "win32":
            from .ime.windows import discard_conversation

            discard_conversation(window)
    except Exception:
        exception_once(logger, "pyglet_discard_ime_conversation_exc", "Failed to discard IME conversation")


def _install_first_mouse_patch(window: object, win: object) -> None:
    """macOS: patch ``acceptsFirstMouse:`` so the activating click is delivered.

    ``window`` is the pyglet window, ``win`` the nuiitivet Window model whose
    ``accepts_first_mouse`` decides the answer. No-op off macOS.
    """
    try:
        if sys.platform == "darwin":
            from .first_mouse_macos import install_patch

            install_patch(window, bool(getattr(win, "accepts_first_mouse", True)))
    except Exception:
        exception_once(
            logger,
            "pyglet_install_first_mouse_patch_exc",
            "Failed to install acceptsFirstMouse patch",
        )


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


def _normalize_modifiers(pyglet_modifiers: int) -> int:
    """Translate a pyglet modifier bitmask into nuiitivet's MOD_* mask."""
    try:
        keymod = pyglet.window.key

        modifier_keys = 0
        if pyglet_modifiers & keymod.MOD_SHIFT:
            modifier_keys |= MOD_SHIFT
        if pyglet_modifiers & keymod.MOD_CTRL:
            modifier_keys |= MOD_CTRL
        if pyglet_modifiers & keymod.MOD_ALT:
            modifier_keys |= MOD_ALT
        # Map Command to META on macOS
        if pyglet_modifiers & getattr(keymod, "MOD_COMMAND", 0):
            modifier_keys |= MOD_META
        return modifier_keys
    except Exception:
        exception_once(logger, "pyglet_normalize_modifiers_exc", "Failed to normalize modifier mapping")
        return 0


def _normalize_mouse_button(pyglet_button: int) -> Optional[int]:
    """Translate a single pyglet mouse button into a backend-neutral ``BUTTON_*``.

    Returns ``None`` for an unrecognized button so the event carries no button
    rather than leaking a raw pyglet value.
    """
    try:
        mouse = pyglet.window.mouse

        if pyglet_button == mouse.LEFT:
            return BUTTON_LEFT
        if pyglet_button == mouse.MIDDLE:
            return BUTTON_MIDDLE
        if pyglet_button == mouse.RIGHT:
            return BUTTON_RIGHT
    except Exception:
        exception_once(logger, "pyglet_normalize_mouse_button_exc", "Failed to normalize mouse button")
    return None


def _normalize_mouse_buttons(pyglet_buttons: int) -> int:
    """Translate a pyglet held-button bit mask into a ``BUTTON_*`` bit mask."""
    try:
        mouse = pyglet.window.mouse

        buttons = 0
        if pyglet_buttons & mouse.LEFT:
            buttons |= BUTTON_LEFT
        if pyglet_buttons & mouse.MIDDLE:
            buttons |= BUTTON_MIDDLE
        if pyglet_buttons & mouse.RIGHT:
            buttons |= BUTTON_RIGHT
        return buttons
    except Exception:
        exception_once(logger, "pyglet_normalize_mouse_buttons_exc", "Failed to normalize mouse buttons")
        return 0


def _normalize_key(symbol: int, pyglet_modifiers: int) -> tuple[str, int]:
    """Translate a pyglet key symbol and modifier mask into nuiitivet's key name and MOD_* mask.

    The modifier mask is resolved independently of the key name so that a failure
    to name the key never silently drops the modifiers, and vice versa.
    """
    modifier_keys = _normalize_modifiers(pyglet_modifiers)

    try:
        keymod = pyglet.window.key

        if symbol == keymod.TAB:
            name = "tab"
        elif symbol == keymod.SPACE:
            name = "space"
        elif symbol in (keymod.ENTER, keymod.RETURN):
            name = "enter"
        else:
            name = keymod.symbol_string(symbol).lower()
    except Exception:
        exception_once(logger, "pyglet_normalize_key_name_exc", "Failed to normalize key name")
        name = ""

    return name, modifier_keys


def _normalize_text_motion(motion: int) -> int:
    """Translate a pyglet text-motion constant into nuiitivet's TEXT_MOTION_* code.

    Motions nuiitivet has no code for (word/page/file moves, and the vertical
    moves the arrow keys emit) pass through unchanged.
    """
    try:
        keymod = pyglet.window.key

        mapping = {
            keymod.MOTION_BACKSPACE: TEXT_MOTION_BACKSPACE,
            keymod.MOTION_DELETE: TEXT_MOTION_DELETE,
            keymod.MOTION_LEFT: TEXT_MOTION_LEFT,
            keymod.MOTION_RIGHT: TEXT_MOTION_RIGHT,
            keymod.MOTION_BEGINNING_OF_LINE: TEXT_MOTION_HOME,
            keymod.MOTION_END_OF_LINE: TEXT_MOTION_END,
        }
        mapped = mapping.get(int(motion))
        if mapped is not None:
            return mapped
    except Exception:
        exception_once(logger, "pyglet_normalize_text_motion_exc", "Failed to normalize text motion")
    return int(motion)
