import threading
import pytest
from unittest.mock import patch

from nuiitivet.observable import Observable
from nuiitivet.runtime.threading import assert_ui_thread


class MockClock:
    def __init__(self):
        self.events = []

    def schedule_once(self, func, dt, *args, **kwargs):
        self.events.append((func, args, kwargs))

    def flush(self):
        current_events = self.events[:]
        self.events.clear()
        for func, args, kwargs in current_events:
            func(0, *args, **kwargs)


@pytest.fixture
def mock_clock():
    clock = MockClock()
    # Patch where it is referenced at runtime
    with patch("nuiitivet.observable.runtime.clock") as runtime_clock:
        runtime_clock.schedule_once = clock.schedule_once
        yield clock


def test_assert_ui_thread_raises_on_worker_thread():
    def worker():
        with pytest.raises(RuntimeError, match="must be run on the UI thread"):
            assert_ui_thread()

    t = threading.Thread(target=worker)
    t.start()
    t.join()


def test_assert_ui_thread_passes_on_main_thread():
    assert_ui_thread()  # Should not raise


def test_observable_coalescing(mock_clock):
    class State:
        value = Observable(0)

    s = State()
    s.value.dispatch_to_ui()

    updates = []
    s.value.subscribe(lambda v: updates.append(v))

    def worker():
        # Simulate rapid updates
        for i in range(1, 6):
            s.value = i

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    # At this point, updates should be empty because they are scheduled
    assert updates == []
    # Only one scheduled event due to coalescing
    assert len(mock_clock.events) == 1

    # Flush events
    mock_clock.flush()

    # Should have only the last value
    assert updates == [5]
    assert s.value.value == 5


def test_computed_observable_coalescing_direct_source(mock_clock):
    class State:
        source = Observable(0)

    state = State()
    # source does NOT dispatch. Updates immediately.

    computed = state.source.map(lambda v: v * 2).dispatch_to_ui()

    updates = []
    computed.subscribe(lambda v: updates.append(v))

    def worker():
        for i in range(1, 6):
            state.source = i
            # source updates immediately.
            # computed._on_dep called immediately on worker thread.
            # computed schedules update on UI thread.

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    # Computed should have scheduled updates.
    # Due to coalescing, should be only one schedule.
    assert len(mock_clock.events) == 1

    mock_clock.flush()

    assert updates == [10]
