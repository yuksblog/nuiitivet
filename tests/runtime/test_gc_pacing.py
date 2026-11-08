import gc
import weakref

import pytest

from nuiitivet.runtime.gc_pacing import GcPacer


class _Cycle:
    """An object only the collector can free."""

    def __init__(self) -> None:
        self.me = self


def _cycles(count: int) -> list:
    return [weakref.ref(_Cycle()) for _ in range(count)]


def _alive(refs: list) -> int:
    return sum(1 for ref in refs if ref() is not None)


@pytest.fixture
def collector():
    """A clean collector before the test, the process default after it."""
    thresholds = gc.get_threshold()
    gc.collect()
    yield
    gc.set_threshold(*thresholds)
    gc.enable()
    gc.collect()


def test_install_disables_the_collector_and_uninstall_restores_it(collector):
    pacer = GcPacer()
    assert gc.isenabled()

    pacer.install()
    assert not gc.isenabled()
    assert pacer.installed

    pacer.uninstall()
    assert gc.isenabled()
    assert not pacer.installed


def test_nothing_runs_while_not_installed(collector):
    pacer = GcPacer()
    refs = _cycles(2000)

    pacer.before_frame()
    assert pacer.idle(0.0) is None
    assert gc.isenabled()
    # Enabled, the collector itself may already have freed them; the pacer did not disable it.
    del refs


def test_no_collection_runs_inside_a_frame(collector):
    pacer = GcPacer()
    pacer.install()
    try:
        pacer.before_frame()
        refs = _cycles(2000)  # past the default threshold of 700
        assert _alive(refs) == 2000, "the collector stayed out of the frame"
        pacer.after_frame(0.0)
        pacer.idle(0.0)
        assert _alive(refs) == 0, "the wait after the frame collected them"
    finally:
        pacer.uninstall()


def test_idle_leaves_a_young_generation_under_its_threshold_alone(collector):
    pacer = GcPacer()
    pacer.install()
    try:
        refs = _cycles(100)
        pacer.idle(0.0)
        assert _alive(refs) == 100
    finally:
        pacer.uninstall()


def test_before_frame_collects_only_past_the_backstop(collector):
    pacer = GcPacer(young_backstop=5000)
    pacer.install()
    try:
        few = _cycles(500)  # a cycle and its weakref are two tracked allocations
        pacer.before_frame()
        assert _alive(few) == 500

        many = _cycles(3000)
        pacer.before_frame()
        assert _alive(few) == 0
        assert _alive(many) == 0
    finally:
        pacer.uninstall()


def _promote_to_the_old_generation(pacer: GcPacer, obj: object) -> None:
    """Two idle calls carry a live object through the young and middle generations."""
    for _ in range(2):
        _cycles(5)
        pacer.idle(0.0)


def test_a_due_full_collection_waits_for_a_quiet_moment(collector):
    gc.set_threshold(1, 1, 1)
    pacer = GcPacer(middle_budget=0, old_budget=10**9, quiet_seconds=1.0, freeze=False)
    pacer.install()
    try:
        pacer.after_frame(0.0)
        old = _Cycle()
        ref = weakref.ref(old)
        _promote_to_the_old_generation(pacer, old)
        del old
        assert ref() is not None, "an old-generation cycle survives the young and middle collections"

        assert pacer.idle(0.5) == pytest.approx(0.5), "a full collection is due, half a second from quiet"
        assert ref() is not None

        assert pacer.idle(1.0) is None
        assert ref() is None, "the quiet moment collected the whole heap"
    finally:
        pacer.uninstall()


def test_the_old_budget_forces_a_full_collection_before_quiet(collector):
    gc.set_threshold(1, 1, 1)
    pacer = GcPacer(middle_budget=0, old_budget=0, quiet_seconds=1.0, freeze=False)
    pacer.install()
    try:
        pacer.after_frame(0.0)
        old = _Cycle()
        ref = weakref.ref(old)
        _cycles(5)
        pacer.idle(0.0)
        del old
        _cycles(5)
        pacer.idle(0.0)
        assert ref() is None, "the old generation grew past its budget, so the collection did not wait"
    finally:
        pacer.uninstall()


def test_the_heap_is_frozen_at_the_first_wait_after_the_first_frame(collector):
    pacer = GcPacer()
    pacer.install()
    try:
        garbage = _cycles(1000)
        kept = _Cycle()
        pacer.idle(0.0)
        assert gc.get_freeze_count() == 0, "no frame yet, nothing frozen"
        pacer.after_frame(0.0)
        pacer.idle(0.0)
        assert gc.get_freeze_count() > 0
        assert _alive(garbage) == 0, "the first frame's garbage went before the freeze"
        frozen = gc.get_freeze_count()
        del kept
        pacer.idle(0.5)
        assert gc.get_freeze_count() == frozen, "a frozen object is not looked at by the young collections"
    finally:
        pacer.uninstall()
    assert gc.get_freeze_count() == 0, "uninstall thaws the heap"


def test_a_frozen_object_is_reclaimed_by_the_quiet_collection_only(collector):
    gc.set_threshold(1, 1, 1)
    pacer = GcPacer(middle_budget=0, old_budget=10**9, quiet_seconds=1.0)
    pacer.install()
    try:
        kept = _Cycle()
        ref = weakref.ref(kept)
        pacer.after_frame(0.0)
        pacer.idle(0.0)  # freezes the heap, kept inside it
        del kept
        for _ in range(3):
            _cycles(5)
            pacer.idle(0.0)  # the young and middle collections never see the frozen heap
        assert ref() is not None

        pacer.idle(1.0)
        assert ref() is None, "the quiet collection thawed, collected and froze again"
        assert gc.get_freeze_count() > 0
    finally:
        pacer.uninstall()


def test_a_forced_full_collection_skips_the_frozen_heap(collector):
    gc.set_threshold(1, 1, 1)
    pacer = GcPacer(middle_budget=0, old_budget=0, quiet_seconds=1.0)
    pacer.install()
    try:
        kept = _Cycle()
        kept_ref = weakref.ref(kept)
        pacer.after_frame(0.0)
        pacer.idle(0.0)  # freezes the heap, kept inside it
        del kept

        fresh = _Cycle()
        fresh_ref = weakref.ref(fresh)
        _promote_to_the_old_generation(pacer, fresh)
        del fresh
        for _ in range(2):
            _cycles(5)
            pacer.idle(0.0)
        assert fresh_ref() is None, "the old generation passed its budget, so a full collection ran before quiet"
        assert kept_ref() is not None, "the frozen heap waits for the quiet collection"
    finally:
        pacer.uninstall()
