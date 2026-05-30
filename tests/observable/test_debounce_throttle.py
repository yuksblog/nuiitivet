"""Tests for debounce and throttle observables."""

import pytest
from nuiitivet.observable import Observable


class Model:
    """Test model with observables."""

    source = Observable(0)
    source2 = Observable(10)
    price = Observable(100)
    qty = Observable(1)
    count = Observable(0)


class MockClock:
    """Mock pyglet clock for testing timing-based observables."""

    def __init__(self):
        self.scheduled = []
        self.current_time = 0.0

    def schedule_once(self, fn, delay):
        """Schedule a function to run after delay."""
        self.scheduled.append((self.current_time + delay, fn))
        self.scheduled.sort(key=lambda x: x[0])

    def unschedule(self, fn):
        """Unschedule a function."""
        self.scheduled = [(t, f) for t, f in self.scheduled if f != fn]

    def tick(self, delta):
        """Advance time and run scheduled functions."""
        self.current_time += delta
        to_run = []
        remaining = []

        for schedule_time, fn in self.scheduled:
            # Use epsilon for floating point comparison
            if schedule_time <= self.current_time + 1e-9:
                to_run.append((schedule_time, fn))
            else:
                remaining.append((schedule_time, fn))

        self.scheduled = remaining

        for _, fn in to_run:
            fn(0)  # pyglet passes dt parameter


@pytest.fixture
def mock_clock(monkeypatch):
    """Provide a mock clock for testing."""
    clock = MockClock()

    import nuiitivet.observable.runtime as runtime

    monkeypatch.setattr(runtime, "clock", clock)

    return clock


class TestDebounce:
    """Test debounce functionality."""

    def test_debounce_basic(self, mock_clock):
        """Debounce waits for delay after last change."""
        m = Model()
        debounced = m.source.debounce(0.3)

        results = []
        debounced.subscribe(lambda v: results.append(v))

        # Change multiple times
        m.source.value = 1
        m.source.value = 2
        m.source.value = 3

        # Nothing emitted yet
        assert results == []

        # Advance time by 0.3 seconds
        mock_clock.tick(0.3)

        # Should emit last value
        assert results == [3]

    def test_debounce_cancels_previous(self, mock_clock):
        """Debounce cancels previous scheduled emission."""
        m = Model()
        debounced = m.source.debounce(0.3)

        results = []
        debounced.subscribe(lambda v: results.append(v))

        # First change
        m.source.value = 1
        mock_clock.tick(0.1)  # 0.1s passed

        # Second change (should cancel first)
        m.source.value = 2
        mock_clock.tick(0.1)  # 0.2s passed total

        # Third change (should cancel second)
        m.source.value = 3
        mock_clock.tick(0.3)  # 0.5s passed total

        # Only last value should be emitted
        assert results == [3]

    def test_debounce_multiple_emissions(self, mock_clock):
        """Debounce can emit multiple times if enough time passes."""
        m = Model()
        debounced = m.source.debounce(0.3)

        results = []
        debounced.subscribe(lambda v: results.append(v))

        # First change
        m.source.value = 1
        mock_clock.tick(0.3)
        assert results == [1]

        # Second change after debounce period
        m.source.value = 2
        mock_clock.tick(0.3)
        assert results == [1, 2]

    def test_debounce_value_property(self):
        """Debounce.value returns current source value (not debounced)."""
        m = Model()
        debounced = m.source2.debounce(0.3)

        assert debounced.value == 10

        m.source2.value = 20
        assert debounced.value == 20  # Not debounced

    def test_debounce_map_chain(self, mock_clock):
        """Debounce can be chained with map."""
        m = Model()
        debounced_doubled = m.source.debounce(0.3).map(lambda x: x * 2)

        results = []
        debounced_doubled.subscribe(lambda v: results.append(v))

        m.source.value = 5
        mock_clock.tick(0.3)

        assert results == [10]

    def test_debounce_dispatch_to_ui(self, mock_clock):
        """Debounce supports dispatch_to_ui()."""
        m = Model()
        debounced = m.source.debounce(0.3).dispatch_to_ui()

        assert debounced._dispatch_to_ui is True


class TestThrottle:
    """Test throttle functionality."""

    def test_throttle_basic(self, mock_clock):
        """Throttle emits first value immediately, then ignores for duration."""
        m = Model()
        throttled = m.source.throttle(0.3)

        results = []
        throttled.subscribe(lambda v: results.append(v))

        # First change - emitted immediately
        m.source.value = 1
        assert results == [1]

        # Changes during throttle period - ignored
        m.source.value = 2
        m.source.value = 3
        assert results == [1]

        # After throttle period, pending value is emitted
        mock_clock.tick(0.3)
        assert results == [1, 3]

    def test_throttle_immediate_first_emission(self):
        """Throttle emits first value without delay."""
        m = Model()
        throttled = m.source.throttle(0.3)

        results = []
        throttled.subscribe(lambda v: results.append(v))

        m.source.value = 1
        assert results == [1]  # Immediate

    def test_throttle_samples_at_intervals(self, mock_clock):
        """Throttle samples values at regular intervals."""
        m = Model()
        throttled = m.source.throttle(0.1)

        results = []
        throttled.subscribe(lambda v: results.append(v))

        # t=0: emit 1 immediately (schedule callback for t=0.1)
        m.source.value = 1
        assert results == [1]

        # t=0.05: value=2 stored as pending
        mock_clock.tick(0.05)
        m.source.value = 2
        assert results == [1]

        # t=0.1 (0.05 + 0.05): scheduled callback runs, emit pending 2, schedule next for t=0.2
        mock_clock.tick(0.05)
        assert results == [1, 2]

        # t=0.15 (0.1 + 0.05): value=3 stored as pending
        mock_clock.tick(0.05)
        m.source.value = 3
        assert results == [1, 2]

        # t=0.2 (0.15 + 0.05): scheduled callback runs, emit pending 3, schedule next for t=0.3
        mock_clock.tick(0.05)
        assert results == [1, 2, 3]

        # t=0.25 (0.2 + 0.05): value=4 stored as pending
        mock_clock.tick(0.05)
        m.source.value = 4
        assert results == [1, 2, 3]

        # t=0.3 (0.25 + 0.05): scheduled callback runs, emit pending 4
        mock_clock.tick(0.05)
        assert results == [1, 2, 3, 4]

    def test_throttle_value_property(self):
        """Throttle.value returns current source value (not throttled)."""
        m = Model()
        throttled = m.source2.throttle(0.3)

        assert throttled.value == 10

        m.source2.value = 20
        assert throttled.value == 20  # Not throttled

    def test_throttle_map_chain(self, mock_clock):
        """Throttle can be chained with map."""
        m = Model()
        throttled_doubled = m.source.throttle(0.3).map(lambda x: x * 2)

        results = []
        throttled_doubled.subscribe(lambda v: results.append(v))

        m.source.value = 5
        assert results == [10]  # Immediate

    def test_throttle_dispatch_to_ui(self):
        """Throttle supports dispatch_to_ui()."""
        m = Model()
        throttled = m.source.throttle(0.3).dispatch_to_ui()

        assert throttled._dispatch_to_ui is True


class TestDebounceThrottleComparison:
    """Compare debounce and throttle behaviors."""

    def test_debounce_vs_throttle_timing(self, mock_clock):
        """Demonstrate timing difference between debounce and throttle."""
        m = Model()
        debounced = m.source.debounce(0.3)
        throttled = m.source.throttle(0.3)

        debounce_results = []
        throttle_results = []

        debounced.subscribe(lambda v: debounce_results.append((round(mock_clock.current_time, 2), v)))
        throttled.subscribe(lambda v: throttle_results.append((round(mock_clock.current_time, 2), v)))

        # t=0: Set value
        m.source.value = 1
        assert throttle_results == [(0.0, 1)]  # Throttle emits immediately
        assert debounce_results == []  # Debounce waits

        # t=0.1: Set value
        mock_clock.tick(0.1)
        m.source.value = 2
        assert throttle_results == [(0.0, 1)]  # Still throttled
        assert debounce_results == []  # Timer reset

        # t=0.3 (0.1 + 0.2): Throttle scheduled callback runs (0.3s after t=0)
        mock_clock.tick(0.2)
        assert throttle_results == [(0.0, 1), (0.3, 2)]
        # Debounce still waiting (0.3s since last change at t=0.1 is t=0.4)
        assert debounce_results == []

        # t=0.4 (0.3 + 0.1): Debounce emits (0.3s after last change at t=0.1)
        mock_clock.tick(0.1)
        assert debounce_results == [(0.4, 2)]


class TestWithComputed:
    """Test debounce/throttle with computed observables."""

    def test_computed_debounce(self, mock_clock):
        """Debounce works with computed observables."""
        m = Model()

        total = m.price.combine(m.qty).compute(lambda p, q: p * q)
        debounced_total = total.debounce(0.3)

        results = []
        debounced_total.subscribe(lambda v: results.append(v))

        m.price.value = 200
        m.qty.value = 2

        assert results == []
        mock_clock.tick(0.3)
        assert results == [400]

    def test_computed_throttle(self, mock_clock):
        """Throttle works with computed observables."""
        m = Model()
        doubled = m.count.map(lambda x: x * 2)
        throttled = doubled.throttle(0.1)

        results = []
        throttled.subscribe(lambda v: results.append(v))

        m.count.value = 1  # Immediate: 2
        assert results == [2]

        m.count.value = 2  # Throttled
        m.count.value = 3  # Throttled
        assert results == [2]

        mock_clock.tick(0.1)  # Emit pending: 6
        assert results == [2, 6]
