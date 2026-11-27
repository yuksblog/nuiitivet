"""Core text widget.

Displays a string or State-like value and invalidates when the value changes.
"""

from nuiitivet.widgeting.paint_replay import replay_safe
import logging
import math
import unicodedata
from typing import Any, Callable, List, Literal, NamedTuple, Optional, Tuple, Union, TYPE_CHECKING

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.widget_binding import notify_binding_probe
from nuiitivet.observable import Disposable, ReadOnlyStateProtocol
from nuiitivet.rendering.skia import (
    get_typeface,
    get_default_font_fallbacks,
    make_font,
    make_rect,
    make_text_blob,
    measure_text_ink_bounds,
    measure_text_width,
    rgba_to_skia_color,
    shared_paint,
)
from nuiitivet.theme.dependency import ThemeKept
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.type_scale import DEFAULT_TYPE_SCALE, TypeScale, TypeScaleToken
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgets._line_break_data import LINE_BREAK_RANGES
from nuiitivet.widgets.semantics import Semantics, SemanticsNode, SemanticsRole, attach_semantics
from nuiitivet.widgets.text_style import TextStyle, TextStyleProtocol

if TYPE_CHECKING:
    pass


_logger = logging.getLogger(__name__)

# The float error a line height times a line count may carry.
_FLOAT_SLACK = 1e-6


def _line_break_classes(*names: str) -> frozenset[str]:
    """Return the characters of the given Unicode line break classes."""
    return frozenset(
        chr(code) for name in names for low, high in LINE_BREAK_RANGES[name] for code in range(low, high + 1)
    )


def _quotation_marks(excluding: str) -> frozenset[str]:
    """Return the quotation marks outside a general category: ``Pi`` opens, ``Pf`` closes."""
    return frozenset(mark for mark in _line_break_classes("QU") if unicodedata.category(mark) != excluding)


class _Run(NamedTuple):
    """One laid-out line: its text blob and the horizontal extent of its ink."""

    blob: Optional[object]
    ink_left: float
    ink_right: float


class _PaintCache(NamedTuple):
    """What a paint reuses while the text, the box and the font are unchanged."""

    key: tuple
    typeface: Optional[object]
    runs: List[_Run]
    ascent: float
    descent: float


class _Look(NamedTuple):
    """What the theme and the font settings decide: the typeface and the colour."""

    typeface: Optional[object]
    color: Any


class TextBase(Widget):
    """Display text with optional State binding.

    Parameters:
    - label: Text string or State
    - style: Visual style (color, font_family) — not typography or alignment
    - type_scale: MD3 type-scale token supplying typography (font size, line
      height, weight, tracking). Defaults to Body Medium.
    - alignment: Horizontal text alignment within the box (``"start"``,
      ``"center"``, ``"end"``).
    - width: Explicit width sizing
    - height: Explicit height sizing
    - padding: Insets from the allocated rect to the text
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

    @classmethod
    def editable_parameters(cls) -> dict[str, type]:
        """``type_scale`` is picked from :class:`TypeScale`'s roles."""
        return {"type_scale": TypeScale}

    # instance Disposable returned from subscribing to a label State
    _label_unsub: Optional["Disposable"] = None

    _paint_cache: Optional[_PaintCache] = None

    def __init__(
        self,
        label: Union[str, ReadOnlyStateProtocol[Any]],
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
        key: Optional[str] = None,
    ):
        super().__init__(width=width, height=height, padding=padding, key=key)
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

        self._paint_cache = None
        self._look: ThemeKept[_Look] = ThemeKept()

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

    # East Asian wide, fullwidth and halfwidth: a line may break beside one.
    _BREAKING_WIDTHS = frozenset("WFH")
    # Kinsoku, by Unicode line break class. No line starts with closing
    # punctuation, a hyphen, an iteration mark, a small kana, a unit sign, a
    # no-break space, an emoji modifier or the tail of a Hangul syllable.
    _NO_LINE_START = (
        _line_break_classes(
            "BA", "CJ", "CL", "CP", "EM", "EX", "GL", "HH", "HY", "IN", "IS", "JT", "JV", "NS", "PO", "SY", "WJ"
        )
        | _quotation_marks(excluding="Pi")
        # Its class allows the break, but Japanese typed on Windows carries it for the wave dash.
        | {"\N{FULLWIDTH TILDE}"}
    )
    # No line ends with an opening bracket, a currency sign or a joiner.
    _NO_LINE_END = _line_break_classes("BB", "GL", "OP", "PR", "WJ", "ZWJ") | _quotation_marks(excluding="Pf")

    @classmethod
    def _breaks_between(cls, before: str, after: str) -> bool:
        """Whether a line may end with ``before`` and the next start with ``after``.

        The Unicode line breaking algorithm (UAX 14) in a simplified form. A
        break needs an East Asian character on one side, so a word in a spaced
        script stays whole. Kinsoku forbids it, by the line break class of
        either character. So does a combining mark or a format character
        after it.
        """
        widths = (unicodedata.east_asian_width(before), unicodedata.east_asian_width(after))
        if cls._BREAKING_WIDTHS.isdisjoint(widths):
            return False
        if before in cls._NO_LINE_END or after in cls._NO_LINE_START:
            return False
        return unicodedata.category(after) not in ("Mn", "Mc", "Me", "Cf")

    @classmethod
    def _unbreakable_pieces(cls, word: str) -> List[str]:
        """Split a word without spaces into the pieces a line may break between."""
        if word.isascii():
            return [word]
        pieces: List[str] = []
        start = 0
        for i in range(1, len(word)):
            if cls._breaks_between(word[i - 1], word[i]):
                pieces.append(word[start:i])
                start = i
        pieces.append(word[start:])
        return pieces

    def _wrap_paragraph(self, para: str, avail_w: float, measure: Callable[[str], float]) -> List[str]:
        """Greedily wrap a single paragraph (no hard breaks) to ``avail_w``.

        Wrapping only occurs when ``soft_wrap`` is enabled and a bounded width
        is available. A line breaks at a space, or beside a CJK character
        where :meth:`_breaks_between` allows. A piece longer than the width is
        broken character-by-character so it never overflows silently.
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
            # A word that fits is never split, so it costs one measure.
            glue = " "
            for piece in self._unbreakable_pieces(word):
                candidate = piece if not cur else cur + glue + piece
                glue = ""
                if measure(candidate) <= avail_w:
                    cur = candidate
                    continue
                if cur:
                    lines.append(cur)
                    cur = ""
                if measure(piece) <= avail_w:
                    cur = piece
                else:
                    chunk = ""
                    for ch in piece:
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
        family = self.style.font_family
        if family:
            return (family,) + fallbacks
        return fallbacks

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> tuple[int, int]:
        """Return the preferred (width, height), padding included.

        A fixed ``width`` or ``height`` is returned as given. A measured
        height is the type scale's line height times the number of lines,
        rounded up. The glyphs do not change it.
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
        except Exception:
            exception_once(_logger, "text_preferred_size_measure_exc", "Text preferred_size measurement failed")
            # Fallback: approximate character width ~0.6 * font_size
            approx_char_w = int(font_size * 0.6)
            measured_width = len(txt) * approx_char_w
            n_lines = 1

        # Rounded up, so the box holds the lines paint stacks at the unrounded line height.
        measured_height = int(math.ceil(float(self.type_scale.line_height) * n_lines - _FLOAT_SLACK))

        # Apply explicit sizing where provided
        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            width = measured_width

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = measured_height

        # The allocated rect is the text plus its padding.
        l, t, r, b = self.padding
        total_w = int(width) + int(l) + int(r)
        total_h = int(height) + int(t) + int(b)

        if max_width is not None:
            total_w = min(int(total_w), int(max_width))
        if max_height is not None:
            total_h = min(int(total_h), int(max_height))

        return (int(total_w), int(total_h))

    @replay_safe
    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """Paint text with padding, multi-line layout and overflow support."""
        cx, cy, cw, ch = self.content_rect(x, y, width, height)

        txt = self._resolve_label()
        type_scale = self.type_scale
        font_size = type_scale.font_size
        weight = type_scale.weight
        tracking = type_scale.tracking
        # A parent recolours its label by replacing the style object.
        look = self._look.get(self, (self._style, get_default_font_fallbacks()), self._resolve_look)
        tf = look.typeface
        alignment = self._alignment

        # The key holds every input of line breaking and truncation. The
        # typeface is compared by identity beside it.
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
        cache = self._paint_cache
        if cache is None or cache.key != cache_key or cache.typeface is not tf:
            cache = self._build_paint_cache(cache_key, tf, txt, float(cw), font_size, tracking)
            self._paint_cache = cache

        runs = cache.runs
        if not runs or canvas is None:
            return
        paint = shared_paint(look.color)
        if paint is None:
            return

        clip = self._overflow == "clip"
        if clip:
            canvas.save()
            canvas.clipRect(self._clip_rect(len(runs), cx, cy, cw, ch))

        self._paint_lines(canvas, cache, cx, cy, cw, ch, alignment, paint)

        if clip:
            canvas.restore()

    def _resolve_look(self) -> _Look:
        from nuiitivet.theme.theme import Theme

        style = self.style
        family = style.font_family
        fallbacks = get_default_font_fallbacks()
        typeface = get_typeface(
            candidate_files=None,
            family_candidates=(family,) + fallbacks if family else fallbacks,
            pkg_font_dir=None,
            fallback_to_default=True,
            weight=self.type_scale.weight,
        )
        rgba = resolve_color_to_rgba(style.color, default="#000000", theme=Theme.of(self))
        return _Look(typeface, rgba_to_skia_color(rgba))

    def _build_paint_cache(
        self, key: tuple, tf: Optional[object], txt: str, avail_w: float, font_size: float, tracking: float
    ) -> _PaintCache:
        """Break ``txt`` into lines and build one run per line."""

        def measure_text_w(text_value: str) -> float:
            return float(measure_text_width(tf, font_size, str(text_value), tracking))

        laid, overflowed = self._layout_lines(txt, avail_w, measure_text_w)
        lines = self._apply_ellipsis(laid, overflowed, avail_w, measure_text_w)
        font = make_font(tf, font_size)
        if not lines or font is None:
            return _PaintCache(key, tf, [], 0.0, 0.0)

        runs: List[_Run] = []
        for line in lines:
            ink_left, _, ink_right, _ = measure_text_ink_bounds(tf, font_size, line, tracking)
            runs.append(_Run(make_text_blob(line, font, tracking), ink_left, ink_right))
        ascent, descent = self._font_vmetrics(font, font_size)
        return _PaintCache(key, tf, runs, ascent, descent)

    @staticmethod
    def _aligned_x(run: _Run, cx: int, cw: int, alignment: str) -> float:
        ink_w = max(0.0, run.ink_right - run.ink_left)
        if alignment == "center":
            return float(cx) + (cw - ink_w) / 2 - run.ink_left
        if alignment == "end":
            return float(cx) + cw - ink_w - run.ink_left
        return float(cx) - run.ink_left

    def _clip_rect(self, lines: int, cx, cy, cw, ch) -> Optional[object]:
        """Return the rect ``overflow="clip"`` cuts at: the content box, taller while the lines fit it."""
        line_h = float(self.type_scale.line_height)
        if line_h * lines > ch + _FLOAT_SLACK:
            return make_rect(cx, cy, cw, ch)
        # A font taller than the line height puts ink past the first and the last line box.
        return make_rect(cx, cy - line_h, cw, ch + 2 * line_h)

    def _paint_lines(self, canvas, cache: _PaintCache, cx, cy, cw, ch, alignment, paint) -> None:
        """Draw the lines stacked in line boxes, the stack centred in the content box."""
        line_h = float(self.type_scale.line_height)
        block_h = line_h * len(cache.runs)
        top = float(cy) + (ch - block_h) / 2.0
        # The font's ascent and descent, not the line's ink, are centred in the line box.
        baseline_offset = (line_h - (cache.ascent + cache.descent)) / 2.0 + cache.ascent

        for i, run in enumerate(cache.runs):
            if run.blob is None:
                continue
            ty = top + i * line_h + baseline_offset
            canvas.drawTextBlob(run.blob, self._aligned_x(run, cx, cw, alignment), ty, paint)

    @property
    def semantics_node(self) -> SemanticsNode:
        """The node that says this text to assistive technology."""
        node = self._semantics_node
        if node is None:
            # Built on the first ask, so a text nobody reads aloud carries none.
            node = SemanticsNode(self._semantics)
            attach_semantics(self, node)
        return node

    def _semantics(self) -> Optional[Semantics]:
        text = self._resolve_label().strip()
        return Semantics(role=SemanticsRole.TEXT, label=text) if text else None

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
                notify_binding_probe(self)
                try:
                    self._paint_cache = None
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

        self._paint_cache = None
        self._look.clear()
        super().on_unmount()
