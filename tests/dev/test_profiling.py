"""Tests for the dev profiling session: wrappers, probes, counters, report."""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from nuiitivet.dev import profiling
from nuiitivet.observable import Observable
from nuiitivet.widgeting import widget_binding, widget_builder
from nuiitivet.widgeting.widget_kernel import WidgetKernel


class _Leaf(WidgetKernel):
    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        pass


class _Chained(WidgetKernel):
    """Overrides paint and chains to the base, the double-count hazard."""

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        super().paint(canvas, x, y, width, height)


class _Host:
    """Weakref-able recomposition host."""

    def __init__(self) -> None:
        self.processed: list[set] = []

    def _process_scope_recompositions(self, scopes: set) -> None:
        self.processed.append(scopes)


class _Bindable(widget_binding.BindingHostMixin):
    """Weakref-able binding host."""

    def invalidate(self) -> None:
        pass


@pytest.fixture
def profiled() -> Iterator[profiling.ProfilingSession]:
    session = profiling.start()
    try:
        yield session
    finally:
        profiling.stop()


def test_start_installs_wrappers_and_stop_restores() -> None:
    original = _Leaf.__dict__["paint"]
    session = profiling.start()
    try:
        assert profiling.active_session() is session
        assert getattr(_Leaf.__dict__["paint"], "__wrapped__", None) is original
    finally:
        assert profiling.stop() is session
    assert _Leaf.__dict__["paint"] is original
    assert profiling.active_session() is None


def test_start_is_idempotent(profiled: profiling.ProfilingSession) -> None:
    assert profiling.start() is profiled
    # A second start must not wrap the wrapper.
    assert not getattr(_Leaf.__dict__["paint"].__wrapped__, "__nuiitivet_profiling_wrapper__", False)


def test_paint_counts_per_widget(profiled: profiling.ProfilingSession) -> None:
    a, b = _Leaf(), _Leaf()
    for _ in range(3):
        a.paint(None, 0, 0, 10, 10)
    b.paint(None, 0, 0, 10, 10)
    assert profiled.paint_counts[id(a)] == 3
    assert profiled.paint_counts[id(b)] == 1


def test_super_paint_chain_counts_once(profiled: profiling.ProfilingSession) -> None:
    widget = _Chained()
    widget.paint(None, 0, 0, 10, 10)
    assert profiled.paint_counts[id(widget)] == 1


def test_recomposition_probe_counts_flushed_scopes(profiled: profiling.ProfilingSession) -> None:
    host = _Host()
    widget_builder._queue_scope_recomposition(host, "s1")  # type: ignore[arg-type]
    widget_builder._queue_scope_recomposition(host, "s2")  # type: ignore[arg-type]
    widget_builder.flush_scope_recompositions()
    assert profiled.rebuild_counts[id(host)] == 2
    assert len(host.processed) == 1


def test_binding_probe_counts_observe_updates(profiled: profiling.ProfilingSession) -> None:
    obs = Observable(0)
    widget = _Bindable()
    widget.observe(obs, lambda _v: None)
    # The mount-time initial apply is not an update and must not count.
    assert id(widget) not in profiled.binding_counts
    obs.value = 1
    obs.value = 2
    assert profiled.binding_counts[id(widget)] == 2


def test_binding_probe_counts_bind_to_updates(profiled: profiling.ProfilingSession) -> None:
    obs = Observable(0)
    widget = _Bindable()
    widget.bind_to(obs, lambda _v: None, dependency="text")
    assert id(widget) not in profiled.binding_counts
    obs.value = 1
    assert profiled.binding_counts[id(widget)] == 1


def test_nothing_counts_outside_a_session() -> None:
    session = profiling.start()
    profiling.stop()

    _Leaf().paint(None, 0, 0, 10, 10)
    host = _Host()
    widget_builder._queue_scope_recomposition(host, "s1")  # type: ignore[arg-type]
    widget_builder.flush_scope_recompositions()
    obs = Observable(0)
    widget = _Bindable()
    widget.observe(obs, lambda _v: None)
    obs.value = 1

    assert session.paint_counts == {}
    assert session.rebuild_counts == {}
    assert session.binding_counts == {}


def test_report_aggregates_paints_by_type(profiled: profiling.ProfilingSession) -> None:
    a, b = _Leaf(), _Leaf()
    a.paint(None, 0, 0, 10, 10)
    a.paint(None, 0, 0, 10, 10)
    b.paint(None, 0, 0, 10, 10)
    report = profiled.report()
    assert report["frames"] is None
    row = next(r for r in report["paints"] if r["widget"] == "_Leaf")
    assert row["instances"] == 2
    assert row["paints"] == 3


def test_report_frames_and_per_widget_rows(profiled: profiling.ProfilingSession) -> None:
    profiled.record_frame(0.010)
    profiled.record_frame(0.020)
    host = _Host()
    widget_builder._queue_scope_recomposition(host, "s1")  # type: ignore[arg-type]
    widget_builder.flush_scope_recompositions()

    report = profiled.report()
    assert report["frames"]["painted"] == 2
    assert report["frames"]["mean_ms"] == 15.0
    assert report["frames"]["max_ms"] == 20.0
    assert report["duration_s"] >= 0
    (row,) = report["rebuilds"]
    assert row["widget"] == "_Host"
    assert row["alive"] is True
    assert row["count"] == 1
    assert report["bindings"] == []


def test_report_marks_dead_widgets(profiled: profiling.ProfilingSession) -> None:
    host: Any = _Host()
    widget_builder._queue_scope_recomposition(host, "s1")  # type: ignore[arg-type]
    widget_builder.flush_scope_recompositions()
    del host
    (row,) = profiled.report()["rebuilds"]
    assert row["alive"] is False
