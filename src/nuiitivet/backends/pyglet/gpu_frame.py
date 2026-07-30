"""GPU frame rendering for the pyglet backend."""

from __future__ import annotations

import logging
from typing import Any

from nuiitivet.common.logging_once import debug_once, exception_once

logger = logging.getLogger(__name__)


def draw_gpu_frame(app: Any, gr_context: Any, GL: Any, skia: Any) -> bool:
    """Render a frame directly into the active OpenGL framebuffer via Skia GPU."""

    _reset_gr_context(gr_context)

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

    # Fast path: the widget tree is unchanged and only a surface-loss redraw
    # (window show/activate) requested this frame. Re-blit the cached full frame
    # 1:1 in device pixels instead of walking the whole tree. This fills the
    # entire back buffer, so the flip invariant (never flip a buffer you did not
    # just draw) is preserved -- see docs/design/RENDERING_PIPELINE.md.
    if _try_reblit_cached_frame(app, canvas, phys_w, phys_h, skia):
        _flush_gpu(app, gr_context)
        app._dirty = False
        return True

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

    _paint_dev_action_overlay(app, canvas)

    # Cache this fully-painted frame so a later surface-loss redraw can re-blit it
    # instead of walking the tree again. The snapshot captures the surface at its
    # physical (device-pixel) resolution regardless of the canvas scale transform.
    _store_frame_cache(app, surf, phys_w, phys_h)
    app._paint_dirty = False

    _flush_gpu(app, gr_context)
    app._dirty = False
    return True


def _paint_dev_action_overlay(app: Any, canvas: Any) -> None:
    """Paint the human-only dev action overlay onto the live frame.

    Only the on-screen frame paths call this; the off-screen ``screenshot``
    render deliberately does not, so markers never enter the assistant's
    perception. A no-op (import guarded) when the dev overlay is unavailable.
    """
    try:
        from nuiitivet.dev import action_overlay

        action_overlay.paint_markers(app, canvas, int(app.width), int(app.height))
    except Exception:
        exception_once(logger, "gpu_frame_dev_action_overlay_exc", "dev action overlay paint raised")


def _store_frame_cache(app: Any, surf: Any, phys_w: int, phys_h: int) -> None:
    """Snapshot the just-painted surface into the app's full-frame GPU cache."""

    try:
        snapshot = surf.makeImageSnapshot()
    except Exception:
        exception_once(logger, "gpu_frame_snapshot_exc", "surf.makeImageSnapshot raised")
        snapshot = None
    app._gpu_frame_cache = snapshot
    app._gpu_frame_cache_size = (phys_w, phys_h) if snapshot is not None else None


def _try_reblit_cached_frame(app: Any, canvas: Any, phys_w: int, phys_h: int, skia: Any) -> bool:
    """Re-blit the cached full frame 1:1 when the tree is unchanged.

    Returns True when the cached frame was drawn (caller should flip); False when
    no valid cache exists and a full paint is required.
    """

    if getattr(app, "_paint_dirty", True):
        return False
    cache = getattr(app, "_gpu_frame_cache", None)
    if cache is None:
        return False
    if getattr(app, "_gpu_frame_cache_size", None) != (phys_w, phys_h):
        return False
    try:
        # Clear to transparent then blit at device resolution with the identity
        # matrix so 1 canvas unit == 1 device pixel. Any transparency baked into
        # the snapshot (e.g. CustomChrome rounded corners) is reproduced exactly.
        canvas.clear(skia.Color(0, 0, 0, 0))
        canvas.drawImage(cache, 0.0, 0.0)
        return True
    except Exception:
        exception_once(logger, "gpu_frame_reblit_exc", "Failed to re-blit cached GPU frame")
        return False


def _reset_gr_context(gr_context: Any) -> None:
    """Tell Skia its cached GL state is stale before drawing the frame.

    ``GrDirectContext`` caches GL state, but ``on_draw`` and pyglet's ``on_resize``
    rewrite the viewport behind its back -- hence the garbled frame after a
    drag-resize (#467). A full reset (not just ``resetGLTextureBindings()``, which
    leaves the cached viewport wrong) costs one state resend per frame.
    """

    reset = getattr(gr_context, "resetContext", None)
    if not callable(reset):
        debug_once(logger, "gpu_frame_no_reset_context", "gr_context has no resetContext (skipping GL state reset)")
        return
    try:
        reset()
    except Exception:
        exception_once(logger, "gpu_frame_reset_context_exc", "gr_context.resetContext raised")


def _flush_gpu(app: Any, gr_context: Any) -> None:
    try:
        gr_context.flush()
    except Exception:
        try:
            gr_context.submit()
        except Exception:
            exception_once(logger, "gpu_frame_submit_exc", "gr_context.submit raised")
