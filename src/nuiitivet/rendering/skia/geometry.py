from __future__ import annotations

from typing import Optional, Sequence, Union

import logging

from nuiitivet.common.logging_once import debug_once, exception_once

from .skia_module import get_skia


logger = logging.getLogger(__name__)


Number = Union[int, float]
RadiiInput = Union[list[Number], tuple[Number], Number, None]


def _normalize_radii(radii: Sequence[Number]) -> Sequence[float]:
    normalized = []
    for value in radii:
        try:
            normalized.append(float(max(0.0, value or 0.0)))
        except Exception:
            normalized.append(0.0)
    return normalized


def make_rect(x: Number, y: Number, width: Number, height: Number) -> Optional[object]:
    """Return a skia.Rect for the given bounds or None if unavailable."""

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    rect_cls = getattr(skia, "Rect", None)
    if rect_cls is None:
        return None

    try:
        return rect_cls.MakeXYWH(float(x), float(y), float(width), float(height))
    except Exception:
        exception_once(logger, "skia_rect_make_xywh_exc", "skia.Rect.MakeXYWH failed")
        try:
            rect = rect_cls()
        except Exception:
            exception_once(logger, "skia_rect_ctor_exc", "skia.Rect() failed")
            return None
        setter = getattr(rect, "setXYWH", None)
        if callable(setter):
            try:
                setter(float(x), float(y), float(width), float(height))
                return rect
            except Exception:
                exception_once(logger, "skia_rect_set_xywh_exc", "skia.Rect.setXYWH failed")
                return None
    return None


def make_rrect(rect, radii: Sequence[float]) -> Optional[object]:
    """Return a skia.RRect for the given rect and per-corner radii.

    Falls back to MakeRectXY or setRectRadii when MakeRectRadii is unavailable.
    Returns None if no RRect could be created or skia is missing.
    """

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    rrect_cls = getattr(skia, "RRect", None)
    if rrect_cls is None:
        return None

    normalized = _normalize_radii(radii)
    if not normalized:
        return None

    radii_pairs = []
    for radius in normalized:
        radii_pairs.extend([radius, radius])

    maker = getattr(rrect_cls, "MakeRectRadii", None)
    if callable(maker):
        try:
            return maker(rect, radii_pairs)
        except Exception:
            exception_once(logger, "skia_rrect_make_rect_radii_exc", "skia.RRect.MakeRectRadii failed")

    maker_xy = getattr(rrect_cls, "MakeRectXY", None)
    if callable(maker_xy):
        try:
            fallback = max(normalized)
            return maker_xy(rect, fallback, fallback)
        except Exception:
            exception_once(logger, "skia_rrect_make_rect_xy_exc", "skia.RRect.MakeRectXY failed")

    try:
        rrect = rrect_cls()
    except Exception:
        debug_once(logger, "skia_rrect_ctor_make_rrect_exc", "skia.RRect() failed in make_rrect")
        rrect = None
    if rrect is not None:
        setter = getattr(rrect, "setRectRadii", None)
        if callable(setter):
            try:
                setter(rect, radii_pairs)
                return rrect
            except Exception:
                exception_once(logger, "skia_rrect_set_rect_radii_exc", "skia.RRect.setRectRadii failed")

    return None


def _make_rect_xy(rect, radius: float) -> Optional[object]:
    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    try:
        rrect_cls = getattr(skia, "RRect", None)
    except Exception:
        debug_once(logger, "skia_get_rrect_cls_exc", "Failed to access skia.RRect")
        rrect_cls = None
    if rrect_cls is None:
        return None

    maker_xy = getattr(rrect_cls, "MakeRectXY", None)
    if callable(maker_xy):
        try:
            return maker_xy(rect, radius, radius)
        except Exception:
            debug_once(logger, "skia_rrect_make_rect_xy_exc", "skia.RRect.MakeRectXY failed")
            return None

    try:
        rrect = rrect_cls()
    except Exception:
        debug_once(logger, "skia_rrect_ctor_exc", "skia.RRect() failed")
        return None

    setter = getattr(rrect, "setRectXY", None)
    if callable(setter):
        try:
            setter(rect, radius, radius)
            return rrect
        except Exception:
            debug_once(logger, "skia_rrect_set_rect_xy_exc", "skia.RRect.setRectXY failed")
            return None

    return None


def resolve_rrect(rect, radii: RadiiInput) -> Optional[object]:
    """Resolve either per-corner radii or a scalar into a skia.RRect."""

    if rect is None:
        return None

    if isinstance(radii, (list, tuple)):
        normalized = _normalize_radii(radii)
        if not normalized or not any(value > 0.0 for value in normalized):
            return None
        rrect = make_rrect(rect, normalized)
        if rrect is not None:
            return rrect
        fallback = max(normalized)
        return _make_rect_xy(rect, fallback)

    try:
        radius = float(radii or 0.0)
    except Exception:
        debug_once(logger, "resolve_rrect_radius_float_exc", "Failed to coerce radii to float")
        return None

    if radius <= 0.0:
        return None

    return _make_rect_xy(rect, radius)


def draw_round_rect(canvas, rect, radii: RadiiInput, paint) -> bool:
    """Draw a rounded rect or fallback to a rect. Returns True on success."""

    if canvas is None or rect is None:
        return False

    rrect = resolve_rrect(rect, radii)
    try:
        if rrect is not None and hasattr(canvas, "drawRRect"):
            canvas.drawRRect(rrect, paint)
        elif hasattr(canvas, "drawRect"):
            canvas.drawRect(rect, paint)
        else:
            return False
    except Exception:
        try:
            canvas.drawRect(rect, paint)
        except Exception:
            exception_once(logger, "canvas_draw_round_rect_exc", "Failed to draw round rect and fallback rect")
            return False
    return True


def clip_round_rect(canvas, rect, radii: RadiiInput, anti_alias: bool = True) -> bool:
    """Clip canvas to a rounded rect or fallback to a rect. Returns True when applied."""

    if canvas is None or rect is None:
        return False

    rrect = resolve_rrect(rect, radii)
    try:
        if rrect is not None and hasattr(canvas, "clipRRect"):
            canvas.clipRRect(rrect, bool(anti_alias))
        elif hasattr(canvas, "clipRect"):
            canvas.clipRect(rect, bool(anti_alias))
        else:
            return False
    except Exception:
        try:
            canvas.clipRect(rect, bool(anti_alias))
        except Exception:
            exception_once(logger, "canvas_clip_round_rect_exc", "Failed to clip round rect and fallback rect")
            return False
    return True


def clip_rect(canvas, rect, anti_alias: bool = True) -> bool:
    """Clip canvas to a rect. Returns True when applied.

    This prefers ClipOp.kIntersect when available, but falls back to the
    simpler clipRect(rect, aa) signature.
    """

    if canvas is None or rect is None:
        return False

    skia = get_skia(raise_if_missing=False)
    try:
        if skia is not None:
            clip_op = getattr(skia, "ClipOp", None)
            if clip_op is not None and hasattr(clip_op, "kIntersect"):
                try:
                    canvas.clipRect(rect, clip_op.kIntersect, bool(anti_alias))
                    return True
                except Exception:
                    exception_once(
                        logger,
                        "canvas_cliprect_clipop_exc",
                        "canvas.clipRect(rect, ClipOp.kIntersect, aa) failed; falling back to simpler signature",
                    )
        canvas.clipRect(rect, bool(anti_alias))
        return True
    except Exception:
        exception_once(logger, "canvas_cliprect_exc", "canvas.clipRect failed")
        return False


def make_point(x: Number, y: Number) -> Optional[object]:
    """Return a skia.Point or None if unavailable."""

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None

    point_cls = getattr(skia, "Point", None)
    if point_cls is None:
        debug_once(logger, "skia_point_missing", "skia.Point is missing")
        return None
    try:
        return point_cls(float(x), float(y))
    except Exception:
        exception_once(logger, "skia_point_ctor_exc", "skia.Point(...) failed")
        return None


def draw_oval(canvas, rect, paint) -> bool:
    """Draw an oval for the given rect. Returns True on success."""

    if canvas is None or rect is None or paint is None:
        return False
    draw = getattr(canvas, "drawOval", None)
    if callable(draw):
        try:
            draw(rect, paint)
            return True
        except Exception:
            exception_once(logger, "canvas_drawoval_exc", "canvas.drawOval failed")
            return False

    debug_once(logger, "canvas_drawoval_missing", "canvas.drawOval unavailable")
    return False


def make_path() -> Optional[object]:
    """Return a skia.Path or None if unavailable."""

    skia = get_skia(raise_if_missing=False)
    if skia is None:
        return None
    path_cls = getattr(skia, "Path", None)
    if path_cls is None:
        debug_once(logger, "skia_path_missing", "skia.Path is missing")
        return None
    try:
        return path_cls()
    except Exception:
        exception_once(logger, "skia_path_ctor_exc", "skia.Path() failed")
        return None


def path_add_rect(path, rect) -> bool:
    """Add a rect to path. Returns True when applied."""

    if path is None or rect is None:
        return False
    adder = getattr(path, "addRect", None)
    if callable(adder):
        try:
            adder(rect)
            return True
        except Exception:
            exception_once(logger, "skia_path_addrect_exc", "path.addRect failed")
            return False
    debug_once(logger, "skia_path_addrect_missing", "path.addRect is missing")
    return False


def path_add_rrect(path, rrect) -> bool:
    """Add an rrect to path. Returns True when applied."""

    if path is None or rrect is None:
        return False

    adder = getattr(path, "addRRect", None)
    if callable(adder):
        try:
            adder(rrect)
            return True
        except Exception:
            exception_once(logger, "skia_path_addrrect_exc", "path.addRRect failed")
            return False

    debug_once(logger, "skia_path_addrrect_missing", "path.addRRect is missing")
    return False


def path_move_to(path, x: Number, y: Number) -> bool:
    if path is None:
        return False
    fn = getattr(path, "moveTo", None)
    if callable(fn):
        try:
            fn(float(x), float(y))
            return True
        except Exception:
            exception_once(logger, "skia_path_moveto_exc", "path.moveTo failed")
            return False
    debug_once(logger, "skia_path_moveto_missing", "path.moveTo is missing")
    return False


def path_line_to(path, x: Number, y: Number) -> bool:
    if path is None:
        return False
    fn = getattr(path, "lineTo", None)
    if callable(fn):
        try:
            fn(float(x), float(y))
            return True
        except Exception:
            exception_once(logger, "skia_path_lineto_exc", "path.lineTo failed")
            return False
    debug_once(logger, "skia_path_lineto_missing", "path.lineTo is missing")
    return False


__all__ = [
    "make_rect",
    "make_rrect",
    "resolve_rrect",
    "draw_round_rect",
    "clip_round_rect",
    "clip_rect",
    "make_point",
    "draw_oval",
    "make_path",
    "path_add_rect",
    "path_add_rrect",
    "path_move_to",
    "path_line_to",
]
