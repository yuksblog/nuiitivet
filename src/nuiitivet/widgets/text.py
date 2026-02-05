"""Core text widget.

Displays a string or State-like value and invalidates when the value changes.
"""

import logging
from typing import Any, Optional, Tuple, Union, TYPE_CHECKING

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.widget import Widget
from nuiitivet.observable import Disposable, ReadOnlyObservableProtocol
from nuiitivet.rendering.skia import (
    get_typeface,
    get_default_font_fallbacks,
    make_font,
    make_paint,
    make_text_blob,
    measure_text_ink_bounds,
    measure_text_width,
    rgba_to_skia_color,
)
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgets.text_style import TextStyle, TextStyleProtocol

if TYPE_CHECKING:
    pass


_logger = logging.getLogger(__name__)


class TextBase(Widget):
    """Display text with optional Observable binding.

    Parameters:
    - label: Text string or Observable
    - style: Text style for font size, color, alignment, overflow
    - width: Explicit width sizing
    - height: Explicit height sizing
    - padding: Space around text
    """

    # instance Disposable returned from subscribing to a label Observable
    _label_unsub: Optional["Disposable"] = None

    # Paint-time cache to avoid expensive repeated shaping/measurement.
    _paint_cache_key: Optional[tuple] = None
    _paint_cache_text: Optional[str] = None
    _paint_cache_advance_w: Optional[float] = None

    def __init__(
        self,
        label: Union[str, ReadOnlyObservableProtocol[Any]],
        style: Optional[TextStyleProtocol] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
    ):
        super().__init__(width=width, height=height, padding=padding)
        self.label = label

        # Use provided style or None (resolved via property)
        self._style = style

        # instance attribute tracking a Disposable returned by subscribe
        self._label_unsub = None

        self._paint_cache_key = None
        self._paint_cache_text = None
        self._paint_cache_advance_w = None

    @property
    def style(self) -> TextStyleProtocol:
        """Return the current text style."""
        if self._style is not None:
            return self._style
        return TextStyle()

    def _resolve_font_candidates(self) -> Tuple[str, ...]:
        """Resolve font family candidates including Japanese fonts."""
        fallbacks = get_default_font_fallbacks()
        if self.style.font_family:
            return (self.style.font_family,) + fallbacks
        return fallbacks

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> tuple[int, int]:
        """Return the preferred (width, height) for this Text including padding (M3準拠).

        Use explicit sizing if provided, otherwise measure text content.
        """
        # Check for explicit sizing first
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        # If both sizing are fixed, return them directly (plus padding)
        if w_dim.kind == "fixed" and h_dim.kind == "fixed":
            l, t, r, b = self.padding
            return (int(w_dim.value) + l + r, int(h_dim.value) + t + b)

        # Otherwise measure the text
        txt = self._resolve_label()
        # Use font size from style
        font_size = self.style.font_size

        try:
            tf = get_typeface(
                candidate_files=None,
                family_candidates=self._resolve_font_candidates(),
                pkg_font_dir=None,
                fallback_to_default=True,
            )
            left, top, right, bottom = measure_text_ink_bounds(tf, font_size, txt)
            measured_width = int(max(0.0, right - left))
            measured_height = int(max(0.0, bottom - top))

            if measured_width <= 0:
                measured_width = max(0, int(font_size * max(1, len(txt) * 0.6)))
            if measured_height <= 0:
                measured_height = font_size
        except Exception:
            exception_once(_logger, "text_preferred_size_measure_exc", "Text preferred_size measurement failed")
            # Fallback: approximate character width ~0.6 * font_size
            approx_char_w = int(font_size * 0.6)
            measured_width = len(txt) * approx_char_w
            measured_height = font_size

        # Apply explicit sizing where provided
        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            width = measured_width

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = measured_height

        # Add padding (M3: space between UI elements)
        l, t, r, b = self.padding
        total_w = int(width) + int(l) + int(r)
        total_h = int(height) + int(t) + int(b)

        if max_width is not None:
            total_w = min(int(total_w), int(max_width))
        if max_height is not None:
            total_h = min(int(total_h), int(max_height))

        return (int(total_w), int(total_h))

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """Paint text with padding support (M3準拠)."""
        # Apply padding to get content area (M3: space between UI elements)
        cx, cy, cw, ch = self.content_rect(x, y, width, height)

        txt = self._resolve_label()
        tf = get_typeface(
            candidate_files=None,
            family_candidates=self._resolve_font_candidates(),
            pkg_font_dir=None,
            fallback_to_default=True,
        )
        # Use font size from style
        font = make_font(tf, self.style.font_size)

        def measure_text_w(text_value: str) -> float:
            return float(measure_text_width(tf, self.style.font_size, str(text_value)))

        # Cache overflow processing and alignment width.
        # Key must change when any factor affecting truncation/advance width changes.
        cache_key = (
            txt,
            int(cw),
            int(ch),
            float(self.style.font_size),
            str(self.style.overflow),
            str(self.style.text_alignment),
            tuple(self.padding),
        )
        if self._paint_cache_key == cache_key and self._paint_cache_text is not None:
            txt = self._paint_cache_text
            cached_advance = self._paint_cache_advance_w
        else:
            cached_advance = None

        # Overflow handling: ellipsis requires measurement. Clip can be done via canvas clipping.
        if self.style.overflow == "ellipsis" and cw > 0 and self._paint_cache_key != cache_key:
            text_width = measure_text_w(txt)
            if text_width > cw:
                ellipsis = "…"
                ellipsis_width = measure_text_w(ellipsis)

                left, right = 0, len(txt)
                while left < right:
                    mid = (left + right + 1) // 2
                    test_text = txt[:mid]
                    test_width = measure_text_w(test_text)
                    if test_width + ellipsis_width <= cw:
                        left = mid
                    else:
                        right = mid - 1

                txt = (txt[:left] + ellipsis) if left > 0 else ellipsis

        tp = make_text_blob(txt, font)
        # skia may return None for an empty or unrenderable blob (or missing backend); guard
        # against that to avoid calling .bounds() on None.
        if tp is None:
            # Nothing to draw for empty/unrenderable text or missing backend
            return

        ink_left, ink_top, ink_right, ink_bottom = measure_text_ink_bounds(tf, self.style.font_size, txt)
        ink_w = max(0.0, float(ink_right) - float(ink_left))
        ink_h = max(0.0, float(ink_bottom) - float(ink_top))

        # Use advance width for center/end alignment.
        alignment = str(self.style.text_alignment)
        if cached_advance is not None:
            advance_width = float(cached_advance)
        elif alignment in ("center", "end"):
            try:
                advance_width = float(measure_text_w(txt))
            except Exception:
                advance_width = 0.0
        else:
            advance_width = 0.0

        # Handle text alignment.
        # Use tight ink bounds for visual alignment.
        tx: float
        if alignment == "start":
            tx = float(cx) - float(ink_left)
        elif alignment == "center":
            tx = float(cx) + (cw - ink_w) / 2 - float(ink_left)
        elif alignment == "end":
            tx = float(cx) + cw - ink_w - float(ink_left)
        else:
            # Fallback to start
            tx = float(cx) - float(ink_left)

        # Vertical centering
        ty: float = float(cy) + (ch - ink_h) / 2 - float(ink_top)

        # Resolve text color from the theme to an RGBA tuple and convert
        # to a skia color when skia is available.
        from nuiitivet.theme.manager import manager as theme_manager

        rgba = resolve_color_to_rgba(self.style.color, default="#000000", theme=theme_manager.current)
        paint_color = rgba_to_skia_color(rgba)

        paint = make_paint(color=paint_color, style="fill", aa=True)
        if paint is not None and canvas is not None:
            # Apply clipping if overflow is "clip"
            if self.style.overflow == "clip":
                canvas.save()
                canvas.clipRect((cx, cy, cx + cw, cy + ch))
                canvas.drawTextBlob(tp, tx, ty, paint)
                canvas.restore()
            else:
                canvas.drawTextBlob(tp, tx, ty, paint)

        # Update cache for stable frames.
        self._paint_cache_key = cache_key
        self._paint_cache_text = txt
        if alignment in ("center", "end"):
            self._paint_cache_advance_w = float(advance_width)
        else:
            self._paint_cache_advance_w = None

    def _resolve_label(self) -> str:
        lbl = self.label
        if hasattr(lbl, "value"):
            try:
                return str(lbl.value)
            except Exception:
                exception_once(_logger, "text_label_value_str_exc", "Failed to stringify label.value")
                return str(lbl)
        return str(lbl)

    def on_mount(self) -> None:
        lbl = self.label
        if lbl is None:
            return
        subscribe = getattr(lbl, "subscribe", None)
        if callable(subscribe):

            def _cb(*_args, **_kwargs):
                try:
                    self._paint_cache_key = None
                    self._paint_cache_text = None
                    self._paint_cache_advance_w = None
                    # Label changes affect measured width/height, so request
                    # layout when possible and always schedule a redraw.
                    if self.needs_layout:
                        self.invalidate()
                    else:
                        self.mark_needs_layout()
                except Exception:
                    exception_once(_logger, "text_label_change_cb_exc", "Text label change callback failed")

            try:
                # subscribe is expected to return a Disposable with dispose()
                unsub = subscribe(_cb)
                # Accept only Disposable-style subscriptions. Store the
                # Disposable directly and call .dispose() on unmount.
                if hasattr(unsub, "dispose"):
                    self._label_unsub = unsub
                else:
                    # If something else is returned, be conservative and
                    # do not retain it (forces callers to update).
                    self._label_unsub = None
            except Exception:
                exception_once(_logger, "text_label_subscribe_exc", "Text label subscribe failed")
                self._label_unsub = None

    def on_unmount(self) -> None:
        unsub = getattr(self, "_label_unsub", None)
        if unsub is not None:
            try:
                # Expect a Disposable and call dispose()
                unsub.dispose()
            except Exception:
                exception_once(_logger, "text_label_unsub_dispose_exc", "Text label unsubscribe dispose failed")
            self._label_unsub = None

        self._paint_cache_key = None
        self._paint_cache_text = None
        self._paint_cache_advance_w = None
