"""Unit tests for HarnessClock: pump semantics, equality, thread safety."""

import threading
import time

import pytest

from nuiitivet.testing import HarnessClock


def test_zero_delay_fires_under_pump_immediate_only():
    clock = HarnessClock()
    fired = []
    clock.schedule_once(lambda dt: fired.append(("zero", dt)), 0)
    clock.schedule_once(lambda dt: fired.append(("delayed", dt)), 0.3)
    clock.schedule_interval(lambda dt: fired.append(("interval", dt)), 0.05)

    assert clock.pump_immediate() == 1
    assert fired == [("zero", 0.0)]
    # The genuine waits stay armed.
    kinds = {(p.is_interval, p.delay) for p in clock.pending()}
    assert kinds == {(False, 0.3), (True, 0.05)}


def test_pump_fires_only_what_is_due():
    clock = HarnessClock()
    fired = []
    clock.schedule_once(lambda dt: fired.append("short"), 0.01)
    clock.schedule_once(lambda dt: fired.append("long"), 60.0)

    time.sleep(0.02)
    assert clock.pump() == 1
    assert fired == ["short"]
    assert [p.delay for p in clock.pending()] == [60.0]


def test_reentrant_zero_delay_fires_in_same_pump():
    clock = HarnessClock()
    fired = []

    def outer(dt):
        fired.append("outer")
        clock.schedule_once(lambda dt: fired.append("inner"), 0)

    clock.schedule_once(outer, 0)
    assert clock.pump_immediate() == 2
    assert fired == ["outer", "inner"]


def test_schedule_once_twice_arms_twice():
    # pyglet semantics: scheduling the same callback twice fires it twice.
    clock = HarnessClock()
    calls = []
    clock.schedule_once(calls.append, 0)
    clock.schedule_once(calls.append, 0)
    assert clock.pump_immediate() == 2


class _Widget:
    def __init__(self):
        self.calls = 0

    def _emit(self, dt):
        self.calls += 1


def test_unschedule_matches_bound_methods_by_equality():
    clock = HarnessClock()
    widget = _Widget()
    clock.schedule_once(widget._emit, 0)
    assert widget._emit is not widget._emit  # fresh object per access
    clock.unschedule(widget._emit)

    assert clock.pump_immediate() == 0
    assert widget.calls == 0
    assert clock.pending() == []


def test_interval_fires_once_per_elapsed_period():
    clock = HarnessClock()
    dts = []
    clock.schedule_interval(dts.append, 0.01)

    time.sleep(0.035)
    fired = clock.pump()
    assert fired >= 3
    assert all(dt == 0.01 for dt in dts)  # ideal cadence, no drift compensation
    assert not clock.due_now  # caught up


def test_nonpositive_interval_fires_once_per_pump():
    clock = HarnessClock()
    calls = []
    clock.schedule_interval(calls.append, 0)
    assert clock.pump() == 1
    assert clock.pump() == 1


def test_callback_can_unschedule_a_due_callback_during_pump():
    clock = HarnessClock()
    fired = []

    def victim(dt):
        fired.append("victim")

    def killer(dt):
        fired.append("killer")
        clock.unschedule(victim)

    clock.schedule_once(killer, 0)
    clock.schedule_once(victim, 0)
    assert clock.pump_immediate() == 1
    assert fired == ["killer"]


def test_schedule_once_is_thread_safe():
    clock = HarnessClock()
    calls = []

    def worker():
        for _ in range(100):
            clock.schedule_once(calls.append, 0)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert clock.pump_immediate() == 400
    assert len(calls) == 400


def test_pump_raises_on_nonconverging_schedule():
    clock = HarnessClock()

    def again(dt):
        clock.schedule_once(again, 0)

    clock.schedule_once(again, 0)
    with pytest.raises(RuntimeError, match="did not converge"):
        clock.pump_immediate()


def test_due_now_and_next_deadline():
    clock = HarnessClock()
    assert clock.next_deadline is None
    assert not clock.due_now

    clock.schedule_once(lambda dt: None, 60.0)
    remaining = clock.next_deadline
    assert remaining is not None
    assert 0.0 < remaining <= 60.0
    assert not clock.due_now

    clock.schedule_once(lambda dt: None, 0)
    assert clock.due_now
    assert clock.next_deadline == 0.0


def test_cancel_all_reports_due_state_and_clears():
    clock = HarnessClock()
    clock.schedule_once(lambda dt: None, 0)
    clock.schedule_once(lambda dt: None, 60.0)

    dropped = clock.cancel_all()
    assert [cb.due for cb in dropped] == [True, False]
    assert clock.pending() == []
    assert clock.pump() == 0


def test_pending_records_scheduling_site():
    clock = HarnessClock()
    clock.schedule_once(lambda dt: None, 0)
    (cb,) = clock.pending()
    assert "test_harness_clock.py" in cb.site
