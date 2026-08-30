"""Core text widget.

Displays a string or State-like value and invalidates when the value changes.
"""

import logging
import math
from typing import Any, Callable, List, Literal, Optional, Tuple, Union, TYPE_CHECKING

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
from nuiitivet.theme.type_scale import DEFAULT_TYPE_SCALE, TypeScaleToken
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgets.text_style import TextStyle, TextStyleProtocol

if TYPE_CHECKING:
    pass


_logger = logging.getLogger(__name__)


class TextBase(Widget):
    """Display text with optional Observable binding.

    Parameters:
    - label: Text string or Observable
    - style: Visual style (color, font_family) — not typography or alignment
    - type_scale: MD3 type-scale token supplying typography (font size, line
      height, weight, tracking). Defaults to Body Medium.
    - alignment: Horizontal text alignment within the box (``"start"``,
      ``"center"``, ``"end"``).
    - width: Explicit width sizing
    - height: Explicit height sizing
    - padding: Space around text
    - max_lines: Maximum number of lines (``None`` = unbounded). Hard line
      breaks (``\\n``) and soft wrapping both count toward this limit.
    - overflow: What to do when text exceeds the layout box: ``"visible"``
      (draw beyond bounds), ``"clip"`` (cut at the edge), or ``"ellipsis"``
      (truncate the last visible line with ``…``).
    - truncation: Where the ellipsis is placed — ``"tail"``, ``"head"`` or
      ``"middle"``. Only meaningful when ``overflow="ellipsis"``.
    - soft_wrap: Whether text wraps at soft line breaks when the width is
      bounded. Hard breaks (``\\n``) always break regardless of this flag.
    """

    # instance Disposable returned from subscribing to a label Observable
    _label_unsub: Optional["Disposable"] = None

    # Paint-time cache to avoid expensive repeated shaping/measurement.
    _paint_cache_key: Optional[tuple] = None
    _paint_cache_lines: Optional[List[str]] = None

    def __init__(
        self,
        label: Union[str, ReadOnlyObservableProtocol[Any]],
        style: Optional[TextStyleProtocol] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        *,
        type_scale: Optional[TypeScaleToken] = None,
        alignment: Literal["start", "center", "end"] = "start",
        max_lines: Optional[int] = None,
        overflow: Literal["visible", "clip", "ellipsis"] = "visible",
        truncation: Literal["tail", "head", "middle"] = "tail",
        soft_wrap: bool = True,
    ):
        super().__init__(width=width, height=height, padding=padding)
        self.label = label

        # Use provided style or None (resolved via property)
        self._style = style

        # Typography comes from the type-scale token (not the style).
        self._type_scale = type_scale

        # Alignment is a layout/flow concern and lives on the widget.
        self._alignment: str = alignment if alignment in ("start", "center", "end") else "start"

        # Overflow / wrapping behavior lives on the widget, not the style.
        self._max_lines = self._normalize_max_lines(max_lines)
        self._overflow: str = overflow if overflow in ("visible", "clip", "ellipsis") else "visible"
        self._truncation: str = truncation if truncation in ("tail", "head", "middle") else "tail"
        self._soft_wrap: bool = bool(soft_wrap)

        # instance attribute tracking a Disposable returned by subscribe
        self._label_unsub = None

        self._paint_cache_key = None
        self._paint_cache_lines = None

    @staticmethod
    def _normalize_max_lines(value: Optional[int]) -> Optional[int]:
        """Normalize ``max_lines`` to ``None`` or an int ``>= 1``."""
        if value is None:
            return None
        try:
            v = int(value)
        except (TypeError, ValueError):
            return None
        return v if v >= 1 else 1

    def _wrap_paragraph(self, para: str, avail_w: float, measure: Callable[[str], float]) -> List[str]:
        """Greedily wrap a single paragraph (no hard breaks) to ``avail_w``.

        Wrapping only occurs when ``soft_wrap`` is enabled and a bounded width
        is available. Words longer than the width are broken character-by-
        character so they never overflow silently.
        """
        if not self._soft_wrap or avail_w <= 0 or measure(para) <= avail_w:
            return [para]

        lines: List[str] = []
        cur = ""
        for word in para.split(" "):
            candidate = word if not cur else cur + " " + word
            if measure(candidate) <= avail_w:
                cur = candidate
                continue
            if cur:
                lines.append(cur)
                cur = ""
            if measure(word) <= avail_w:
                cur = word
            else:
                # Break an overly long word across lines by character.
                chunk = ""
                for ch in word:
                    if chunk and measure(chunk + ch) > avail_w:
                        lines.append(chunk)
                        chunk = ch
                    else:
                        chunk += ch
                cur = chunk
        if cur or not lines:
            lines.append(cur)
        return lines

    def _layout_lines(
        self, txt: str, avail_w: float, measure: Callable[[str], float]
    ) -> Tuple[List[str], bool]:
        """Resolve ``txt`` into visible lines.

        Normalizes line endings, honors ``\\n`` as hard breaks, applies soft
        wrapping, then caps to ``max_lines``. Returns the lines together with a
        flag indicating whether content was cut by the line limit.
        """
        norm = txt.replace("\r\n", "\n").replace("\r", "\n")
        lines: List[str] = []
        for para in norm.split("\n"):
            lines.extend(self._wrap_paragraph(para, avail_w, measure))

        overflowed = False
        if self._max_lines is not None and len(lines) > self._max_lines:
            lines = lines[: self._max_lines]
            overflowed = True
        return lines, overflowed

    def _apply_ellipsis(
        self, lines: List[str], overflowed: bool, avail_w: float, measure: Callable[[str], float]
    ) -> List[str]:
        """Truncate the last visible line with ``…`` when content overflows."""
        if not lines or self._overflow != "ellipsis" or avail_w <= 0:
            return lines
        last = lines[-1]
        if overflowed or measure(last) > avail_w:
            lines = list(lines)
            lines[-1] = self._truncate_line(last, avail_w, measure)
        return lines

    def _truncate_line(self, text: str, avail_w: float, measure: Callable[[str], float]) -> str:
        """Truncate ``text`` to fit ``avail_w`` with an ellipsis at head/middle/tail."""
        ellipsis = "…"
        ew = measure(ellipsis)
        if ew > avail_w:
            return ellipsis
        n = len(text)

        if self._truncation == "head":
            lo, hi, best = 0, n, 0
            while lo <= hi:
                mid = (lo + hi) // 2
                if ew + measure(text[n - mid:]) <= avail_w:
                    best, lo = mid, mid + 1
                else:
                    hi = mid - 1
            return (ellipsis + text[n - best:]) if best > 0 else ellipsis

        if self._truncation == "middle":
            lo, hi = 0, n
            best_pre, best_suf = 0, 0
            while lo <= hi:
                k = (lo + hi) // 2
                pre, suf = (k + 1) // 2, k // 2
                candidate = text[:pre] + ellipsis + (text[n - suf:] if suf else "")
                if measure(candidate) <= avail_w:
                    best_pre, best_suf, lo = pre, suf, k + 1
                else:
                    hi = k - 1
            if best_pre == 0 and best_suf == 0:
                return ellipsis
            return text[:best_pre] + ellipsis + (text[n - best_suf:] if best_suf else "")

        # tail (default)
        lo, hi, best = 0, n, 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if measure(text[:mid]) + ew <= avail_w:
                best, lo = mid, mid + 1
            else:
                hi = mid - 1
        return (text[:best] + ellipsis) if best > 0 else ellipsis

    @staticmethod
    def _font_vmetrics(font: Any, font_size: float) -> Tuple[float, float]:
        """Return (ascent, descent) as positive magnitudes for baseline layout."""
        getter = getattr(font, "getMetrics", None)
        if callable(getter):
            try:
                m = getter()
                asc = float(getattr(m, "fAscent", 0.0))
                desc = float(getattr(m, "fDescent", 0.0))
                if asc != 0.0 or desc != 0.0:
                    return (-asc, desc)
            except Exception:
                pass
        return (float(font_size) * 0.8, float(font_size) * 0.2)

    @property
    def style(self) -> TextStyleProtocol:
        """Return the current text style."""
        if self._style is not None:
            return self._style
        return TextStyle()

    @property
    def type_scale(self) -> TypeScaleToken:
        """Return the active type-scale token (defaults to Body Medium)."""
        if self._type_scale is not None:
            return self._type_scale
        return DEFAULT_TYPE_SCALE

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
        # Typography comes from the type-scale token.
        font_size = self.type_scale.font_size
        weight = self.type_scale.weight
        tracking = self.type_scale.tracking

        try:
            tf = get_typeface(
                candidate_files=None,
                family_candidates=self._resolve_font_candidates(),
                pkg_font_dir=None,
                fallback_to_default=True,
                weight=weight,
            )

            # Available content width for wrapping: explicit width if fixed,
            # otherwise the constraint handed down by the parent (P0-C). ``0``
            # means unbounded, so soft wrapping stays off.
            l, t, r, b = self.padding
            if w_dim.kind == "fixed":
                avail_w = float(w_dim.value)
            elif max_width is not None:
                avail_w = max(0.0, float(max_width) - float(l) - float(r))
            else:
                avail_w = 0.0

            def measure_w(s: str) -> float:
                return float(measure_text_width(tf, font_size, str(s), tracking))

            lines, _ = self._layout_lines(txt, avail_w, measure_w)

            # Use advance width (the same metric paint uses for wrapping) and
            # round up, so a Text allocated its own preferred width never wraps
            # against itself due to an ink-vs-advance rounding gap.
            measured_width = 0
            for ln in lines:
                measured_width = max(measured_width, int(math.ceil(measure_w(ln))))
            if measured_width <= 0:
                measured_width = max(0, int(font_size * max(1, len(txt) * 0.6)))

            n_lines = max(1, len(lines))
            if n_lines == 1:
                # Preserve prior single-line ink-based height.
                sl, st, sr, sb = measure_text_ink_bounds(tf, font_size, lines[0] if lines else txt, tracking)
                measured_height = int(max(0.0, sb - st))
                if measured_height <= 0:
                    measured_height = int(font_size)
            else:
                line_h = float(self.type_scale.line_height)
                measured_height = int(round(line_h * n_lines))
        except Exception:
            exception_once(_logger, "text_preferred_size_measure_exc", "Text preferred_size measurement failed")
            # Fallback: approximate character width ~0.6 * font_size
            approx_char_w = int(font_size * 0.6)
            measured_width = len(txt) * approx_char_w
            measured_height = int(font_size)

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
        """Paint text with padding, multi-line layout and overflow support."""
        # Apply padding to get content area (M3: space between UI elements)
        cx, cy, cw, ch = self.content_rect(x, y, width, height)

        txt = self._resolve_label()
        font_size = self.type_scale.font_size
        weight = self.type_scale.weight
        tracking = self.type_scale.tracking
        tf = get_typeface(
            candidate_files=None,
            family_candidates=self._resolve_font_candidates(),
            pkg_font_dir=None,
            fallback_to_default=True,
            weight=weight,
        )
        font = make_font(tf, font_size)

        def measure_text_w(text_value: str) -> float:
            return float(measure_text_width(tf, font_size, str(text_value), tracking))

        alignment = self._alignment
        avail_w = float(cw)

        # Cache the resolved line list. The key must change when any factor
        # affecting line breaking or truncation changes.
        cache_key = (
            txt,
            int(cw),
            int(ch),
            float(font_size),
            int(weight),
            float(tracking),
            self._overflow,
            self._truncation,
            bool(self._soft_wrap),
            self._max_lines if self._max_lines is not None else -1,
            alignment,
            tuple(self.padding),
        )
        if self._paint_cache_key == cache_key and self._paint_cache_lines is not None:
            lines = self._paint_cache_lines
        else:
            laid, overflowed = self._layout_lines(txt, avail_w, measure_text_w)
            lines = self._apply_ellipsis(laid, overflowed, avail_w, measure_text_w)
            self._paint_cache_key = cache_key
            self._paint_cache_lines = lines

        if not lines or font is None or canvas is None:
            return

        # Resolve text color from the theme to an RGBA tuple and convert
        # to a skia color when skia is available.
        from nuiitivet.theme.theme import Theme

        rgba = resolve_color_to_rgba(self.style.color, default="#000000", theme=Theme.of(self))
        paint = make_paint(color=rgba_to_skia_color(rgba), style="fill", aa=True)
        if paint is None:
            return

        clip = self._overflow == "clip"
        if clip:
            canvas.save()
            canvas.clipRect((cx, cy, cx + cw, cy + ch))

        if len(lines) == 1:
            self._paint_single_line(
                canvas, font, tf, font_size, tracking, lines[0], cx, cy, cw, ch, alignment, paint
            )
        else:
            self._paint_multi_line(
                canvas, font, tf, font_size, tracking, lines, cx, cy, cw, ch, alignment, paint
            )

        if clip:
            canvas.restore()

    def _paint_single_line(
        self, canvas, font, tf, font_size, tracking, text, cx, cy, cw, ch, alignment, paint
    ) -> None:
        """Draw one line using tight ink bounds for centering (parity path)."""
        tp = make_text_blob(text, font, tracking)
        if tp is None:
            return
        ink_left, ink_top, ink_right, ink_bottom = measure_text_ink_bounds(tf, font_size, text, tracking)
        ink_w = max(0.0, float(ink_right) - float(ink_left))
        ink_h = max(0.0, float(ink_bottom) - float(ink_top))

        if alignment == "center":
            tx = float(cx) + (cw - ink_w) / 2 - float(ink_left)
        elif alignment == "end":
            tx = float(cx) + cw - ink_w - float(ink_left)
        else:
            tx = float(cx) - float(ink_left)
        ty = float(cy) + (ch - ink_h) / 2 - float(ink_top)
        canvas.drawTextBlob(tp, tx, ty, paint)

    def _paint_multi_line(
        self, canvas, font, tf, font_size, tracking, lines, cx, cy, cw, ch, alignment, paint
    ) -> None:
        """Draw stacked lines on consistent baselines derived from font metrics."""
        line_h = float(self.type_scale.line_height)
        ascent, descent = self._font_vmetrics(font, font_size)
        n = len(lines)
        block_h = line_h * n
        top = float(cy) + (ch - block_h) / 2.0
        # Vertically center the glyph box within each line slot.
        baseline_offset = (line_h - (ascent + descent)) / 2.0 + ascent

        for i, text in enumerate(lines):
            tp = make_text_blob(text, font, tracking)
            if tp is None:
                continue
            ink_left, _t, ink_right, _b = measure_text_ink_bounds(tf, font_size, text, tracking)
            ink_w = max(0.0, float(ink_right) - float(ink_left))
            if alignment == "center":
                tx = float(cx) + (cw - ink_w) / 2 - float(ink_left)
            elif alignment == "end":
                tx = float(cx) + cw - ink_w - float(ink_left)
            else:
                tx = float(cx) - float(ink_left)
            ty = top + i * line_h + baseline_offset
            canvas.drawTextBlob(tp, tx, ty, paint)

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
        super().on_mount()
        lbl = self.label
        if lbl is None:
            return
        subscribe = getattr(lbl, "subscribe", None)
        if callable(subscribe):

            def _cb(*_args, **_kwargs):
                try:
                    self._paint_cache_key = None
                    self._paint_cache_lines = None
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
        self._paint_cache_lines = None
        super().on_unmount()
