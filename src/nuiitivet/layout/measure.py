from __future__ import annotations

from typing import List, Optional, Tuple

from ..widgeting.widget_kernel import WidgetKernel

# One remembered measurement: (max_width, max_height, width, height).
_CacheEntry = Tuple[Optional[int], Optional[int], int, int]

# A widget is typically measured under only a handful of distinct constraints
# per pass (its parent's measure and arrange constraints); a short list keeps
# lookup cheap while covering them all.
_MAX_CACHE_ENTRIES = 8


def _axis_reusable(cached: Optional[int], requested: Optional[int], result: int) -> bool:
    """Whether a measurement cached under ``cached`` answers ``requested``.

    Beyond an exact constraint match, a measurement may be reused when the
    constraint *shrinks* but the measured result still fits: greedy layout
    (text wrapping, min/max clamping) produces the same result for any
    constraint in ``[result, cached]``. A *growing* constraint may unlock a
    larger layout (e.g. wrapped text un-wraps), so it always re-measures.
    ``None`` means unconstrained and behaves as an infinite constraint.
    """
    if cached == requested:
        return True
    if requested is None:
        # Unconstrained query: a constrained measurement may have been
        # clamped or wrapped, so it cannot stand in for the natural size.
        return False
    if cached is not None and requested > cached:
        return False
    return result <= requested


def _cache_lookup(
    entries: List[_CacheEntry],
    max_width: Optional[int],
    max_height: Optional[int],
) -> Optional[Tuple[int, int]]:
    for mw, mh, w, h in entries:
        if _axis_reusable(mw, max_width, w) and _axis_reusable(mh, max_height, h):
            return (w, h)
    return None


def _cache_store(
    widget: WidgetKernel,
    max_width: Optional[int],
    max_height: Optional[int],
    size: Tuple[int, int],
) -> None:
    try:
        w, h = size
    except Exception:
        return
    if not isinstance(w, (int, float)) or not isinstance(h, (int, float)):
        return
    entries = widget._measure_cache
    if entries is None:
        entries = []
        widget._measure_cache = entries
    entry: _CacheEntry = (max_width, max_height, w, h)
    for i, existing in enumerate(entries):
        if existing[0] == max_width and existing[1] == max_height:
            entries[i] = entry
            if i:
                entries.insert(0, entries.pop(i))
            return
    entries.insert(0, entry)
    del entries[_MAX_CACHE_ENTRIES:]


def preferred_size(
    widget,
    *,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    default: Tuple[int, int] = (0, 0),
) -> Tuple[int, int]:
    """Return widget's preferred size, optionally within constraints.

    Results are memoized per widget, keyed on the constraints; the cache is
    dropped by ``mark_needs_layout()``, so any change that routes through the
    normal layout-invalidation path re-measures. This makes re-measuring an
    unchanged subtree under unchanged (or compatibly shrunk — see
    ``_axis_reusable``) constraints O(1) instead of a full subtree walk.

    This function tolerates legacy implementations that still define
    preferred_size(self) with no constraint parameters.
    """

    fn = getattr(widget, "preferred_size", None)
    if fn is None:
        return default

    # Only WidgetKernel subclasses clear ``_measure_cache`` from
    # ``mark_needs_layout``; caching on anything else could never invalidate.
    cacheable = isinstance(widget, WidgetKernel)
    if cacheable:
        entries = widget._measure_cache
        if entries:
            hit = _cache_lookup(entries, max_width, max_height)
            if hit is not None:
                return hit

    try:
        result = fn(max_width=max_width, max_height=max_height)
    except TypeError as e:
        msg = str(e)
        if "unexpected keyword argument" in msg:
            try:
                result = fn()
            except Exception:
                return default
            if cacheable:
                # A constraint-blind measure is by definition unconstrained.
                _cache_store(widget, None, None, result)
            return result
        return default
    except Exception:
        return default

    if cacheable:
        _cache_store(widget, max_width, max_height, result)
    return result
