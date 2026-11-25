from __future__ import annotations

import functools
import logging
from typing import Any

from nuiitivet.common.logging_once import exception_once
from nuiitivet.layout.alignment import AlignmentLike, normalize_alignment
from nuiitivet.observable.protocols import ReadOnlyStateProtocol
from nuiitivet.rendering.fit import Fit
from nuiitivet.rendering.raster import Raster, raster_image
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.rendering.skia import clip_rect, make_rect
from nuiitivet.rendering.skia.skia_module import get_skia
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.paint_replay import replay_safe

logger = logging.getLogger(__name__)


ImageSource = bytes | Raster | None


class Image(Widget):
    """A picture fitted into the widget: a PNG or JPEG as bytes, or decoded pixels as a :class:`Raster`.

    Without ``width`` and ``height`` the widget takes the picture's size.

    The picture is smoothed when scaled. Shrunk, it shows no moiré; enlarged,
    it turns soft, not blocky.

    Bytes are decoded at the first paint, on the UI thread. A Raster was
    decoded by the app, so its first paint only draws.
    """

    def __init__(
        self,
        source: ImageSource | ReadOnlyStateProtocol[ImageSource],
        *,
        fit: Fit = "contain",
        width: SizingLike = None,
        height: SizingLike = None,
        padding: int | tuple[int, int] | tuple[int, int, int, int] = 0,
        alignment: AlignmentLike = "center",
        key: str | None = None,
    ) -> None:
        """Initialize an Image widget.

        Args:
            source: Encoded PNG or JPEG bytes, a :class:`Raster`, ``None``
                for nothing, or a State of one of them.
            fit: Content fit mode. One of ``"contain"``, ``"cover"``, ``"fill"``, ``"none"``.
            width: Width sizing.
            height: Height sizing.
            padding: Insets from the allocated rect to the image.
            alignment: Content alignment in the allocated content rect.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(width=width, height=height, padding=padding, key=key)
        self._fit: Fit = self._normalize_fit(fit)
        self._align_raw: AlignmentLike = alignment
        self._alignment: tuple[str, str] = normalize_alignment(alignment, default=("center", "center"))

        self._source: ImageSource | ReadOnlyStateProtocol[ImageSource] = source
        self._decoded_image: Any | None = None

        if isinstance(source, ReadOnlyStateProtocol):
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

    @replay_safe
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

        if fit == "none":
            # Allow negative offsets so alignment works even when the image is
            # larger than the container (image is centered/aligned and clipped).
            dx = float(cx) + (float(cw) - draw_w) * fx
            dy = float(cy) + (float(ch) - draw_h) * fy
        else:
            dx = float(cx) + max(0.0, float(cw) - draw_w) * fx
            dy = float(cy) + max(0.0, float(ch) - draw_h) * fy

        if fit == "none" and (draw_w > float(cw) or draw_h > float(ch)):
            clip_r = make_rect(cx, cy, cw, ch)
            save_fn = getattr(canvas, "save", None)
            restore_fn = getattr(canvas, "restore", None)
            if callable(save_fn) and callable(restore_fn) and clip_r is not None:
                save_fn()
                clip_rect(canvas, clip_r)
                self._draw_image_rect(canvas, image, (0.0, 0.0, float(img_w), float(img_h)), (dx, dy, draw_w, draw_h))
                restore_fn()
                return

        self._draw_image_rect(canvas, image, (0.0, 0.0, float(img_w), float(img_h)), (dx, dy, draw_w, draw_h))

    def _on_source_change(self, value: ImageSource) -> None:
        old_size = self._image_size(self._decoded_image)
        self._decoded_image = self._image_of(value)
        if self._image_size(self._decoded_image) != old_size:
            self.mark_needs_layout()
        else:
            self.invalidate()

    def _image_of(self, value: ImageSource) -> Any | None:
        if value is None:
            return None
        if isinstance(value, Raster):
            return raster_image(value)
        if not isinstance(value, bytes):
            exception_once(
                logger,
                "image_source_type_exc",
                "Image source must be bytes | Raster | None, got %s",
                type(value).__name__,
            )
            return None

        backend = get_skia(raise_if_missing=False)
        image_cls = getattr(backend, "Image", None) if backend is not None else None
        make_from_encoded = getattr(image_cls, "MakeFromEncoded", None) if image_cls is not None else None
        if not callable(make_from_encoded):
            return None
        try:
            return make_from_encoded(value)
        except Exception:
            exception_once(logger, "image_decode_exc", "Failed to decode image bytes")
            return None

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
            sampling = _smooth_sampling(get_skia(raise_if_missing=False))
            try:
                canvas.drawImageRect(image, src_rect, dst_rect, *sampling)
                return
            except Exception:
                exception_once(logger, "image_draw_rect_exc", "drawImageRect failed")
            if sampling:
                try:
                    canvas.drawImageRect(image, src_rect, dst_rect)
                    return
                except Exception:
                    exception_once(logger, "image_draw_rect_plain_exc", "drawImageRect without sampling failed")

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


@functools.lru_cache(maxsize=4)
def _smooth_sampling(backend: Any) -> tuple[Any, ...]:
    """The arguments after ``dst`` that make ``drawImageRect`` filter between pixels and mipmap levels."""
    sampling_cls = getattr(backend, "SamplingOptions", None) if backend is not None else None
    linear = getattr(getattr(backend, "FilterMode", None), "kLinear", None)
    if sampling_cls is None or linear is None:
        return ()
    mipmap = getattr(getattr(backend, "MipmapMode", None), "kLinear", None)
    # The strict constraint, Skia's default, turns mipmaps off. The price: a cover crop's edge pixel
    # may blend in the picture just outside the crop.
    fast = getattr(getattr(backend, "Canvas", None), "kFast_SrcRectConstraint", None)
    try:
        if mipmap is None or fast is None:
            return (sampling_cls(linear),)
        return (sampling_cls(linear, mipmap), None, fast)
    except Exception:
        exception_once(logger, "image_sampling_exc", "Could not build the image sampling")
        return ()


__all__ = ["Image"]
