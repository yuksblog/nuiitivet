"""Helper to compute container layout sizes and positions."""

import logging
from typing import Dict, Optional, Tuple

from nuiitivet.common.logging_once import exception_once

from ..rendering.sizing import sizing_signature
from .measure import preferred_size as measure_preferred_size


logger = logging.getLogger(__name__)


_CACHE_PROFILE_ENABLED = False
_CACHE_STAT_KEYS = (
    "preferred_hits",
    "preferred_misses",
    "inner_hits",
    "inner_misses",
    "placement_hits",
    "placement_misses",
)
_CACHE_STATS: Dict[str, int] = {key: 0 for key in _CACHE_STAT_KEYS}


def enable_layout_cache_profiling(enabled: bool) -> None:
    """Toggle cache hit/miss tracking for LayoutEngine."""

    global _CACHE_PROFILE_ENABLED
    _CACHE_PROFILE_ENABLED = bool(enabled)


def reset_layout_cache_stats() -> None:
    for key in _CACHE_STATS:
        _CACHE_STATS[key] = 0


def get_layout_cache_stats() -> Dict[str, int]:
    return dict(_CACHE_STATS)


def _record_cache_event(event: str) -> None:
    if _CACHE_PROFILE_ENABLED and event in _CACHE_STATS:
        _CACHE_STATS[event] += 1


class LayoutEngine:
    """Encapsulate padding/border/align based layout calculations for a single-child container.

    This class intentionally keeps no heavy dependencies and operates on
    primitive ints/tuples. The owner (Container) provides configuration
    values (padding tuple, border_width, align).
    """

    def __init__(self, owner) -> None:
        self.owner = owner
        self._pref_cache_key: Optional[Tuple[Tuple[int, int, int, int], int, Optional[int]]] = None
        self._pref_cache_value: Tuple[int, int] = (0, 0)
        self._inner_cache_key: Optional[Tuple[Tuple[int, int, int, int], int, Optional[int]]] = None
        self._inner_cache_value: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self._placement_cache_key: Optional[
            Tuple[
                Tuple[str, str],
                Tuple[str, str],
                int,
                int,
                int,
                int,
                bool,
                bool,
                Optional[int],
                Optional[Tuple[str, float]],
                Optional[Tuple[str, float]],
            ]
        ] = None
        self._placement_cache_value: Tuple[int, int, int, int] = (0, 0, 0, 0)

    def preferred_size(self, child_pref_w: int, child_pref_h: int) -> Tuple[int, int]:
        """Return preferred size including padding and border.

        child_pref_* are expected to be non-negative ints (0 if unknown).
        """
        pad = self._owner_padding()
        bw = self._owner_border()
        key = (pad, bw, self._owner_layout_token())
        if key == self._pref_cache_key:
            extra_w, extra_h = self._pref_cache_value
            _record_cache_event("preferred_hits")
        else:
            extra_w = pad[0] + pad[2] + bw * 2
            extra_h = pad[1] + pad[3] + bw * 2
            self._pref_cache_key = key
            self._pref_cache_value = (extra_w, extra_h)
            _record_cache_event("preferred_misses")
        return (int(child_pref_w or 0) + extra_w, int(child_pref_h or 0) + extra_h)

    def compute_inner_rect(self, x: int, y: int, width: int, height: int) -> Tuple[int, int, int, int]:
        """Compute the inner rectangle (x,y,w,h) reduced by padding and border.

        Returned rect is where child content may be placed; border is drawn
        inside the outer rect so border_width is subtracted from the inside.
        """
        pad = self._owner_padding()
        bw = self._owner_border()
        key = (pad, bw, self._owner_layout_token())
        if key == self._inner_cache_key:
            off_x, off_y, shrink_w, shrink_h = self._inner_cache_value
            _record_cache_event("inner_hits")
        else:
            off_x = pad[0] + bw
            off_y = pad[1] + bw
            shrink_w = pad[0] + pad[2] + bw * 2
            shrink_h = pad[1] + pad[3] + bw * 2
            self._inner_cache_key = key
            self._inner_cache_value = (off_x, off_y, shrink_w, shrink_h)
            _record_cache_event("inner_misses")
        ix = x + off_x
        iy = y + off_y
        iw = max(0, width - shrink_w)
        ih = max(0, height - shrink_h)
        return (ix, iy, iw, ih)

    def compute_child_placement(
        self,
        iw: int,
        ih: int,
        pref_w: int,
        pref_h: int,
        child_align: Optional[Tuple[str, str]] = None,
        *,
        clamp_w: bool = False,
        clamp_h: bool = False,
        child_token: Optional[int] = None,
        width_signature: Optional[Tuple[str, float]] = None,
        height_signature: Optional[Tuple[str, float]] = None,
    ) -> Tuple[int, int, int, int]:
        """Given inner available size and child preferred size, compute child's
        allocated width/height and top-left coords relative to the inner rect.

        Returns (cx_offset, cy_offset, child_w, child_h) where offsets are
        measured from the inner rect origin.
        """
        # choose child size: prefer pref when positive, otherwise fill
        child_w = pref_w if pref_w > 0 else iw
        child_h = pref_h if pref_h > 0 else ih
        if clamp_w:
            child_w = min(child_w, iw)
        if clamp_h:
            child_h = min(child_h, ih)

        norm_child_align = self._normalize_align(child_align)
        owner_align = self._normalize_align(getattr(self.owner, "_align", ("start", "start")))
        key = (
            norm_child_align,
            owner_align,
            iw,
            ih,
            pref_w,
            pref_h,
            clamp_w,
            clamp_h,
            child_token,
            width_signature,
            height_signature,
        )
        if key == self._placement_cache_key:
            off_x, off_y, child_w, child_h = self._placement_cache_value
            _record_cache_event("placement_hits")
            return (off_x, off_y, child_w, child_h)
        else:
            _record_cache_event("placement_misses")

        if norm_child_align != ("", ""):
            h_align, v_align = norm_child_align
        else:
            h_align, v_align = owner_align

        if h_align == "center":
            cx = (iw - child_w) // 2
        elif h_align == "end":
            cx = iw - child_w
        else:
            cx = 0

        if v_align == "center":
            cy = (ih - child_h) // 2
        elif v_align == "end":
            cy = ih - child_h
        else:
            cy = 0
        self._placement_cache_key = key
        self._placement_cache_value = (cx, cy, child_w, child_h)
        return (cx, cy, child_w, child_h)

    def resolve_child_geometry(self, child, ix: int, iy: int, iw: int, ih: int) -> Tuple[int, int, int, int]:
        """Resolve child geometry (x, y, w, h) within the inner rect.

        Handles child's preferred size and flex sizing.
        Returns absolute coordinates (cx, cy, cw, ch).
        """
        pref_w, pref_h = measure_preferred_size(child, max_width=int(iw), max_height=int(ih))

        w_dim = getattr(child, "width_sizing", None)
        clamp_w = True
        if w_dim:
            kind = getattr(w_dim, "kind", None)
            if kind == "flex":
                pref_w = 0
            elif kind == "fixed":
                clamp_w = False
                try:
                    pref_w = max(pref_w, int(w_dim.value))
                except Exception:
                    pref_w = max(pref_w, 0)

        h_dim = getattr(child, "height_sizing", None)
        clamp_h = True
        if h_dim:
            kind = getattr(h_dim, "kind", None)
            if kind == "flex":
                pref_h = 0
            elif kind == "fixed":
                clamp_h = False
                try:
                    pref_h = max(pref_h, int(h_dim.value))
                except Exception:
                    pref_h = max(pref_h, 0)

        # Check for child-specific layout alignment override.
        child_align_raw = getattr(child, "layout_align", None)
        child_align = None
        if child_align_raw:
            if isinstance(child_align_raw, str):
                child_align = (child_align_raw, child_align_raw)
            elif isinstance(child_align_raw, (list, tuple)) and len(child_align_raw) == 2:
                child_align = (str(child_align_raw[0]), str(child_align_raw[1]))

        child_token = getattr(child, "layout_cache_token", None)
        width_signature = sizing_signature(w_dim) if w_dim is not None else None
        height_signature = sizing_signature(h_dim) if h_dim is not None else None

        off_x, off_y, child_w, child_h = self.compute_child_placement(
            iw,
            ih,
            max(0, int(pref_w or 0)),
            max(0, int(pref_h or 0)),
            child_align=child_align,
            clamp_w=clamp_w,
            clamp_h=clamp_h,
            child_token=child_token,
            width_signature=width_signature,
            height_signature=height_signature,
        )
        return (ix + off_x, iy + off_y, child_w, child_h)

    def invalidate_cache(self) -> None:
        self._pref_cache_key = None
        self._inner_cache_key = None
        self._placement_cache_key = None

    def _owner_padding(self) -> Tuple[int, int, int, int]:
        pad = getattr(self.owner, "padding", (0, 0, 0, 0))
        if isinstance(pad, tuple) and len(pad) == 4:
            return (int(pad[0]), int(pad[1]), int(pad[2]), int(pad[3]))
        return (0, 0, 0, 0)

    def _owner_border(self) -> int:
        try:
            return int(getattr(self.owner, "border_width", 0) or 0)
        except Exception:
            exception_once(logger, "layout_engine_owner_border_exc", "Failed to read owner.border_width")
            return 0

    def _owner_layout_token(self) -> Optional[int]:
        owner = self.owner
        if owner is None:
            return None
        return getattr(owner, "layout_cache_token", None)

    @staticmethod
    def _normalize_align(value: Optional[Tuple[str, str]]) -> Tuple[str, str]:
        if not value:
            return ("", "")
        return (str(value[0] or ""), str(value[1] or ""))


__all__ = [
    "LayoutEngine",
    "enable_layout_cache_profiling",
    "reset_layout_cache_stats",
    "get_layout_cache_stats",
]
