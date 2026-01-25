from .skia import (
    make_blur_image_filter,
    make_blur_mask_filter,
    make_paint,
    make_path,
    make_rect,
    path_add_rrect,
    resolve_rrect,
    set_paint_image_filter,
    set_paint_mask_filter,
)
from .skia.geometry import draw_round_rect
from nuiitivet.common.logging_once import exception_once
import logging

logger = logging.getLogger(__name__)


class BackgroundRenderer:
    """Encapsulate background/shadow/border drawing and corner-radius logic.

    This class delegates to the owner (typically a Container-like widget) for
    configuration values but centralizes all skia-specific drawing and
    compatibility fallbacks.
    """

    def __init__(self, owner) -> None:
        self.owner = owner

    def corner_radius_pixels(self, width: int, height: int) -> float:
        # Backwards-compatible scalar radius: return the maximum of per-corner radii
        try:
            radii = self.corner_radii_pixels(width, height)
            if not radii:
                return 0.0
            return float(max(radii))
        except Exception:
            exception_once(logger, "background_renderer_corner_radius_pixels_exc", "corner_radius_pixels failed")
            # fallback to legacy single value
            cr = getattr(self.owner, "corner_radius", 0)
            if cr is None:
                return 0.0
            try:
                return float(cr)
            except Exception:
                exception_once(
                    logger,
                    "background_renderer_corner_radius_float_exc",
                    "Failed to coerce owner.corner_radius to float",
                )
                return 0.0

    def corner_radii_pixels(self, width: int, height: int):
        """Return per-corner radii in pixels as a 4-tuple (tl, tr, br, bl).

        Accepts owner's `corner_radii` (4-tuple of floats) or `corner_radius` scalar.
        Values <= 1.0 are treated as proportions of min(width,height)/2.
        """
        cr_owner = getattr(self.owner, "corner_radii", None)
        if cr_owner is None:
            # fallback to scalar corner_radius
            cr_owner = getattr(self.owner, "corner_radius", 0.0)

        try:
            if isinstance(cr_owner, (list, tuple)):
                if len(cr_owner) != 4:
                    return (0.0, 0.0, 0.0, 0.0)
                out = []
                for v in cr_owner:
                    try:
                        fv = float(v or 0.0)
                    except Exception:
                        exception_once(
                            logger,
                            "background_renderer_corner_radii_value_float_exc",
                            "Failed to coerce corner_radii value to float (type=%s)",
                            type(v).__name__,
                        )
                        fv = 0.0
                    if fv <= 0.0:
                        out.append(0.0)
                    elif fv < 1.0:
                        out.append(float(fv) * (min(width, height) / 2.0))
                    else:
                        # values >= 1.0 are treated as absolute pixels but capped
                        # to half of the min size to avoid oversized radii
                        cap = float(min(width, height) / 2.0)
                        out.append(float(min(fv, cap)))
                return (out[0], out[1], out[2], out[3])
            else:
                # preserve legacy behavior:
                # - integer values (type int) are absolute pixels
                # - float values are proportions (values >=1.0 cap to 1.0)
                # - other coercible values (e.g. strings) that coerce to an integer-like float
                #   are treated as absolute pixels; otherwise treated like floats
                if isinstance(cr_owner, int):
                    v = float(cr_owner)
                    return (v, v, v, v)
                if isinstance(cr_owner, float):
                    if cr_owner <= 0.0:
                        return (0.0, 0.0, 0.0, 0.0)
                    prop = cr_owner if cr_owner < 1.0 else 1.0
                    px = float(prop) * (min(width, height) / 2.0)
                    return (px, px, px, px)
                try:
                    f = float(cr_owner or 0.0)
                except Exception:
                    exception_once(
                        logger,
                        "background_renderer_corner_radii_float_exc",
                        "Failed to coerce corner radius",
                    )
                    return (0.0, 0.0, 0.0, 0.0)
                if f <= 0.0:
                    return (0.0, 0.0, 0.0, 0.0)
                # coercible numeric that is integer-like -> treat as absolute pixels
                try:
                    if float(f).is_integer():
                        v = float(int(f))
                        return (v, v, v, v)
                except Exception:
                    exception_once(
                        logger,
                        "background_renderer_corner_radius_is_integer_exc",
                        "Failed to normalize corner radius",
                    )
                # otherwise treat as float proportion
                prop = f if f < 1.0 else 1.0
                px = float(prop) * (min(width, height) / 2.0)
                return (px, px, px, px)
        except Exception:
            exception_once(logger, "background_renderer_corner_radii_pixels_exc", "corner_radii_pixels failed")
            return (0.0, 0.0, 0.0, 0.0)

    def _draw_shadow(self, canvas, x, y, width, height, sc, dx, dy, sb, eff_rad):
        if canvas is None:
            return

        sx = x + int(dx)
        sy = y + int(dy)

        # prefer saveLayer + ImageFilter when blur requested
        if sb and sb > 0.0:
            try:
                imgf = make_blur_image_filter(float(sb))
                if imgf is None:
                    return
                layer_paint = make_paint(style="fill", aa=True)
                if layer_paint is None:
                    return
                set_paint_image_filter(layer_paint, imgf)

                pad = int(max(4, sb * 3))
                lb = make_rect(sx - pad, sy - pad, width + pad * 2, height + pad * 2)
                if lb is None or not hasattr(canvas, "saveLayer"):
                    return
                canvas.saveLayer(lb, layer_paint)
                try:
                    # sc is an RGBA primitive resolved earlier
                    sp = make_paint(color=sc, style="fill", aa=True)
                    if sp is None:
                        return
                    has_rad = (isinstance(eff_rad, (list, tuple)) and any(float(r or 0.0) > 0.0 for r in eff_rad)) or (
                        not isinstance(eff_rad, (list, tuple)) and eff_rad and float(eff_rad) > 0.0
                    )
                    _r = make_rect(sx, sy, width, height)
                    if _r is None:
                        return
                    if has_rad:
                        srr = resolve_rrect(_r, eff_rad)
                        if srr is not None:
                            canvas.drawRRect(srr, sp)
                        else:
                            canvas.drawRect(_r, sp)
                    else:
                        canvas.drawRect(_r, sp)
                finally:
                    try:
                        canvas.restore()
                    except Exception:
                        exception_once(
                            logger,
                            "background_renderer_canvas_restore_exc",
                            "Failed to restore canvas after shadow saveLayer",
                        )
            except Exception:
                exception_once(
                    logger,
                    "background_renderer_shadow_imagefilter_exc",
                    "Failed to draw shadow using image filter; falling back",
                )
                # fallback: mask-filter blur
                try:
                    shadow_paint = make_paint(color=sc, style="fill", aa=True)
                    if shadow_paint is None:
                        return
                    mf = make_blur_mask_filter(float(sb))
                    if mf is None:
                        return
                    set_paint_mask_filter(shadow_paint, mf)

                    try:
                        _r = make_rect(sx, sy, width, height)
                        if _r is None:
                            return
                        srr = resolve_rrect(_r, eff_rad)
                        if srr is not None:
                            canvas.drawRRect(srr, shadow_paint)
                        else:
                            canvas.drawRect(_r, shadow_paint)
                    except Exception:
                        exception_once(
                            logger,
                            "background_renderer_shadow_maskfilter_draw_exc",
                            "Failed to draw shadow using mask filter",
                        )
                except Exception:
                    exception_once(
                        logger,
                        "background_renderer_shadow_maskfilter_exc",
                        "Failed to prepare shadow mask filter",
                    )
        else:
            try:
                shadow_paint = make_paint(color=sc, style="fill", aa=True)
                if shadow_paint is None:
                    return
                try:
                    _r = make_rect(sx, sy, width, height)
                    if _r is None:
                        return
                    srr = resolve_rrect(_r, eff_rad)
                    if srr is not None:
                        canvas.drawRRect(srr, shadow_paint)
                    else:
                        canvas.drawRect(_r, shadow_paint)
                except Exception:
                    exception_once(
                        logger,
                        "background_renderer_shadow_simple_draw_exc",
                        "Failed to draw shadow",
                    )
            except Exception:
                exception_once(
                    logger,
                    "background_renderer_shadow_simple_exc",
                    "Failed to prepare shadow paint",
                )

    def _draw_background(self, canvas, x, y, width, height, paint, eff_rad):
        rect = make_rect(x, y, width, height)
        if rect is None:
            return
        draw_round_rect(canvas, rect, eff_rad, paint)

    def _draw_border(self, canvas, x, y, width, height, bw, eff_rad):
        if canvas is None:
            return

        from nuiitivet.theme.resolver import resolve_color_to_rgba
        from nuiitivet.theme.manager import manager as theme_manager

        try:
            stroke_rgba = resolve_color_to_rgba(self.owner.border_color, theme=theme_manager.current)
            stroke_paint = make_paint(color=stroke_rgba, style="stroke", stroke_width=bw, aa=True)
            if stroke_paint is None:
                return

            try:
                if eff_rad and (isinstance(eff_rad, (list, tuple)) or eff_rad > 0.0):
                    rr_x = x + bw / 2.0
                    rr_y = y + bw / 2.0
                    rr_w = width - bw
                    rr_h = height - bw
                    try:
                        rect = make_rect(rr_x, rr_y, rr_w, rr_h)
                        if rect is None:
                            return
                        if isinstance(eff_rad, (list, tuple)):
                            adjusted = []
                            all_equal = True
                            first_r = None
                            for r in eff_rad:
                                rv = float(max(0.0, r - bw / 2.0))
                                if first_r is None:
                                    first_r = rv
                                elif abs(rv - first_r) > 0.001:
                                    all_equal = False
                                adjusted.append(rv)

                            if all_equal and first_r is not None:
                                rrect = resolve_rrect(rect, (first_r, first_r, first_r, first_r))
                            else:
                                rrect = resolve_rrect(rect, adjusted)
                            if rrect is None and first_r is not None:
                                rrect = resolve_rrect(rect, first_r)
                        else:
                            rr_rad = max(0.0, float(eff_rad - bw / 2.0))
                            rrect = resolve_rrect(rect, rr_rad)

                        if rrect is not None:
                            path = make_path()
                            if path is not None and path_add_rrect(path, rrect):
                                canvas.drawPath(path, stroke_paint)
                            else:
                                canvas.drawRRect(rrect, stroke_paint)
                        else:
                            canvas.drawRect(rect, stroke_paint)
                    except Exception:
                        try:
                            if isinstance(eff_rad, (list, tuple)):
                                fallback_radius = float(max(eff_rad))
                            else:
                                fallback_radius = float(eff_rad)
                        except Exception:
                            exception_once(
                                logger,
                                "background_renderer_fallback_radius_float_exc",
                                "Failed to compute fallback border radius",
                            )
                            fallback_radius = 0.0
                        rect = make_rect(rr_x, rr_y, rr_w, rr_h)
                        if rect is None:
                            return
                        rr = resolve_rrect(rect, fallback_radius)
                        if rr is not None:
                            canvas.drawRRect(rr, stroke_paint)
                        else:
                            canvas.drawRect(rect, stroke_paint)
                else:
                    br = make_rect(x + bw / 2.0, y + bw / 2.0, width - bw, height - bw)
                    if br is not None:
                        canvas.drawRect(br, stroke_paint)
            except Exception:
                exception_once(
                    logger,
                    "background_renderer_draw_border_inner_exc",
                    "Failed to draw border",
                )
        except Exception as e:
            exception_once(
                logger,
                "background_renderer_draw_border_outer_exc",
                "Error in _draw_border outer: %s",
                e,
            )

    def paint_shadow_and_background(self, canvas, x, y, width, height):
        """Draw shadow and background (but not border)."""
        # draw shadow first if requested
        from nuiitivet.theme.resolver import resolve_color_to_rgba
        from nuiitivet.theme.manager import manager as theme_manager

        try:
            sc = resolve_color_to_rgba(self.owner.shadow_color, theme=theme_manager.current)
            dx, dy = getattr(self.owner, "shadow_offset", (0, 0))
            sb = float(getattr(self.owner, "shadow_blur", 0.0) or 0.0)
            if sc is not None and (dx != 0 or dy != 0 or sb > 0.0):
                radii = self.corner_radii_pixels(width, height)
                self._draw_shadow(canvas, x, y, width, height, sc, dx, dy, sb, radii)
        except Exception:
            exception_once(
                logger,
                "background_renderer_paint_shadow_exc",
                "Failed to paint shadow",
            )

        # draw background if present
        if self.owner.bgcolor is not None:
            try:
                bg_rgba = resolve_color_to_rgba(self.owner.bgcolor, theme=theme_manager.current)
                paint = make_paint(color=bg_rgba, style="fill", aa=True)

                if paint is not None:
                    # log when background resolves to fully transparent
                    if isinstance(bg_rgba, (list, tuple)) and len(bg_rgba) > 3 and bg_rgba[3] == 0:
                        logger.debug("background resolved to transparent RGBA=%r", bg_rgba)

                    radii = self.corner_radii_pixels(width, height)
                    self._draw_background(canvas, x, y, width, height, paint, radii)
            except Exception:
                exception_once(
                    logger,
                    "background_renderer_paint_background_exc",
                    "Failed to draw background",
                )

    def paint_border(self, canvas, x, y, width, height):
        """Draw border only."""
        try:
            if getattr(self.owner, "border_width", 0) and getattr(self.owner, "border_color", None) is not None:
                radii = self.corner_radii_pixels(width, height)
                self._draw_border(canvas, x, y, width, height, int(getattr(self.owner, "border_width", 0)), radii)
        except Exception:
            exception_once(
                logger,
                "background_renderer_paint_border_exc",
                "Failed to paint border",
            )

    def paint_background(self, canvas, x, y, width, height):
        """High-level helper: draw shadow/background/border using owner's config.

        This mirrors the previous sequence from Container.paint where the
        shadow/background/border were drawn in order.
        """
        self.paint_shadow_and_background(canvas, x, y, width, height)
        self.paint_border(canvas, x, y, width, height)
