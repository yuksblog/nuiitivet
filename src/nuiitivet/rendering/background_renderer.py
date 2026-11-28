from .skia import (
    make_blur_mask_filter,
    make_paint,
    make_path,
    make_rect,
    path_add_rrect,
    resolve_rrect,
    set_paint_mask_filter,
)
from .skia.geometry import draw_round_rect
from .shadow import NO_SHADOWS
from nuiitivet.common.back_reference import back_reference
from nuiitivet.common.logging_once import exception_once
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.theme import Theme
import logging
from typing import Any, Optional, Tuple

Radii = Tuple[float, float, float, float]

logger = logging.getLogger(__name__)


class BackgroundRenderer:
    """Encapsulate background/shadow/border drawing and corner-radius logic.

    This class delegates to the owner (typically a Container-like widget) for
    configuration values but centralizes all skia-specific drawing and
    compatibility fallbacks.
    """

    def __init__(self, owner) -> None:
        self._owner_ref = back_reference(owner)
        # Each visit asks for the same answers until a size or a property changes.
        self._radii_key: Any = None
        self._radii: Radii = (0.0, 0.0, 0.0, 0.0)
        self._stroke_key: Any = None
        self._stroke_paint: Any = None
        self._border_key: Any = None
        self._border_draw: Optional[Tuple[str, Any]] = None
        self._clip_key: Any = None
        self._clip_shape: Optional[Tuple[str, Any]] = None

    @property
    def owner(self) -> Any:
        """The widget drawn, while it lives."""
        return self._owner_ref()

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

    def corner_radii_pixels(self, width: int, height: int) -> Radii:
        """Return per-corner radii in pixels as a 4-tuple (tl, tr, br, bl).

        Accepts owner's `corner_radii` (4-tuple of floats) or `corner_radius` scalar.
        Values <= 1.0 are treated as proportions of min(width,height)/2.
        """
        owner = self.owner
        cr_owner = getattr(owner, "corner_radii", None)
        if cr_owner is None:
            # fallback to scalar corner_radius
            cr_owner = getattr(owner, "corner_radius", 0.0)
        if isinstance(cr_owner, list):
            cr_owner = tuple(cr_owner)
        # The type is part of the key: an int radius is pixels, an equal float a proportion.
        key = (cr_owner, type(cr_owner), width, height)
        if key != self._radii_key:
            self._radii = self._resolve_corner_radii(cr_owner, width, height)
            self._radii_key = key
        return self._radii

    @staticmethod
    def _resolve_corner_radii(cr_owner: Any, width: int, height: int) -> Radii:
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

    @staticmethod
    def _inflate_radii(eff_rad, spread):
        """Grow corner radii by *spread*, matching the inflated shadow rect."""
        try:
            if isinstance(eff_rad, (list, tuple)):
                return tuple(max(0.0, float(r or 0.0) + spread) for r in eff_rad)
            return max(0.0, float(eff_rad or 0.0) + spread)
        except Exception:
            exception_once(
                logger,
                "background_renderer_inflate_radii_exc",
                "Failed to inflate corner radii by spread",
            )
            return eff_rad

    @staticmethod
    def _has_radius(eff_rad) -> bool:
        try:
            if isinstance(eff_rad, (list, tuple)):
                return any(float(r or 0.0) > 0.0 for r in eff_rad)
            return bool(eff_rad) and float(eff_rad) > 0.0
        except Exception:
            exception_once(
                logger,
                "background_renderer_has_radius_exc",
                "Failed to inspect corner radii",
            )
            return False

    def _draw_shadow_rect(self, canvas, sx, sy, width, height, paint, eff_rad) -> None:
        """Fill one shadow rect with *paint*, rounding it when radii ask for it."""
        _r = make_rect(sx, sy, width, height)
        if _r is None:
            return
        if self._has_radius(eff_rad):
            srr = resolve_rrect(_r, eff_rad)
            if srr is not None:
                canvas.drawRRect(srr, paint)
                return
        canvas.drawRect(_r, paint)

    def _draw_shadow(self, canvas, x, y, width, height, sc, dx, dy, blur_radius, eff_rad, spread_radius=0.0):
        """Draw one shadow layer.

        *spread_radius* inflates the shadow rect outward on every side before
        the blur is applied, growing the corner radii to match. It is what
        lets a low-elevation shadow show past the opaque body drawn on top of
        it.
        """
        if canvas is None:
            return

        try:
            spread = float(spread_radius or 0.0)
        except Exception:
            exception_once(logger, "background_renderer_shadow_spread_exc", "Failed to coerce shadow spread")
            spread = 0.0

        sx = x + int(dx) - spread
        sy = y + int(dy) - spread
        width = width + spread * 2.0
        height = height + spread * 2.0
        if width <= 0.0 or height <= 0.0:
            return
        eff_rad = self._inflate_radii(eff_rad, spread)

        try:
            shadow_paint = make_paint(color=sc, style="fill", aa=True)
            if shadow_paint is None:
                return
            if blur_radius and blur_radius > 0.0:
                # Skia blurs a round rect's mask analytically, so a MaskFilter
                # needs no offscreen layer -- which is the whole cost of the
                # alternative, and it grows with the square of the sigma.
                # A CSS blur-radius is twice the Gaussian sigma Skia takes.
                mf = make_blur_mask_filter(float(blur_radius) / 2.0)
                if mf is None:
                    return
                set_paint_mask_filter(shadow_paint, mf)
            self._draw_shadow_rect(canvas, sx, sy, width, height, shadow_paint, eff_rad)
        except Exception:
            exception_once(
                logger,
                "background_renderer_shadow_draw_exc",
                "Failed to draw shadow",
            )

    def _draw_background(self, canvas, x, y, width, height, paint, eff_rad):
        rect = make_rect(x, y, width, height)
        if rect is None:
            return
        draw_round_rect(canvas, rect, eff_rad, paint)

    def _draw_border(self, canvas, x, y, width, height, bw, eff_rad):
        if canvas is None:
            return
        try:
            stroke_rgba = resolve_color_to_rgba(self.owner.border_color, theme=Theme.of(self.owner))
            stroke_key = (stroke_rgba, bw)
            if stroke_key != self._stroke_key:
                self._stroke_paint = make_paint(color=stroke_rgba, style="stroke", stroke_width=bw, aa=True)
                self._stroke_key = stroke_key
            stroke_paint = self._stroke_paint
            if stroke_paint is None:
                return
        except Exception:
            exception_once(logger, "background_renderer_border_paint_exc", "Failed to resolve the border paint")
            return
        half = bw / 2.0
        try:
            border_key = (x, y, width, height, bw, eff_rad)
            if border_key != self._border_key:
                self._border_draw = self._border_shape(x, y, width, height, bw, eff_rad)
                self._border_key = border_key
            drawn = self._border_draw
            if drawn is None:
                return
            kind, shape = drawn
            if kind == "path":
                canvas.drawPath(shape, stroke_paint)
            elif kind == "rrect":
                canvas.drawRRect(shape, stroke_paint)
            else:
                canvas.drawRect(shape, stroke_paint)
        except Exception:
            exception_once(logger, "background_renderer_draw_border_exc", "Failed to draw the rounded border")
            self._border_key = None
            # A square border still shows where the box ends.
            rect = make_rect(x + half, y + half, width - bw, height - bw)
            if rect is not None:
                try:
                    canvas.drawRect(rect, stroke_paint)
                except Exception:
                    exception_once(logger, "background_renderer_draw_border_rect_exc", "Failed to draw border")

    @staticmethod
    def _border_shape(x, y, width, height, bw, eff_rad) -> Optional[Tuple[str, Any]]:
        """The stroke's centre line, inset by half the stroke so it stays inside the rect."""
        half = bw / 2.0
        rect = make_rect(x + half, y + half, width - bw, height - bw)
        if rect is None:
            return None
        if not isinstance(eff_rad, (list, tuple)):
            eff_rad = (eff_rad, eff_rad, eff_rad, eff_rad)
        adjusted = [float(max(0.0, r - half)) for r in eff_rad]
        if not adjusted:
            return ("rect", rect)
        first_r = adjusted[0]
        if all(abs(r - first_r) <= 0.001 for r in adjusted):
            rrect = resolve_rrect(rect, (first_r, first_r, first_r, first_r))
        else:
            rrect = resolve_rrect(rect, adjusted)
        if rrect is None:
            rrect = resolve_rrect(rect, first_r)
        if rrect is None:
            return ("rect", rect)
        path = make_path()
        if path is not None and path_add_rrect(path, rrect):
            return ("path", path)
        return ("rrect", rrect)

    def paint_shadow_and_background(self, canvas, x, y, width, height):
        """Draw shadow and background (but not border).

        ``owner.shadows``, when present, must already be a normalized
        ``Shadows`` tuple — ``Box.shadows``'s setter guarantees it.
        """
        # draw shadow first if requested
        try:
            layers = getattr(self.owner, "shadows", NO_SHADOWS)
            if layers:
                theme = Theme.of(self.owner)
                radii = self.corner_radii_pixels(width, height)
                # Back to front: the first layer is drawn first and sits underneath.
                for layer in layers:
                    sc = resolve_color_to_rgba(layer.color, theme=theme)
                    # An unresolvable color comes back transparent, and a blur
                    # pass over it costs a saveLayer to paint nothing.
                    if sc is None or (len(sc) > 3 and sc[3] == 0):
                        continue
                    dx, dy = layer.offset
                    self._draw_shadow(
                        canvas, x, y, width, height, sc, dx, dy, layer.blur_radius, radii, layer.spread_radius
                    )
        except Exception:
            exception_once(
                logger,
                "background_renderer_paint_shadow_exc",
                "Failed to paint shadow",
            )

        # draw background if present
        if self.owner.bgcolor is not None:
            try:
                bg_rgba = resolve_color_to_rgba(self.owner.bgcolor, theme=Theme.of(self.owner))
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
            owner = self.owner
            border_width = getattr(owner, "border_width", 0)
            if border_width and getattr(owner, "border_color", None) is not None:
                radii = self.corner_radii_pixels(width, height)
                self._draw_border(canvas, x, y, width, height, int(border_width), radii)
        except Exception:
            exception_once(
                logger,
                "background_renderer_paint_border_exc",
                "Failed to paint border",
            )

    def clip_to_shape(self, canvas, x, y, width, height, radii: Radii) -> bool:
        """Clip ``canvas`` to a rounded rect, anti-aliased.

        Args:
            canvas: The canvas to clip.
            x: Left edge of the rect.
            y: Top edge of the rect.
            width: Width of the rect.
            height: Height of the rect.
            radii: Corner radii in pixels, (tl, tr, br, bl).

        Returns:
            ``True`` when a clip was applied.
        """
        if canvas is None:
            return False
        key = (x, y, width, height, tuple(radii))
        if key != self._clip_key:
            rect = make_rect(x, y, width, height)
            rrect = resolve_rrect(rect, radii)
            self._clip_shape = None if rect is None else ("rrect", rrect) if rrect is not None else ("rect", rect)
            self._clip_key = key
        shape = self._clip_shape
        if shape is None:
            return False
        kind, value = shape
        try:
            if kind == "rrect":
                canvas.clipRRect(value, True)
            else:
                canvas.clipRect(value, True)
            return True
        except Exception:
            exception_once(logger, "background_renderer_clip_exc", "Failed to clip to the rounded rect")
        # Content clipped square still stays inside the box.
        rect = make_rect(x, y, width, height)
        if rect is None:
            return False
        try:
            canvas.clipRect(rect, True)
        except Exception:
            exception_once(logger, "background_renderer_clip_rect_exc", "Failed to clip to the rect")
            return False
        return True

    def paint_background(self, canvas, x, y, width, height):
        """High-level helper: draw shadow/background/border using owner's config.

        This mirrors the previous sequence from Container.paint where the
        shadow/background/border were drawn in order.
        """
        self.paint_shadow_and_background(canvas, x, y, width, height)
        self.paint_border(canvas, x, y, width, height)
