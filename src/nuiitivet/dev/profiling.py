"""Dev-session rebuild/repaint counters and painted-frame timing.

Start/stop model, like a DevTools performance recording: a
:class:`ProfilingSession` accumulates, between :func:`start` and
:func:`stop`:

- per-widget paint-call counts (installed by wrapping each widget class's
  ``paint`` for the duration of the session),
- per-host scope-recomposition counts and per-widget binding-update counts
  (via the probe hooks in :mod:`nuiitivet.widgeting.widget_builder` and
  :mod:`nuiitivet.widgeting.widget_binding`),
- the duration of each painted frame's tree walk (recorded by the render
  path while a session is active).

Counters are cumulative for the life of the session; there is no reset or
``seq`` — the session boundary is the reset. Nothing is installed outside a
session, so apps pay no cost beyond a per-frame ``None`` check on the render
path. Measured on a 1000-row full-repaint stress app, an active session
inflates frame time by roughly 10%.

Limitations: widget classes imported *after* :func:`start` are not wrapped
and their paints go uncounted; every painted frame walks the whole tree, so
paint counts are per painted frame, not per damaged region.
"""

from __future__ import annotations

import time
import weakref
from typing import Any, Dict, Iterator, List, Optional, Tuple

from nuiitivet.widgeting import widget_binding, widget_builder
from nuiitivet.widgeting.widget_kernel import WidgetKernel

_PAINT_WRAPPER_ATTR = "__nuiitivet_profiling_wrapper__"

_active: Optional["ProfilingSession"] = None


def active_session() -> Optional["ProfilingSession"]:
    """Return the currently active session, or ``None``."""
    return _active


class ProfilingSession:
    """Counter store for one profiling run.

    Counters are keyed by ``id(widget)``; :meth:`report` resolves keys to
    widget metadata via weak references kept alongside the counts.
    """

    def __init__(self) -> None:
        self.paint_counts: Dict[int, int] = {}
        self.rebuild_counts: Dict[int, int] = {}
        self.binding_counts: Dict[int, int] = {}
        self.frame_durations: List[float] = []
        self._registry: Dict[int, Tuple[str, Optional[str], "weakref.ref[Any]"]] = {}
        self._started = time.perf_counter()

    def register(self, key: int, obj: Any) -> None:
        """Remember *obj*'s identity for report-time resolution."""
        try:
            ref = weakref.ref(obj)
        except TypeError:
            return
        widget_key = getattr(obj, "key", None)
        self._registry[key] = (type(obj).__name__, widget_key if isinstance(widget_key, str) else None, ref)

    def record_frame(self, duration: float) -> None:
        """Record one painted frame's tree-walk duration in seconds."""
        self.frame_durations.append(duration)

    def report(self) -> Dict[str, Any]:
        """Summarize the session.

        Returns::

            {
                "duration_s": wall seconds the session has been active,
                "frames": {"painted", "mean_ms", "p95_ms", "max_ms"} or None,
                "paints": [{"widget", "instances", "paints"}, ...],   # by type
                "rebuilds": [{"widget", "key", "alive", "count"}, ...],  # by host
                "bindings": [{"widget", "key", "alive", "count"}, ...],  # by widget
            }

        ``paints`` aggregates by widget type (individual widgets all repaint
        together on this render path); ``rebuilds`` and ``bindings`` stay
        per-widget because those are the sparse, actionable signals.
        """
        durations = self.frame_durations
        frames: Optional[Dict[str, Any]] = None
        if durations:
            ordered = sorted(d * 1000.0 for d in durations)
            frames = {
                "painted": len(ordered),
                "mean_ms": round(sum(ordered) / len(ordered), 3),
                "p95_ms": round(ordered[max(0, int(len(ordered) * 0.95) - 1)], 3),
                "max_ms": round(ordered[-1], 3),
            }

        by_type: Dict[str, Dict[str, int]] = {}
        for key, count in self.paint_counts.items():
            name = self._name_of(key)
            entry = by_type.setdefault(name, {"instances": 0, "paints": 0})
            entry["instances"] += 1
            entry["paints"] += count
        paints: List[Dict[str, Any]] = [
            {"widget": name, "instances": entry["instances"], "paints": entry["paints"]}
            for name, entry in by_type.items()
        ]
        paints.sort(key=lambda row: row["paints"], reverse=True)

        return {
            "duration_s": round(time.perf_counter() - self._started, 3),
            "frames": frames,
            "paints": paints,
            "rebuilds": self._per_widget_rows(self.rebuild_counts),
            "bindings": self._per_widget_rows(self.binding_counts),
        }

    def _name_of(self, key: int) -> str:
        entry = self._registry.get(key)
        return entry[0] if entry is not None else "<unknown>"

    def _per_widget_rows(self, counts: Dict[int, int]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for key, count in counts.items():
            entry = self._registry.get(key)
            if entry is None:
                rows.append({"widget": "<unknown>", "key": None, "alive": False, "count": count})
            else:
                rows.append(
                    {"widget": entry[0], "key": entry[1], "alive": entry[2]() is not None, "count": count}
                )
        rows.sort(key=lambda row: row["count"], reverse=True)
        return rows


def start() -> ProfilingSession:
    """Activate profiling; return the (possibly already active) session."""
    global _active
    if _active is not None:
        return _active
    session = ProfilingSession()
    _install_paint_wrappers()
    widget_builder.set_recomposition_probe(_on_recomposition)
    widget_binding.set_binding_probe(_on_binding)
    _active = session
    return session


def stop() -> Optional[ProfilingSession]:
    """Deactivate profiling and return the finished session, if any."""
    global _active
    session = _active
    _active = None
    widget_builder.set_recomposition_probe(None)
    widget_binding.set_binding_probe(None)
    _uninstall_paint_wrappers()
    return session


def _on_recomposition(host: Any, scope_count: int) -> None:
    session = _active
    if session is None:
        return
    _bump(session, session.rebuild_counts, host, scope_count)


def _on_binding(widget: Any) -> None:
    session = _active
    if session is None:
        return
    _bump(session, session.binding_counts, widget, 1)


def _bump(session: ProfilingSession, counts: Dict[int, int], obj: Any, amount: int) -> None:
    key = id(obj)
    n = counts.get(key)
    if n is None:
        counts[key] = amount
        session.register(key, obj)
    else:
        counts[key] = n + amount


def _iter_widget_classes() -> Iterator[type]:
    seen: set[type] = set()
    stack: List[type] = [WidgetKernel]
    while stack:
        cls = stack.pop()
        if cls in seen:
            continue
        seen.add(cls)
        yield cls
        stack.extend(cls.__subclasses__())


def _make_paint_wrapper(orig: Any) -> Any:
    def paint(self: Any, *args: Any, **kwargs: Any) -> Any:
        # Count only in the wrapper the MRO actually dispatches to, so a
        # subclass paint that calls super().paint() is not counted twice.
        session = _active
        if session is not None and getattr(type(self), "paint", None) is paint:
            key = id(self)
            counts = session.paint_counts
            n = counts.get(key)
            if n is None:
                counts[key] = 1
                session.register(key, self)
            else:
                counts[key] = n + 1
        return orig(self, *args, **kwargs)

    paint.__wrapped__ = orig  # type: ignore[attr-defined]
    setattr(paint, _PAINT_WRAPPER_ATTR, True)
    return paint


def _install_paint_wrappers() -> None:
    for cls in _iter_widget_classes():
        orig = cls.__dict__.get("paint")
        if orig is None or getattr(orig, _PAINT_WRAPPER_ATTR, False):
            continue
        setattr(cls, "paint", _make_paint_wrapper(orig))


def _uninstall_paint_wrappers() -> None:
    for cls in _iter_widget_classes():
        fn = cls.__dict__.get("paint")
        if fn is not None and getattr(fn, _PAINT_WRAPPER_ATTR, False):
            setattr(cls, "paint", fn.__wrapped__)
