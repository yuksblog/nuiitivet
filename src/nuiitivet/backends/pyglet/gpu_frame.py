"""GPU frame rendering for the pyglet backend."""

from __future__ import annotations

import logging
from typing import Any

from nuiitivet.common.logging_once import debug_once, exception_once

logger = logging.getLogger(__name__)


def draw_gpu_frame(app: Any, gr_context: Any, GL: Any, skia: Any) -> bool:
    """Render a frame directly into the active OpenGL framebuffer via Skia GPU."""

    try:
        fbo = int(GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING))
    except Exception:
        debug_once(logger, "gpu_frame_gl_fbo_exc", "Failed to query GL_FRAMEBUFFER_BINDING (assuming 0)")
        fbo = 0

    try:
        samples = int(GL.glGetIntegerv(GL.GL_SAMPLES))
    except Exception:
        debug_once(logger, "gpu_frame_gl_samples_exc", "Failed to query GL_SAMPLES (assuming 0)")
        samples = 0

    try:
        stencil = int(GL.glGetIntegerv(GL.GL_STENCIL_BITS))
    except Exception:
        debug_once(logger, "gpu_frame_gl_stencil_exc", "Failed to query GL_STENCIL_BITS (assuming 0)")
        stencil = 0

    phys_w = max(1, int(app.width * getattr(app, "_scale", 1.0)))
    phys_h = max(1, int(app.height * getattr(app, "_scale", 1.0)))

    try:
        fb_info = skia.GrGLFramebufferInfo(fbo, GL.GL_RGBA8)
    except Exception:
        fb_info = skia.GrGLFramebufferInfo(0, GL.GL_RGBA8 if hasattr(GL, "GL_RGBA8") else 0)

    backend = skia.GrBackendRenderTarget(phys_w, phys_h, samples, stencil, fb_info)

    surf = skia.Surface.MakeFromBackendRenderTarget(
        gr_context,
        backend,
        skia.kBottomLeft_GrSurfaceOrigin,
        skia.kRGBA_8888_ColorType,
        None,
    )

    if not surf:
        return False

    canvas = surf.getCanvas()
    if getattr(app, "_scale", 1.0) != 1.0:
        canvas.scale(getattr(app, "_scale", 1.0), getattr(app, "_scale", 1.0))

    bg_color = getattr(skia, "ColorWHITE", 0)
    clear_fn = getattr(app, "_background_clear_color", None)
    if callable(clear_fn):
        try:
            bg_color = clear_fn()
        except Exception:
            exception_once(logger, "gpu_frame_clear_color_exc", "_background_clear_color raised")
            bg_color = getattr(skia, "ColorWHITE", 0)
    if isinstance(bg_color, (list, tuple)) and len(bg_color) == 4:
        try:
            from nuiitivet.rendering.skia.color import rgba_to_skia_color

            bg_tuple = tuple(int(x) for x in bg_color)
            if len(bg_tuple) == 4:
                bg_color = rgba_to_skia_color((bg_tuple[0], bg_tuple[1], bg_tuple[2], bg_tuple[3]))
        except Exception:
            exception_once(logger, "gpu_frame_clear_color_convert_exc", "Failed to convert clear color")
            bg_color = getattr(skia, "ColorWHITE", 0)
    # Detect CustomChrome properties needed for rendering
    chrome = getattr(app, "chrome", None)
    chrome_corner_radius = 0.0
    chrome_border = None
    if chrome is not None and type(chrome).__name__ == "CustomChrome":
        chrome_corner_radius = float(getattr(chrome, "corner_radius", 0.0))
        chrome_border = getattr(chrome, "border", None)

    if chrome_corner_radius > 0:
        # Clear to transparent so pixels outside the rounded rect are invisible
        canvas.clear(skia.Color(0, 0, 0, 0))
    else:
        canvas.clear(bg_color)

    if app.root:
        content_height = max(0, app.height)
        w = app.width

        layout_fn = getattr(app.root, "layout", None)
        clear_needs_layout_fn = getattr(app.root, "clear_needs_layout", None)
        if callable(layout_fn):
            needs_layout = getattr(app.root, "needs_layout", True)
            last_size = getattr(app, "_last_layout_size", None)
            current_size = (w, content_height)
            if needs_layout or last_size != current_size:
                layout_fn(w, content_height)
                app._last_layout_size = current_size
                if callable(clear_needs_layout_fn):
                    clear_needs_layout_fn()

        if chrome_corner_radius > 0:
            rrect = skia.RRect.MakeRectXY(
                skia.Rect.MakeWH(float(w), float(content_height)),
                chrome_corner_radius,
                chrome_corner_radius,
            )
            canvas.save()
            canvas.clipRRect(rrect, doAntiAlias=True)
            bg_fill = skia.Paint(AntiAlias=True)
            bg_fill.setColor(bg_color)
            canvas.drawRRect(rrect, bg_fill)

        app.root.paint(canvas, 0, 0, w, content_height)

        if chrome_corner_radius > 0:
            canvas.restore()

        if chrome_border is not None:
            try:
                from nuiitivet.theme.resolver import resolve_color_to_rgba
                from nuiitivet.rendering.skia.color import rgba_to_skia_color

                theme = getattr(getattr(app, "_theme_manager", None), "current", None)
                border_rgba = resolve_color_to_rgba(chrome_border.color, theme=theme)
                raw = tuple(int(x) for x in border_rgba)
                border_color = rgba_to_skia_color((raw[0], raw[1], raw[2], raw[3]))
                border_width = float(chrome_border.width)
                border_paint = skia.Paint(AntiAlias=True)
                border_paint.setStyle(skia.Paint.kStroke_Style)
                border_paint.setStrokeWidth(border_width)
                border_paint.setColor(border_color)
                half = border_width / 2.0
                inset = skia.Rect.MakeXYWH(
                    half,
                    half,
                    float(w) - border_width,
                    float(content_height) - border_width,
                )
                r = max(0.0, chrome_corner_radius - half)
                if r > 0:
                    canvas.drawRRect(skia.RRect.MakeRectXY(inset, r, r), border_paint)
                else:
                    canvas.drawRect(inset, border_paint)
            except Exception:
                exception_once(logger, "gpu_frame_chrome_border_exc", "Failed to draw CustomChrome border")

    try:
        gr_context.flush()
    except Exception:
        try:
            gr_context.submit()
        except Exception:
            exception_once(logger, "gpu_frame_submit_exc", "gr_context.submit raised")

    app._dirty = False
    return True
