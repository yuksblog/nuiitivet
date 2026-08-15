"""``switch_map(fn, initial=...)`` — ``map`` for a function that takes time.

The property worth the machinery is that **the newest run wins regardless of
what order runs finish in**. So the runs here are gated: each one blocks inside
``fn`` until the test releases it, which lets a test land an older run *after* a
newer one and assert the older one is thrown away. ``GatedRuns.finish`` joins the
run's worker before returning, so by the time the clock is ticked the run has
either staged its result or been rejected — no test here sleeps or races.
"""

import gc
import logging
import threading
import weakref

import pytest

from nuiitivet.observable import Observable
from nuiitivet.observable.switched import CancelToken, SwitchMappedObservable


_TIMEOUT = 5.0


class MockClock:
    """Mock clock, with the lock the observable-only clocks do not need.

    ``switch_map`` schedules from its worker threads, so unlike ``debounce`` and
    ``throttle`` it can have two threads inside ``schedule_once`` at once.
    """

    def __init__(self):
        self.scheduled = []
        self.current_time = 0.0
        self._lock = threading.Lock()

    def schedule_once(self, fn, delay):
        with self._lock:
            self.scheduled.append((self.current_time + delay, fn))
            self.scheduled.sort(key=lambda entry: entry[0])

    def unschedule(self, fn):
        with self._lock:
            self.scheduled = [(t, f) for t, f in self.scheduled if f != fn]

    def tick(self, delta=0.0):
        with self._lock:
            self.current_time += delta
            due = [(t, f) for t, f in self.scheduled if t <= self.current_time + 1e-9]
            self.scheduled = [(t, f) for t, f in self.scheduled if t > self.current_time + 1e-9]
        for _, fn in due:
            fn(0)


@pytest.fixture
def mock_clock(monkeypatch):
    clock = MockClock()

    import nuiitivet.observable.runtime as runtime

    monkeypatch.setattr(runtime, "clock", clock)

    return clock


def _default_result(value):
    return f"result:{value}"


class GatedRuns:
    """A ``switch_map`` function whose runs finish only when the test says so.

    ``finish`` releases one run *and joins its worker*, which is what makes the
    ordering assertions exact: ``_deliver`` runs inside the worker, so a joined
    worker has either staged its result or been rejected as superseded, with
    nothing left in flight to arrive later and confuse the next assertion.
    """

    def __init__(self, result=_default_result):
        self._result = result
        self._lock = threading.Lock()
        self._release = {}
        self._started = {}
        self._threads = {}
        self.calls = []
        self.thread_idents = []
        self.tokens = {}

    def _gates(self, value):
        with self._lock:
            return (
                self._release.setdefault(value, threading.Event()),
                self._started.setdefault(value, threading.Event()),
            )

    def __call__(self, value, cancel: CancelToken):
        release, started = self._gates(value)
        with self._lock:
            self.calls.append(value)
            self.thread_idents.append(threading.get_ident())
            self.tokens[value] = cancel
            self._threads[value] = threading.current_thread()
        started.set()
        assert release.wait(timeout=_TIMEOUT), f"run {value!r} was never released"
        return self._result(value)

    def wait_started(self, value):
        _, started = self._gates(value)
        assert started.wait(timeout=_TIMEOUT), f"run {value!r} never started"

    def finish(self, value):
        """Release run ``value`` and wait for it to be done delivering."""
        release, _ = self._gates(value)
        release.set()
        with self._lock:
            thread = self._threads.get(value)
        if thread is not None:
            thread.join(_TIMEOUT)
            assert not thread.is_alive(), f"run {value!r} did not finish"


def _join_ungated_workers():
    """Wait out runs that nothing is holding, for tests that use no gates."""
    for thread in threading.enumerate():
        if thread.name.startswith("switch_map:"):
            thread.join(_TIMEOUT)
            assert not thread.is_alive(), "a switch_map worker did not finish"


class TestTheSeed:
    def test_reports_initial_before_any_run_lands(self):
        source = Observable("")

        results = source.switch_map(lambda value, cancel: value.upper(), initial="<none>")

        assert results.value == "<none>"

    def test_no_run_starts_at_construction(self):
        """Unlike ``filter``, building this must not fire work off."""
        source = Observable("already here")
        runs = GatedRuns()

        results = source.switch_map(runs, initial="")  # noqa: F841

        assert runs.calls == []

    def test_initial_is_required(self):
        source = Observable("")

        with pytest.raises(TypeError):
            source.switch_map(lambda value, cancel: value)  # type: ignore[call-arg]

    def test_initial_is_keyword_only(self):
        source = Observable("")

        with pytest.raises(TypeError):
            source.switch_map(lambda value, cancel: value, "")  # type: ignore[misc]


class TestPublishing:
    def test_a_completed_run_becomes_the_value(self, mock_clock):
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="<none>")

        source.value = "one"
        runs.wait_started("one")
        runs.finish("one")
        mock_clock.tick()

        assert results.value == "result:one"

    def test_subscribers_see_the_result(self, mock_clock):
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="<none>")
        seen = []
        results.subscribe(seen.append)

        source.value = "one"
        runs.wait_started("one")
        runs.finish("one")
        mock_clock.tick()

        assert seen == ["result:one"]

    def test_nothing_is_published_before_the_run_completes(self, mock_clock):
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="<none>")

        source.value = "one"
        runs.wait_started("one")
        mock_clock.tick()

        assert results.value == "<none>"

        runs.finish("one")


class TestSuperseding:
    def test_an_older_run_finishing_last_does_not_win(self, mock_clock):
        """The acceptance criterion: out-of-order completion, newest still wins."""
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="<none>")

        source.value = "one"
        runs.wait_started("one")
        source.value = "two"
        runs.wait_started("two")

        runs.finish("two")
        mock_clock.tick()
        assert results.value == "result:two"

        # The superseded run lands afterwards and must change nothing.
        runs.finish("one")
        mock_clock.tick()
        assert results.value == "result:two"

    def test_a_superseded_run_never_reaches_subscribers(self, mock_clock):
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="<none>")
        seen = []
        results.subscribe(seen.append)

        source.value = "one"
        runs.wait_started("one")
        source.value = "two"
        runs.wait_started("two")

        runs.finish("one")  # the superseded run finishes first this time
        mock_clock.tick()
        assert seen == []

        runs.finish("two")
        mock_clock.tick()
        assert seen == ["result:two"]

    def test_a_result_returned_from_except_is_still_discarded(self, mock_clock):
        """A superseded run's ``except`` path is a result like any other.

        This is the shape ``switch_map`` asks apps to write — catch, and return
        the failure as a value — so it has to obey superseding like a success.
        """

        def recovered(value):
            try:
                raise RuntimeError("boom")
            except RuntimeError:
                return f"recovered:{value}"

        source = Observable("")
        runs = GatedRuns(result=recovered)
        results = source.switch_map(runs, initial="<none>")
        seen = []
        results.subscribe(seen.append)

        source.value = "one"
        runs.wait_started("one")
        source.value = "two"
        runs.wait_started("two")

        runs.finish("one")
        mock_clock.tick()
        assert seen == []

        runs.finish("two")
        mock_clock.tick()
        assert seen == ["recovered:two"]

    def test_the_token_reports_supersession(self, mock_clock):
        source = Observable("")
        runs = GatedRuns()
        # Held: an operator nobody holds is collected, §5.
        results = source.switch_map(runs, initial="")  # noqa: F841

        source.value = "one"
        runs.wait_started("one")
        assert runs.tokens["one"].superseded is False

        source.value = "two"
        runs.wait_started("two")

        assert runs.tokens["one"].superseded is True
        assert runs.tokens["two"].superseded is False

        runs.finish("one")
        runs.finish("two")
        mock_clock.tick()


class TestThreading:
    def test_fn_does_not_run_on_the_ui_thread(self, mock_clock):
        source = Observable("")
        runs = GatedRuns()
        # Held: an operator nobody holds is collected, §5.
        results = source.switch_map(runs, initial="")  # noqa: F841

        source.value = "one"
        runs.wait_started("one")
        runs.finish("one")
        mock_clock.tick()

        assert len(runs.thread_idents) == 1
        assert runs.thread_idents[0] != threading.get_ident()

    def test_subscribers_run_on_the_ui_thread(self, mock_clock):
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="")
        notified_on = []
        results.subscribe(lambda value: notified_on.append(threading.get_ident()))

        source.value = "one"
        runs.wait_started("one")
        runs.finish("one")
        mock_clock.tick()

        assert notified_on == [threading.get_ident()]


class TestARaisingFunction:
    def test_publishes_nothing_and_logs(self, mock_clock, caplog):
        def raises_on_purpose(value, cancel):
            raise RuntimeError("fn is broken")

        source = Observable("")
        results = source.switch_map(raises_on_purpose, initial="<none>")
        seen = []
        results.subscribe(seen.append)

        with caplog.at_level(logging.ERROR, logger="nuiitivet.observable.switched"):
            source.value = "one"
            _join_ungated_workers()
            mock_clock.tick()

        assert seen == []
        assert results.value == "<none>"
        assert "raised" in caplog.text

    def test_does_not_escape_onto_the_worker(self, mock_clock):
        """An unhandled exception in a thread is printed, not raised — so assert
        the worker exits cleanly rather than that nothing was raised."""

        def raises_on_purpose(value, cancel):
            raise RuntimeError("fn is broken")

        source = Observable("")
        source.switch_map(raises_on_purpose, initial="")

        source.value = "one"
        _join_ungated_workers()  # asserts every worker exited cleanly
        mock_clock.tick()


class TestLifetime:
    def test_dispose_supersedes_the_run_in_flight(self, mock_clock):
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="<none>")
        seen = []
        results.subscribe(seen.append)

        source.value = "one"
        runs.wait_started("one")
        results.dispose()

        assert runs.tokens["one"].superseded is True

        runs.finish("one")
        mock_clock.tick()
        assert seen == []
        assert results.value == "<none>"

    def test_dispose_is_idempotent(self):
        source = Observable("")
        results = source.switch_map(lambda value, cancel: value, initial="")

        results.dispose()
        results.dispose()

    def test_dispose_releases_the_source_subscription(self):
        source = Observable("")
        results = source.switch_map(lambda value, cancel: value, initial="")

        assert len(source._subs) == 1
        results.dispose()
        assert source._subs == []

    def test_a_dropped_wrapper_is_collectable(self, collectable):
        source = Observable("")
        results = source.switch_map(lambda value, cancel: value, initial="")
        ref = weakref.ref(results)

        del results
        gc.collect()

        assert ref() is None
        assert source._subs == []


class TestChaining:
    def test_the_result_is_a_plain_observable(self, mock_clock):
        """No wrapper type in the value position: ``map`` chains straight off it."""
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="<none>")
        shouted = results.map(str.upper)

        source.value = "one"
        runs.wait_started("one")
        runs.finish("one")
        mock_clock.tick()

        assert shouted.value == "RESULT:ONE"

    def test_it_reads_only_value(self):
        """The surface stays ``.value`` — failure is a value, not a channel."""
        source = Observable("")
        results = source.switch_map(lambda value, cancel: value, initial="")

        assert not hasattr(results, "error")

    def test_it_chains_off_another_wrapper(self, mock_clock):
        """``debounce(...).switch_map(...)`` — the idiom the docs teach."""
        source = Observable("")
        runs = GatedRuns()
        results = source.debounce(0.3).switch_map(runs, initial="<none>")

        assert isinstance(results, SwitchMappedObservable)

        source.value = "one"
        mock_clock.tick(0.3)  # the debounce settles, only now does a run start
        runs.wait_started("one")
        runs.finish("one")
        mock_clock.tick()

        assert results.value == "result:one"

    def test_it_chains_into_a_filter(self, mock_clock):
        """The operators the wrapper base gained: a chain does not dead-end."""
        source = Observable("")
        runs = GatedRuns()
        results = source.switch_map(runs, initial="<none>")
        succeeded = results.filter(lambda text: text.startswith("result:"), initial="")

        source.value = "one"
        runs.wait_started("one")
        runs.finish("one")
        mock_clock.tick()

        assert succeeded.value == "result:one"
