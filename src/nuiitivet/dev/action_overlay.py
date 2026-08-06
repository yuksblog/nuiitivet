"""Human-facing visualization of AI-driven dev-bridge actions (#398).

When an assistant drives a running app through the dev bridge (``click`` /
``scroll`` / ``type`` / ``key``), hot reload makes the screen update on its own -- but a human
watching cannot tell *what the assistant just did*. This module draws a
short-lived, human-only marker for each synthesized action so the human can
follow the AI's side of the pair-programming loop in real time.

It is the mirror image of :mod:`nuiitivet.dev.interaction`: that closes the loop
in one direction (letting the AI catch up on what the *human* did); this closes
the reverse direction (letting the *human* observe what the *AI* is doing).

Critical constraint -- the overlay must never pollute the assistant's
perception:

* Markers live in a paint-only registry, **outside the widget tree**, so
  :func:`nuiitivet.dev.perception.describe_tree` (which walks the tree) never
  sees them.
* :func:`paint_markers` is invoked only from the *live* frame paths (GPU /
  raster). The off-screen ``screenshot`` render
  (:meth:`App._render_snapshot`) deliberately does not call it, so the assistant
  never sees its own residue nor pays image tokens for it.

Each marker fades on its own timeline driven by the frame clock, so consecutive
actions accumulate into a readable *trail* rather than replacing one another. An
ordered caption stack in a corner keeps the sequence legible even when spatial
markers overlap. Recording is gated on an active dev session plus a live window,
so it is a no-op under headless / automated test runs; a
``NUIITIVET_DEV_ACTION_OVERLAY=0`` env var force-disables it.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from nuiitivet.input.codes import (
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    resolve_modifiers as _resolve_physical_modifiers,
)
from nuiitivet.observable import runtime

logger = logging.getLogger(__name__)

# Truthy/falsy spellings accepted for the disable env var.
_FALSY = {"0", "false", "no", "off"}

# How long a spatial marker (click ripple / type pill) stays on screen.
_MARKER_LIFETIME = 0.9
# A scroll marker lives longer. A click marks a point the human's eye is already
# near; a scroll moves the *whole view*, so they read the new content first and
# look for the cause second -- the marker has to survive that detour. It also
# carries less visual weight than the ripple (a thin chevron drifting away, not
# an expanding ring anchored on a dot), which costs it further legibility.
_SCROLL_MARKER_LIFETIME = 1.2
# Fraction of a scroll marker's life it stays at full opacity before fading, so
# the fade is a tail rather than the whole event (see :func:`_hold_then_fade`).
_SCROLL_MARKER_HOLD = 0.35
# Captions linger longer than spatial markers so the *sequence* stays readable
# even after the pulses have faded.
_CAPTION_LIFETIME = 2.6
# Most recent captions kept in the corner stack.
_MAX_CAPTIONS = 5
# Repaint pump cadence while any marker is alive (matches the animation clock).
_PUMP_INTERVAL = 1 / 60.0

# Accent that reads as "the assistant", distinct from app chrome (MD3 tertiary-ish).
_ACCENT = (124, 77, 255)  # indigo/violet


@dataclass
class _Marker:
    """One transient spatial pulse anchored at a point in root coordinates."""

    kind: str  # "click" | "type" | "scroll"
    x: float
    y: float
    text: Optional[str]
    born: float
    #: Scroll direction the marker drifts along (unit-ish; unused by other kinds).
    dx: float = 0.0
    dy: float = 0.0
    #: How long this marker stays on screen; per-kind, not one global constant.
    lifetime: float = _MARKER_LIFETIME

    def age(self, now: float) -> float:
        return now - self.born

    def progress(self, now: float) -> float:
        """Position in this marker's life, 0 at birth and 1 at expiry."""
        return max(0.0, min(1.0, self.age(now) / self.lifetime))

    def expired(self, now: float) -> bool:
        return self.age(now) >= self.lifetime


@dataclass
class _Caption:
    """One entry in the ordered corner caption stack."""

    seq: int
    text: str
    born: float

    def expired(self, now: float) -> bool:
        return (now - self.born) >= _CAPTION_LIFETIME


@dataclass
class _Registry:
    """Per-app paint-only state for the action overlay."""

    markers: list[_Marker] = field(default_factory=list)
    captions: list[_Caption] = field(default_factory=list)
    seq: int = 0
    ticker: Any = None  # the scheduled repaint pump, while active


# Keyed by id(app); an app's markers are wholly outside its widget tree.
_registries: dict[int, _Registry] = {}


def _overlay_active(app: Any) -> bool:
    """Whether markers should be recorded for ``app`` right now.

    Gated on an active dev session *and* a live window, so headless renders and
    automated tests (which drive actions without a window) never accumulate
    markers. ``NUIITIVET_DEV_ACTION_OVERLAY=0`` force-disables it.
    """
    if os.environ.get("NUIITIVET_DEV_ACTION_OVERLAY", "1").strip().lower() in _FALSY:
        return False
    if getattr(app, "_window", None) is None:
        return False
    try:
        from nuiitivet.dev.session import current_dev_session

        return current_dev_session() is not None
    except Exception:
        return False


def _registry(app: Any) -> _Registry:
    reg = _registries.get(id(app))
    if reg is None:
        reg = _Registry()
        _registries[id(app)] = reg
    return reg


def _combo_label(key: str, mask: int) -> str:
    """Render a key + modifier mask back to a human-readable combo.

    ``mask`` is resolved to physical modifiers first (``accel`` -> Ctrl/Cmd),
    then decoded in a stable order.
    """
    physical = _resolve_physical_modifiers(int(mask))
    parts: list[str] = []
    if physical & MOD_CTRL:
        parts.append("Ctrl")
    if physical & MOD_ALT:
        parts.append("Alt")
    if physical & MOD_SHIFT:
        parts.append("Shift")
    if physical & MOD_META:
        parts.append("Cmd")
    parts.append(str(key))
    return "+".join(parts)


def _push_caption(reg: _Registry, text: str, now: float) -> None:
    reg.seq += 1
    reg.captions.append(_Caption(seq=reg.seq, text=text, born=now))
    if len(reg.captions) > _MAX_CAPTIONS:
        del reg.captions[: len(reg.captions) - _MAX_CAPTIONS]


def _ensure_pump(app: Any, reg: _Registry) -> None:
    """Keep requesting frames while any marker is alive, so fades animate.

    ``App.invalidate`` alone paints one frame; a fade needs the frame clock to
    keep ticking until the last marker expires. The pump self-unschedules once
    the registry drains.
    """
    if reg.ticker is not None:
        return

    def _tick(_dt: float) -> None:
        if not reg.markers and not reg.captions:
            _stop_pump(reg)
            return
        try:
            app.invalidate()
        except Exception:
            logger.debug("action_overlay: invalidate pump failed", exc_info=True)

    try:
        runtime.clock.schedule_interval(_tick, _PUMP_INTERVAL)
        reg.ticker = _tick
    except Exception:
        logger.debug("action_overlay: failed to schedule repaint pump", exc_info=True)


def _stop_pump(reg: _Registry) -> None:
    if reg.ticker is None:
        return
    try:
        runtime.clock.unschedule(reg.ticker)
    except Exception:
        logger.debug("action_overlay: failed to unschedule repaint pump", exc_info=True)
    reg.ticker = None


def _record(app: Any, marker: Optional[_Marker], caption: str) -> None:
    if not _overlay_active(app):
        return
    now = time.monotonic()
    reg = _registry(app)
    if marker is not None:
        reg.markers.append(marker)
    _push_caption(reg, caption, now)
    _ensure_pump(app, reg)
    try:
        app.invalidate()
    except Exception:
        logger.debug("action_overlay: invalidate on record failed", exc_info=True)


# --- Recording entry points (called from the action verbs) -----------------


def record_click(app: Any, x: float, y: float, *, target: Optional[str] = None) -> None:
    """Mark a synthesized ``click`` at ``(x, y)`` (root coords).

    ``target`` is the resolved identifier (``key`` / ``label``); coordinate
    fallback clicks pass ``None`` and show a bare point.
    """
    label = f"click {target}" if target else "click"
    _record(app, _Marker(kind="click", x=float(x), y=float(y), text=target, born=time.monotonic()), label)


def _direction_words(dx: float, dy: float) -> str:
    """Render a scroll delta as ASCII direction words (never arrow glyphs).

    The caption font is a plain UI face resolved at paint time and may lack
    arrow glyphs, which would render as tofu; words always survive.
    """
    parts: list[str] = []
    if dy:
        parts.append("down" if dy > 0 else "up")
    if dx:
        parts.append("right" if dx > 0 else "left")
    return " ".join(parts)


def record_scroll(
    app: Any,
    x: float,
    y: float,
    *,
    dx: float = 0.0,
    dy: float = 0.0,
    target: Optional[str] = None,
    verb: str = "scroll",
) -> None:
    """Mark a synthesized scroll at ``(x, y)`` (root coords), drifting along its direction.

    Shared by ``scroll`` and ``scroll_into_view`` (``verb`` names which); ``dx`` /
    ``dy`` carry only the *direction*, so a one-notch nudge and a long jump draw
    the same chevron.
    """
    words = _direction_words(dx, dy)
    label = " ".join(part for part in (verb, words, target) if part)
    marker = _Marker(
        kind="scroll",
        x=float(x),
        y=float(y),
        text=target,
        born=time.monotonic(),
        dx=float(dx),
        dy=float(dy),
        lifetime=_SCROLL_MARKER_LIFETIME,
    )
    _record(app, marker, label)


def record_type(app: Any, *, x: Optional[float] = None, y: Optional[float] = None) -> None:
    """Mark a synthesized ``type`` near the focused widget.

    The typed *content* is never passed in or rendered (consistent with
    ``interaction_log``, which never logs typed text, and to avoid leaking it
    into ``screenshot``).
    """
    marker: Optional[_Marker] = None
    if x is not None and y is not None:
        marker = _Marker(kind="type", x=float(x), y=float(y), text=None, born=time.monotonic())
    _record(app, marker, "type")


def record_key(app: Any, key: str, mask: int) -> None:
    """Mark a synthesized ``key`` press, rendering its modifier combo."""
    _record(app, None, f"key {_combo_label(key, mask)}")


def reset(app: Any) -> None:
    """Drop all markers for ``app`` (used by tests)."""
    reg = _registries.pop(id(app), None)
    if reg is not None:
        _stop_pump(reg)


# --- Painting (called only from the LIVE frame paths, never the screenshot) --


def paint_markers(app: Any, canvas: Any, width: int, height: int) -> None:
    """Paint live action markers over the just-painted tree.

    Called from the on-screen GPU / raster frame paths *after* the widget tree
    is painted. Never called from :meth:`App._render_snapshot`, so markers are
    excluded from ``screenshot``. All failures are swallowed -- a decoration
    must never break the frame.
    """
    reg = _registries.get(id(app))
    if reg is None or (not reg.markers and not reg.captions):
        return

    now = time.monotonic()
    reg.markers = [m for m in reg.markers if not m.expired(now)]
    reg.captions = [c for c in reg.captions if not c.expired(now)]
    if not reg.markers and not reg.captions:
        _stop_pump(reg)
        return

    try:
        from nuiitivet.rendering.skia.skia_module import get_skia

        skia = get_skia(raise_if_missing=False)
        if skia is None:
            return
        for marker in reg.markers:
            _paint_marker(skia, canvas, marker, now)
        _paint_captions(skia, canvas, reg.captions, now, width, height)
    except Exception:
        logger.debug("action_overlay: paint_markers failed", exc_info=True)


def _ease_out(t: float) -> float:
    """Cubic ease-out for a natural-feeling ripple/fade (t in [0, 1])."""
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _hold_then_fade(t: float, *, hold: float) -> float:
    """Alpha that stays solid for the first ``hold`` of a life, then falls off linearly.

    The ripple's cubic fade (``(1 - t)**3``) is down to a fifth of its opacity a
    third of the way in, which the expanding ring survives -- growth is its own
    attention cue -- but a thin drifting chevron does not. Holding first makes
    the marker's *presence* the event and the fade merely its tail. Shared with
    the caption stack, which reaches for the same shape (see
    :func:`_paint_captions`).
    """
    if t <= hold:
        return 1.0
    return max(0.0, 1.0 - (t - hold) / max(1e-6, 1.0 - hold))


def _accent_color(skia: Any, alpha: float) -> Any:
    a = max(0, min(255, int(round(alpha * 255))))
    r, g, b = _ACCENT
    return skia.Color(r, g, b, a)


def _paint_marker(skia: Any, canvas: Any, marker: _Marker, now: float) -> None:
    progress = _ease_out(marker.progress(now))
    fade = 1.0 - progress

    if marker.kind == "click":
        # Expanding ring + a solid dot at the resolved center.
        radius = 6.0 + progress * 34.0
        ring = skia.Paint(AntiAlias=True)
        ring.setStyle(skia.Paint.kStroke_Style)
        ring.setStrokeWidth(2.5)
        ring.setColor(_accent_color(skia, fade))
        canvas.drawCircle(marker.x, marker.y, radius, ring)

        dot = skia.Paint(AntiAlias=True)
        dot.setColor(_accent_color(skia, fade * 0.9))
        canvas.drawCircle(marker.x, marker.y, 4.0, dot)
    elif marker.kind == "type":
        # A small caret pill near the focused widget; content is never shown.
        pill = skia.Paint(AntiAlias=True)
        pill.setColor(_accent_color(skia, fade * 0.85))
        rect = skia.Rect.MakeXYWH(marker.x - 3.0, marker.y - 9.0, 6.0, 18.0)
        canvas.drawRoundRect(rect, 3.0, 3.0, pill)
    elif marker.kind == "scroll":
        # Its own alpha curve: the ripple's cubic fade leaves a thin chevron
        # invisible long before the marker actually expires.
        _paint_scroll_chevron(
            skia,
            canvas,
            marker,
            progress,
            _hold_then_fade(marker.progress(now), hold=_SCROLL_MARKER_HOLD),
        )


def _paint_scroll_chevron(skia: Any, canvas: Any, marker: _Marker, progress: float, fade: float) -> None:
    """Draw a chevron pointing along the scroll direction, drifting as it fades.

    The drift is what distinguishes it at a glance from the click ripple: the
    screen moved, and the marker moves with it. It is driven by the eased
    ``progress``, so the chevron travels early and then holds where it landed --
    readable while it is still on screen, rather than sliding the whole time.
    """
    length = (marker.dx**2 + marker.dy**2) ** 0.5
    if length <= 0:
        return
    ux, uy = marker.dx / length, marker.dy / length
    # Perpendicular, for the chevron's two arms.
    px, py = -uy, ux

    drift = progress * 26.0
    tip_x = marker.x + ux * (drift + 14.0)
    tip_y = marker.y + uy * (drift + 14.0)
    arm = 13.0

    stroke = skia.Paint(AntiAlias=True)
    stroke.setStyle(skia.Paint.kStroke_Style)
    stroke.setStrokeWidth(3.0)
    stroke.setColor(_accent_color(skia, fade))
    for sign in (1.0, -1.0):
        canvas.drawLine(
            tip_x - ux * arm + px * arm * sign,
            tip_y - uy * arm + py * arm * sign,
            tip_x,
            tip_y,
            stroke,
        )


def _paint_captions(
    skia: Any, canvas: Any, captions: list[_Caption], now: float, width: int, height: int
) -> None:
    from nuiitivet.rendering.skia.font import (
        get_default_font_fallbacks,
        get_typeface,
        make_font,
        make_text_blob,
        measure_text_width,
    )

    # Resolve a concrete UI typeface the way the Text widget does. The bare
    # ``make_font(None, ...)`` / ``fallback_to_default`` paths can land on a
    # decorative system face missing common glyphs (e.g. ``+``), so match Text's
    # family candidates for a proper sans-serif face.
    typeface = get_typeface(family_candidates=get_default_font_fallbacks(), fallback_to_default=True)
    font = make_font(typeface, 13.0)
    if font is None:
        return

    pad_x = 10.0
    line_h = 22.0
    gap = 4.0
    margin = 12.0

    # Newest at the bottom; stack upward from the bottom-left corner.
    n = len(captions)
    for i, caption in enumerate(captions):
        text = f"{caption.seq}. {caption.text}"
        age = now - caption.born
        # Hold, then fade over the last ~0.6s of the caption's life.
        remaining = _CAPTION_LIFETIME - age
        alpha = 1.0 if remaining > 0.6 else max(0.0, remaining / 0.6)

        text_w = measure_text_width(typeface, 13.0, text)
        box_w = text_w + pad_x * 2
        box_h = line_h
        # Row 0 is the oldest (top); the last row sits at the bottom margin.
        y_bottom = height - margin - (n - 1 - i) * (box_h + gap)
        y_top = y_bottom - box_h
        x_left = margin

        bg = skia.Paint(AntiAlias=True)
        bg.setColor(skia.Color(20, 18, 30, int(round(alpha * 200))))
        rect = skia.Rect.MakeXYWH(x_left, y_top, box_w, box_h)
        canvas.drawRoundRect(rect, 6.0, 6.0, bg)

        text_paint = skia.Paint(AntiAlias=True)
        text_paint.setColor(skia.Color(235, 232, 245, int(round(alpha * 255))))
        blob = make_text_blob(text, font)
        if blob is not None:
            baseline = y_top + (box_h + 10.0) / 2.0
            canvas.drawTextBlob(blob, x_left + pad_x, baseline, text_paint)
