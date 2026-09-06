"""What happens when a derivation, a predicate or a subscriber raises.

Neither path is about *expected* failure -- a failed HTTP request is a value the
UI renders, not an exception. These are bugs in application code, and the rule
is that a bug is logged where it happened rather than
thrown at whichever thread happened to trigger the recompute.

The clock matters here, so these tests pump the ``HarnessClock`` the testing
plugin installs. Its ``pump`` does **not** swallow exceptions, which is what
makes it a usable stand-in for the real fallback clock's servicing thread:
anything escaping into a clock callback fails the test instead of vanishing into
a worker.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import List, Optional

import pytest

from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests
from nuiitivet.observable import Observable
from nuiitivet.observable.protocols import mark_internal_subscription
from nuiitivet.testing import HarnessClock


_COMPUTED_LOGGER = "nuiitivet.observable.computed"
_FILTERED_LOGGER = "nuiitivet.observable.filtered"
_SCANNED_LOGGER = "nuiitivet.observable.scanned"
_VALUE_LOGGER = "nuiitivet.observable.value"
_WRAPPER_LOGGER = "nuiitivet.observable.wrapper"

_DERIVATION_FAILED = "Computed function raised; keeping the previous value"
_PRED_FAILED = "filter predicate raised; the value was treated as not passing"
_FOLD_FAILED = "scan function raised; the accumulator was left unchanged"

# Long enough that the debounce window is genuinely elapsed when the test pumps,
# short enough to keep the file fast. HarnessClock uses real time, not virtual.
_WINDOW = 0.01


@pytest.fixture(autouse=True)
def _fresh_log_keys():
    """Let every test see its own first occurrence of a de-duplicated log line."""
    _clear_log_once_keys_for_tests()
    yield
    _clear_log_once_keys_for_tests()


def _records(caplog: pytest.LogCaptureFixture, name: str) -> List[logging.LogRecord]:
    """Records from one logger. ``caplog.at_level(logger=...)`` only sets a level."""
    return [r for r in caplog.records if r.name == name]


def _boom(value: str) -> str:
    """A derivation with the shape the issue describes: fine until it is not."""
    if value == "boom":
        raise ValueError("derivation is broken")
    return value.upper()


class TestRaisingDerivation:
    """A raising ``fn`` is logged, keeps the previous value, and escapes nowhere."""

    def test_worker_thread_write_does_not_escape_into_the_clock_callback(
        self, nuiitivet_clock: HarnessClock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The marshalled write's recompute happens inside ``pump``, and stays there.

        A write from a worker is deferred to the clock, so the derivation runs
        on the clock's callback -- which has no handler for the application's
        bug. Before the fix, ``pump()`` raised.
        """
        source: Observable[str] = Observable("ok")
        derived = source.map(_boom)
        assert derived.value == "OK"

        worker = threading.Thread(target=lambda: setattr(source, "value", "boom"))
        worker.start()
        worker.join()

        with caplog.at_level(logging.ERROR, logger=_COMPUTED_LOGGER):
            nuiitivet_clock.pump()

        assert derived.value == "OK", "the previous value must survive a failed recompute"
        assert [r.message for r in _records(caplog, _COMPUTED_LOGGER)] == [_DERIVATION_FAILED]

    def test_debounce_timer_does_not_escape_into_the_clock_callback(
        self, nuiitivet_clock: HarnessClock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Same for a derivation a ``debounce`` timer drives."""
        source: Observable[str] = Observable("ok")
        derived = source.debounce(_WINDOW).map(_boom)
        assert derived.value == "OK"

        source.value = "boom"
        time.sleep(_WINDOW * 2)

        with caplog.at_level(logging.ERROR, logger=_COMPUTED_LOGGER):
            nuiitivet_clock.pump()

        assert derived.value == "OK"
        assert [r.message for r in _records(caplog, _COMPUTED_LOGGER)] == [_DERIVATION_FAILED]

    def test_ui_thread_write_does_not_reach_the_caller(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Even with a real caller on the stack, the bug goes to the log, not to them.

        The setter is not a handler for a derivation three operators downstream,
        and making it one would mean every write site has to guard every
        derivation reachable from it.
        """
        source: Observable[str] = Observable("ok")
        derived = source.map(_boom)

        with caplog.at_level(logging.ERROR, logger=_COMPUTED_LOGGER):
            source.value = "boom"  # must not raise

        assert derived.value == "OK"
        assert [r.message for r in _records(caplog, _COMPUTED_LOGGER)] == [_DERIVATION_FAILED]

    def test_construction_time_failure_is_logged_not_raised(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """One rule, not two: a derivation never propagates, whenever it runs.

        Raising here would surface on the caller's own thread, which is more
        useful in isolation -- but it makes the *first* broken value an
        exception and every later one a log line, and it lets a ``map`` built
        during a widget's build take the whole tree down with it.
        """
        source: Observable[str] = Observable("boom")

        with caplog.at_level(logging.ERROR, logger=_COMPUTED_LOGGER):
            derived = source.map(_boom)  # must not raise

        assert derived.value is None, "no previous value to keep"
        assert [r.message for r in _records(caplog, _COMPUTED_LOGGER)] == [_DERIVATION_FAILED]

    def test_derivation_recovers_once_the_source_is_fixed(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A failed run re-arms its dependency edges, so the next change retries.

        The edges are torn down *before* the run. Leaving them down because it
        raised would make the observable permanently deaf -- logged once, then
        silently frozen for the rest of the process.
        """
        source: Observable[str] = Observable("ok")
        derived = source.map(_boom)

        seen: List[Optional[str]] = []
        derived.subscribe(seen.append)

        with caplog.at_level(logging.ERROR, logger=_COMPUTED_LOGGER):
            source.value = "boom"
            assert derived.value == "OK"
            source.value = "fine"

        assert derived.value == "FINE"
        assert seen == ["FINE"], "the failed recompute must not emit a value"

    def test_combine_compute_is_covered_too(self, caplog: pytest.LogCaptureFixture) -> None:
        """``combine(...).compute(fn)`` is the same ``ComputedObservable``."""
        left: Observable[int] = Observable(1)
        right: Observable[int] = Observable(2)
        total = left.combine(right).compute(lambda a, b: a // b)

        with caplog.at_level(logging.ERROR, logger=_COMPUTED_LOGGER):
            right.value = 0  # ZeroDivisionError inside the derivation

        assert total.value == 0, "1 // 2 == 0, kept from before the failure"
        assert [r.message for r in _records(caplog, _COMPUTED_LOGGER)] == [_DERIVATION_FAILED]


class TestRaisingFilterPredicate:
    """``filter``'s ``pred`` runs on the graph's own edge, so it guards itself."""

    def test_raising_pred_treats_the_value_as_not_passing(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        source: Observable[Optional[int]] = Observable(2)
        positive = source.filter(lambda n: n > 0, initial=0)  # type: ignore[operator]
        assert positive.value == 2

        with caplog.at_level(logging.ERROR, logger=_FILTERED_LOGGER):
            source.value = None  # TypeError inside the predicate

        assert positive.value == 2, "the last value that passed is kept"
        assert [r.message for r in _records(caplog, _FILTERED_LOGGER)] == [_PRED_FAILED]

    def test_filter_recovers_once_the_source_is_fixed(self) -> None:
        source: Observable[Optional[int]] = Observable(2)
        positive = source.filter(lambda n: n > 0, initial=0)  # type: ignore[operator]

        source.value = None
        source.value = 5

        assert positive.value == 5


class TestRaisingScanFunction:
    """``scan``'s ``fn`` runs on the same edge as ``filter``'s ``pred``, and guards itself."""

    def test_raising_fn_leaves_the_accumulator_alone(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        source: Observable[Optional[int]] = Observable(2)
        total = source.scan(lambda acc, n: acc + n, initial=0)  # type: ignore[operator]

        source.value = 3
        assert total.value == 3

        with caplog.at_level(logging.ERROR, logger=_SCANNED_LOGGER):
            source.value = None  # TypeError inside the fold

        assert total.value == 3, "the accumulator moved on a fold that never completed"
        assert [r.message for r in _records(caplog, _SCANNED_LOGGER)] == [_FOLD_FAILED]

    def test_scan_recovers_once_the_source_is_fixed(self) -> None:
        source: Observable[Optional[int]] = Observable(2)
        total = source.scan(lambda acc, n: acc + n, initial=0)  # type: ignore[operator]

        source.value = 3
        source.value = None
        source.value = 4

        assert total.value == 7


class _Thrower:
    """A subscriber that always raises, and counts how often it was called."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, value: object) -> None:
        self.calls += 1
        raise RuntimeError("subscriber is broken")


class TestThrowingSubscriber:
    """One broken subscriber must not silence the ones registered after it."""

    def test_observable_notifies_past_a_thrower(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        source: Observable[int] = Observable(0)
        thrower = _Thrower()
        seen: List[int] = []

        source.subscribe(thrower)
        source.subscribe(seen.append)

        with caplog.at_level(logging.ERROR, logger=_VALUE_LOGGER):
            source.value = 1

        assert thrower.calls == 1
        assert seen == [1]
        assert len(_records(caplog, _VALUE_LOGGER)) == 1

    def test_computed_notifies_past_a_thrower(self, caplog: pytest.LogCaptureFixture) -> None:
        source: Observable[int] = Observable(0)
        doubled = source.map(lambda n: n * 2)
        thrower = _Thrower()
        seen: List[int] = []

        doubled.subscribe(thrower)
        doubled.subscribe(seen.append)

        with caplog.at_level(logging.ERROR, logger=_COMPUTED_LOGGER):
            source.value = 3

        assert thrower.calls == 1
        assert seen == [6]

    def test_computed_notifies_past_a_thrower_on_the_dispatched_path(
        self, nuiitivet_clock: HarnessClock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The marshalled notify loop is a second copy, and needs the same guard."""
        source: Observable[int] = Observable(0)
        doubled = source.map(lambda n: n * 2)
        thrower = _Thrower()
        seen: List[int] = []

        doubled.subscribe(thrower)
        doubled.subscribe(seen.append)

        worker = threading.Thread(target=lambda: setattr(source, "value", 3))
        worker.start()
        worker.join()

        with caplog.at_level(logging.ERROR, logger=_COMPUTED_LOGGER):
            nuiitivet_clock.pump()

        assert thrower.calls == 1
        assert seen == [6]

    def test_wrapper_notifies_past_a_thrower(self, caplog: pytest.LogCaptureFixture) -> None:
        """Covers every operator on the wrapper base: filter, debounce, throttle."""
        source: Observable[int] = Observable(0)
        positive = source.filter(lambda n: n > 0, initial=0)
        thrower = _Thrower()
        seen: List[int] = []

        positive.subscribe(thrower)
        positive.subscribe(seen.append)

        with caplog.at_level(logging.ERROR, logger=_WRAPPER_LOGGER):
            source.value = 7

        assert thrower.calls == 1
        assert seen == [7]

    def test_a_throwing_subscriber_does_not_stop_later_emissions(self) -> None:
        source: Observable[int] = Observable(0)
        thrower = _Thrower()
        seen: List[int] = []

        source.subscribe(thrower)
        source.subscribe(seen.append)

        source.value = 1
        source.value = 2

        assert thrower.calls == 2
        assert seen == [1, 2]

    def test_a_write_back_from_one_subscriber_reaches_the_next(self) -> None:
        """The guard must not turn the emission into a snapshot of one value.

        A subscriber that normalizes what it was handed writes back during the
        loop, and the subscribers after it are handed what that write left --
        the behaviour ``EditableText``'s external-write path depends on.
        """
        source: Observable[str] = Observable("")
        seen: List[str] = []

        source.subscribe(lambda text: setattr(source, "value", text.upper()))
        source.subscribe(seen.append)

        source.value = "ab"

        assert source.value == "AB"
        assert seen[-1] == "AB"


class TestInternalEdgesStillPropagate:
    """The graph's own subscriptions are exempt: their failures are the framework's."""

    def test_an_internal_subscription_is_not_swallowed(self) -> None:
        """Swallowing one would turn a loud framework guard into a silent one.

        The batch queue's infinite-loop detector raises through exactly this
        path (``tests/observable/test_observable_batch.py``), so a blanket guard
        on the notify loop would make a runaway dependency cycle invisible.
        """
        source: Observable[int] = Observable(0)

        def internal_edge(_value: int) -> None:
            raise RuntimeError("framework invariant broken")

        source.subscribe(mark_internal_subscription(internal_edge))

        with pytest.raises(RuntimeError, match="framework invariant broken"):
            source.value = 1
