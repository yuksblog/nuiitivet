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
    canvas.clear(bg_color)

    if app.root:
        content_height = max(0, app.height)

        layout_fn = getattr(app.root, "layout", None)
        clear_needs_layout_fn = getattr(app.root, "clear_needs_layout", None)
        if callable(layout_fn):
            needs_layout = getattr(app.root, "needs_layout", True)
            last_size = getattr(app, "_last_layout_size", None)
            current_size = (app.width, content_height)
            if needs_layout or last_size != current_size:
                layout_fn(app.width, content_height)
                app._last_layout_size = current_size
                if callable(clear_needs_layout_fn):
                    clear_needs_layout_fn()
        app.root.paint(canvas, 0, 0, app.width, content_height)

    try:
        gr_context.flush()
    except Exception:
        try:
            gr_context.submit()
        except Exception:
            exception_once(logger, "gpu_frame_submit_exc", "gr_context.submit raised")

    app._dirty = False
    return True
