"""The lifetime contract for observables that subscribe to a source.

``debounce`` / ``throttle`` stay subscribed upstream for as long as they live.
These tests pin the two halves of the contract: the source must not keep the
wrapper alive, and teardown must release the source and disarm the clock.
"""

import gc
import weakref

import pytest

from nuiitivet.observable import Observable
from nuiitivet.observable.computed import ComputedObservable
from nuiitivet.observable.timed import DebouncedObservable, ThrottledObservable


class MockClock:
    """Records armed callbacks so a test can assert on them and fire them."""

    def __init__(self):
        self.scheduled = []

    def schedule_once(self, fn, delay):
        self.scheduled.append(fn)

    def unschedule(self, fn):
        self.scheduled = [f for f in self.scheduled if f != fn]

    def fire_all(self):
        due, self.scheduled = self.scheduled, []
        for fn in due:
            fn(0)


@pytest.fixture
def mock_clock(monkeypatch):
    clock = MockClock()
    import nuiitivet.observable.runtime as runtime

    monkeypatch.setattr(runtime, "clock", clock)
    return clock


def _wrappers(source):
    """Both wrapper flavours, so each test covers the contract in one pass."""
    return [source.debounce(0.3), source.throttle(0.3)]


class TestSourceDoesNotOwnTheWrapper:
    """The subscription must point weakly, or the chain can never be collected."""

    @pytest.mark.parametrize("factory", [DebouncedObservable, ThrottledObservable])
    def test_the_callback_on_the_source_holds_no_strong_reference(self, mock_clock, factory):
        """The structural half of the contract, independent of when the GC runs."""
        source = Observable(0)
        wrapper = factory(source, 0.3)

        (registered,) = source._subs
        held = [cell.cell_contents for cell in registered.__closure__ or ()]

        assert held, "the callback must capture something — a weakref to the wrapper"
        assert all(isinstance(value, weakref.ref) for value in held)
        assert wrapper not in held

    @pytest.mark.parametrize("factory", [DebouncedObservable, ThrottledObservable])
    def test_dropping_the_wrapper_releases_the_source(self, mock_clock, collectable, factory):
        source = Observable(0)
        wrapper = factory(source, 0.3)
        ref = weakref.ref(wrapper)
        assert len(source._subs) == 1

        del wrapper
        gc.collect()

        assert ref() is None
        assert source._subs == []

    def test_source_outliving_the_wrapper_does_not_pin_it(self, mock_clock, collectable):
        """The leak this contract exists to prevent, stated directly."""
        source = Observable(0)
        refs = [weakref.ref(w) for w in _wrappers(source)]
        gc.collect()

        # Nothing holds the wrappers; only the source ever referenced them.
        assert all(ref() is None for ref in refs)
        assert source._subs == []


class TestSubscribeCarriesTheLifetime:
    """Holding the Disposable holds the chain — the framework's bind() shape."""

    def test_disposable_keeps_the_chain_alive(self, mock_clock, collectable):
        source = Observable(0)
        seen = []

        # The wrapper itself is never bound to a name, exactly as `self.bind(...)`
        # would leave it.
        disposable = source.debounce(0.3).subscribe(seen.append)
        gc.collect()

        source.value = 1
        mock_clock.fire_all()
        assert seen == [1]

        disposable.dispose()
        del disposable
        gc.collect()
        assert source._subs == []

    def test_dropping_the_disposable_drops_the_chain(self, mock_clock, collectable):
        """A derived observable nobody holds does not exist — same as `compute`."""
        source = Observable(0)
        source.debounce(0.3).subscribe(lambda v: None)
        gc.collect()

        assert source._subs == []


class TestDispose:
    @pytest.mark.parametrize("factory", [DebouncedObservable, ThrottledObservable])
    def test_releases_the_source_subscription(self, mock_clock, factory):
        source = Observable(0)
        wrapper = factory(source, 0.3)

        wrapper.dispose()

        assert source._subs == []

    @pytest.mark.parametrize("factory", [DebouncedObservable, ThrottledObservable])
    def test_is_idempotent(self, mock_clock, factory):
        source = Observable(0)
        wrapper = factory(source, 0.3)

        wrapper.dispose()
        wrapper.dispose()

        assert source._subs == []

    @pytest.mark.parametrize("factory", [DebouncedObservable, ThrottledObservable])
    def test_stops_emission(self, mock_clock, factory):
        source = Observable(0)
        wrapper = factory(source, 0.3)
        seen = []
        wrapper.subscribe(seen.append)

        wrapper.dispose()
        source.value = 1
        mock_clock.fire_all()

        assert seen == []

    def test_disarms_a_pending_debounce_timer(self, mock_clock):
        source = Observable(0)
        wrapper = source.debounce(0.3)
        seen = []
        wrapper.subscribe(seen.append)

        source.value = 1
        assert len(mock_clock.scheduled) == 1

        wrapper.dispose()

        assert mock_clock.scheduled == []
        mock_clock.fire_all()
        assert seen == []

    def test_disarms_a_pending_throttle_timer(self, mock_clock):
        source = Observable(0)
        wrapper = source.throttle(0.3)
        seen = []
        wrapper.subscribe(seen.append)

        source.value = 1  # leading edge emits and arms the trailing timer
        assert seen == [1]
        assert len(mock_clock.scheduled) == 1

        source.value = 2  # queued for the trailing edge
        wrapper.dispose()

        assert mock_clock.scheduled == []
        mock_clock.fire_all()
        assert seen == [1]

    @pytest.mark.parametrize("factory", [DebouncedObservable, ThrottledObservable])
    def test_runs_from_del_as_a_backstop(self, mock_clock, collectable, factory):
        source = Observable(0)
        wrapper = factory(source, 0.3)
        assert len(source._subs) == 1

        del wrapper
        gc.collect()

        assert source._subs == []

    @pytest.mark.parametrize("factory", [DebouncedObservable, ThrottledObservable])
    def test_an_armed_timer_keeps_the_wrapper_alive_until_it_fires(
        self, mock_clock, collectable, factory
    ):
        """A pending emit completes rather than vanishing mid-flight.

        The clock holds the armed callback, which is a bound method, so a wrapper
        with work outstanding survives being dropped — deliberately. It becomes
        collectable once that work is done.
        """
        source = Observable(0)
        wrapper = factory(source, 0.3)
        ref = weakref.ref(wrapper)
        source.value = 1
        assert len(mock_clock.scheduled) == 1

        del wrapper
        gc.collect()
        assert ref() is not None, "an armed timer must not be dropped mid-flight"

        mock_clock.fire_all()
        gc.collect()

        assert ref() is None
        assert source._subs == []


class TestDerivationsDependOnTheWrapper:
    """A derivation must see the shaped notifications, not the raw source."""

    def test_map_over_debounce_is_debounced(self, mock_clock):
        """Regression: the derivation used to subscribe past the wrapper."""
        source = Observable(0)
        derived = source.debounce(0.3).map(lambda x: x * 2)
        seen = []
        derived.subscribe(seen.append)

        source.value = 5
        assert seen == [], "map recomputed on the source, bypassing the debounce"

        mock_clock.fire_all()
        assert seen == [10]

    def test_map_over_throttle_follows_the_throttle(self, mock_clock):
        source = Observable(0)
        derived = source.throttle(0.3).map(lambda x: x * 2)
        seen = []
        derived.subscribe(seen.append)

        source.value = 5  # leading edge passes straight through
        assert seen == [10]

        source.value = 7  # inside the window: held back
        assert seen == [10]

        mock_clock.fire_all()
        assert seen == [10, 14]

    def test_value_holds_the_last_emission(self, mock_clock):
        """Shaping applies to reads too: `.value` is what the wrapper emitted."""
        source = Observable(1)
        debounced = source.debounce(0.3)

        assert debounced.value == 1  # seeded from the source
        source.value = 2
        assert debounced.value == 1, "`.value` read through, bypassing the debounce"

        mock_clock.fire_all()
        assert debounced.value == 2

    def test_seeding_does_not_leak_into_an_enclosing_derivation(self, mock_clock):
        """Building a wrapper inside a compute must not register its source."""
        source = Observable(1)
        other = Observable(10)
        wrappers = []

        def build() -> int:
            wrappers.append(source.debounce(0.3))
            return other.value

        derived = ComputedObservable(build)
        seen = []
        derived.subscribe(seen.append)

        source.value = 2
        mock_clock.fire_all()
        assert seen == [], "the seed read registered the source as a dependency"

        other.value = 20
        assert seen == [20]


class TestDisposableReleasesItsClosure:
    """Disposing must free the subscriber and the chain, not just unhook them."""

    def test_disposing_releases_the_chain_while_still_held(self, mock_clock, collectable):
        source = Observable(0)
        disposable = source.debounce(0.3).subscribe(lambda v: None)

        disposable.dispose()
        gc.collect()

        # The Disposable is still referenced here, exactly as a widget's bind()
        # list holds it after unmount.
        assert source._subs == []

    def test_disposing_releases_the_subscriber(self, mock_clock, collectable):
        class Subscriber:
            def on_value(self, value):
                pass

        source = Observable(0)
        subscriber = Subscriber()
        ref = weakref.ref(subscriber)
        disposable = source.subscribe(subscriber.on_value)

        disposable.dispose()
        del subscriber
        gc.collect()

        assert ref() is None
        assert disposable.is_disposed

    def test_dispose_stays_idempotent(self, mock_clock):
        source = Observable(0)
        seen = []
        disposable = source.subscribe(seen.append)

        disposable.dispose()
        disposable.dispose()

        source.value = 1
        assert seen == []


class TestLeakCheckExemption:
    """The graph's own edges must not be reported as an app's leaked subscription."""

    def test_wrapper_and_computed_edges_are_internal(self, mock_clock):
        from nuiitivet.testing._leaks import track_subscriptions, _classify

        source = Observable(0)
        with track_subscriptions() as registry:
            debounced = source.debounce(0.3)
            throttled = source.throttle(0.3)
            computed = source.map(lambda x: x * 2)

            kinds = [_classify(record)[0] for record in registry.records]

        assert kinds == ["internal", "internal", "internal"]
        # Keep the chain alive to the assertion, so nothing above is collected
        # mid-test and quietly removes the record being classified.
        assert (debounced, throttled, computed) is not None
