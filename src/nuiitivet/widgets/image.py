from __future__ import annotations

import logging
from typing import Any

from nuiitivet.common.logging_once import exception_once
from nuiitivet.layout.alignment import AlignmentLike, normalize_alignment
from nuiitivet.observable.protocols import ReadOnlyObservableProtocol
from nuiitivet.rendering.fit import Fit
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import make_rect
from nuiitivet.rendering.skia.skia_module import get_skia
from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)


class Image(Widget):
    """Display a raster image from in-memory bytes.

    Args:
        source: Encoded image bytes, ``None``, or an Observable that provides them.
        fit: Content fit mode. One of ``"contain"``, ``"cover"``, ``"fill"``, ``"none"``.
        alignment: Content alignment in the allocated content rect.
        width: Width sizing.
        height: Height sizing.
        padding: Space around content.
    """

    def __init__(
        self,
        source: bytes | None | ReadOnlyObservableProtocol[bytes | None],
        *,
        fit: Fit = "contain",
        width: SizingLike = None,
        height: SizingLike = None,
        padding: int | tuple[int, int] | tuple[int, int, int, int] = 0,
        alignment: AlignmentLike = "center",
    ) -> None:
        """Initialize an Image widget.

        Args:
            source: Encoded image bytes, ``None``, or an Observable that provides them.
            fit: Content fit mode. One of ``"contain"``, ``"cover"``, ``"fill"``, ``"none"``.
            width: Width sizing.
            height: Height sizing.
            padding: Space around content.
            alignment: Content alignment in the allocated content rect.
        """
        super().__init__(width=width, height=height, padding=padding)
        self._fit: Fit = self._normalize_fit(fit)
        self._align_raw: AlignmentLike = alignment
        self._alignment: tuple[str, str] = normalize_alignment(alignment, default=("center", "center"))

        self._source: bytes | None | ReadOnlyObservableProtocol[bytes | None] = source
        self._resolved_source: bytes | None = None
        self._decoded_image: Any | None = None
        self._decoded_token: tuple[int, int] | None = None

        if isinstance(source, ReadOnlyObservableProtocol):
            self.observe(source, self._on_source_change)
        else:
            self._on_source_change(source)

    @property
    def fit(self) -> Fit:
        return self._fit

    @fit.setter
    def fit(self, value: Fit) -> None:
        normalized = self._normalize_fit(value)
        if normalized == self._fit:
            return
        self._fit = normalized
        self.invalidate()

    @property
    def alignment(self) -> AlignmentLike:
        return self._align_raw

    @alignment.setter
    def alignment(self, value: AlignmentLike) -> None:
        self._align_raw = value
        self._alignment = normalize_alignment(value, default=("center", "center"))
        self.invalidate()

    def preferred_size(self, max_width: int | None = None, max_height: int | None = None) -> tuple[int, int]:
        """Return preferred size based on intrinsic image size and explicit sizing."""
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed" and h_dim.kind == "fixed":
            l, t, r, b = self.padding
            return (int(w_dim.value) + l + r, int(h_dim.value) + t + b)

        image = self._decoded_image
        intrinsic_w, intrinsic_h = self._image_size(image)

        width = int(w_dim.value) if w_dim.kind == "fixed" else intrinsic_w
        height = int(h_dim.value) if h_dim.kind == "fixed" else intrinsic_h

        l, t, r, b = self.padding
        total_w = int(width) + int(l) + int(r)
        total_h = int(height) + int(t) + int(b)

        if max_width is not None:
            total_w = min(total_w, int(max_width))
        if max_height is not None:
            total_h = min(total_h, int(max_height))

        return (max(0, total_w), max(0, total_h))

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint the image into the given rect according to fit and alignment."""
        self.set_last_rect(x, y, width, height)

        if canvas is None:
            return

        image = self._decoded_image
        if image is None:
            return

        img_w, img_h = self._image_size(image)
        if img_w <= 0 or img_h <= 0:
            return

        cx, cy, cw, ch = self.content_rect(x, y, width, height)
        if cw <= 0 or ch <= 0:
            return

        fit = self._fit
        align_x, align_y = self._alignment
        fx = self._align_factor(align_x)
        fy = self._align_factor(align_y)

        if fit == "fill":
            self._draw_image_rect(
                canvas,
                image,
                (0.0, 0.0, float(img_w), float(img_h)),
                (float(cx), float(cy), float(cw), float(ch)),
            )
            return

        if fit == "cover":
            src = self._compute_cover_source(img_w, img_h, cw, ch, fx, fy)
            self._draw_image_rect(canvas, image, src, (float(cx), float(cy), float(cw), float(ch)))
            return

        if fit == "contain":
            scale = min(float(cw) / float(img_w), float(ch) / float(img_h))
            draw_w = max(0.0, float(img_w) * scale)
            draw_h = max(0.0, float(img_h) * scale)
        else:  # "none"
            draw_w = float(img_w)
            draw_h = float(img_h)

        dx = float(cx) + max(0.0, float(cw) - draw_w) * fx
        dy = float(cy) + max(0.0, float(ch) - draw_h) * fy

        if fit == "none" and (draw_w > float(cw) or draw_h > float(ch)):
            save = getattr(canvas, "save", None)
            restore = getattr(canvas, "restore", None)
            clip = getattr(canvas, "clipRect", None)
            if callable(save) and callable(restore) and callable(clip):
                save()
                clip((float(cx), float(cy), float(cx + cw), float(cy + ch)))
                self._draw_image_rect(canvas, image, (0.0, 0.0, float(img_w), float(img_h)), (dx, dy, draw_w, draw_h))
                restore()
                return

        self._draw_image_rect(canvas, image, (0.0, 0.0, float(img_w), float(img_h)), (dx, dy, draw_w, draw_h))

    def _on_source_change(self, value: bytes | None) -> None:
        if value is not None and not isinstance(value, bytes):
            exception_once(
                logger,
                "image_source_type_exc",
                "Image source must be bytes | None, got %s",
                type(value).__name__,
            )
            self._resolved_source = None
        else:
            self._resolved_source = value

        self._decoded_image = None
        self._decoded_token = None
        self._decode_image_if_needed()
        self.mark_needs_layout()

    def _decode_image_if_needed(self) -> Any | None:
        source = self._resolved_source
        if source is None:
            self._decoded_image = None
            self._decoded_token = None
            return None

        token = (id(source), len(source))
        if self._decoded_token == token and self._decoded_image is not None:
            return self._decoded_image

        skia = get_skia(raise_if_missing=False)
        if skia is None:
            self._decoded_image = None
            self._decoded_token = None
            return None

        image_cls = getattr(skia, "Image", None)
        make_from_encoded = getattr(image_cls, "MakeFromEncoded", None) if image_cls is not None else None
        if not callable(make_from_encoded):
            self._decoded_image = None
            self._decoded_token = None
            return None

        try:
            decoded = make_from_encoded(source)
        except Exception:
            exception_once(logger, "image_decode_exc", "Failed to decode image bytes")
            decoded = None

        self._decoded_image = decoded
        # Keep token even when decode failed to avoid repeated decode attempts
        # for the same bytes on every frame.
        self._decoded_token = token
        return decoded

    def _image_size(self, image: Any | None) -> tuple[int, int]:
        if image is None:
            return (0, 0)

        try:
            width_attr = getattr(image, "width", None)
            w = width_attr() if callable(width_attr) else width_attr
            height_attr = getattr(image, "height", None)
            h = height_attr() if callable(height_attr) else height_attr
            return (max(0, int(w or 0)), max(0, int(h or 0)))
        except Exception:
            exception_once(logger, "image_size_exc", "Failed to read decoded image size")
            return (0, 0)

    def _draw_image_rect(
        self,
        canvas,
        image: Any,
        src: tuple[float, float, float, float],
        dst: tuple[float, float, float, float],
    ) -> None:
        src_rect = make_rect(src[0], src[1], src[2], src[3])
        dst_rect = make_rect(dst[0], dst[1], dst[2], dst[3])

        if src_rect is not None and dst_rect is not None and hasattr(canvas, "drawImageRect"):
            try:
                canvas.drawImageRect(image, src_rect, dst_rect)
                return
            except Exception:
                exception_once(logger, "image_draw_rect_exc", "drawImageRect failed")

        # Fallback for canvases without drawImageRect support.
        if src[0] == 0.0 and src[1] == 0.0 and dst[2] == src[2] and dst[3] == src[3] and hasattr(canvas, "drawImage"):
            try:
                canvas.drawImage(image, dst[0], dst[1])
            except Exception:
                exception_once(logger, "image_draw_image_exc", "drawImage fallback failed")

    def _compute_cover_source(
        self,
        img_w: int,
        img_h: int,
        dst_w: int,
        dst_h: int,
        fx: float,
        fy: float,
    ) -> tuple[float, float, float, float]:
        src_ar = float(img_w) / float(img_h)
        dst_ar = float(dst_w) / float(dst_h)

        if src_ar > dst_ar:
            crop_h = float(img_h)
            crop_w = crop_h * dst_ar
            sx = max(0.0, float(img_w) - crop_w) * fx
            sy = 0.0
        else:
            crop_w = float(img_w)
            crop_h = crop_w / dst_ar
            sx = 0.0
            sy = max(0.0, float(img_h) - crop_h) * fy

        return (sx, sy, crop_w, crop_h)

    def _normalize_fit(self, value: Fit | str) -> Fit:
        key = str(value).strip().lower()
        if key in ("contain", "cover", "fill", "none"):
            return key  # type: ignore[return-value]
        return "contain"

    def _align_factor(self, axis_align: str) -> float:
        if axis_align == "center":
            return 0.5
        if axis_align == "end":
            return 1.0
        return 0.0


__all__ = ["Image"]
