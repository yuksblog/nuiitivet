import threading
import pytest
from unittest.mock import patch

from nuiitivet.observable import Observable
from nuiitivet.runtime import threading as nv_threading
from nuiitivet.runtime.threading import assert_ui_thread, is_ui_thread, set_ui_thread


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


def test_is_ui_thread_is_the_main_thread_by_default():
    assert is_ui_thread() is True

    seen = []
    t = threading.Thread(target=lambda: seen.append(is_ui_thread()))
    t.start()
    t.join()

    assert seen == [False]


def test_set_ui_thread_moves_the_answer():
    """The backend registers the thread that runs its frame loop."""
    worker_ident = []

    def worker():
        set_ui_thread()
        worker_ident.append(threading.get_ident())

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    try:
        assert nv_threading._ui_thread_ident == worker_ident[0]
        assert is_ui_thread() is False  # the main thread is no longer it
        with pytest.raises(RuntimeError, match="must be run on the UI thread"):
            assert_ui_thread()
    finally:
        set_ui_thread(threading.main_thread().ident)

    assert is_ui_thread() is True


def test_reset_after_fork_reseats_the_main_thread():
    """A forked child re-seats its main thread, so the cached ident goes stale."""
    set_ui_thread(-1)
    try:
        assert is_ui_thread() is False
        nv_threading._reset_after_fork()
        assert is_ui_thread() is True
    finally:
        set_ui_thread(threading.main_thread().ident)


def test_observable_coalescing(mock_clock):
    class State:
        value = Observable(0)

    s = State()

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
    """The *computed* coalesces when its source hands it every write inline.

    The source opts out, so a worker's writes apply immediately on the worker
    and reach ``_on_dep`` there, one per write. Only the computed marshals, and
    it is the computed's own coalescing that turns five notifications into one
    scheduled flush. Leaving the source dispatching would coalesce the writes
    *before* the computed ever saw them and prove nothing about this path.
    """

    class State:
        source = Observable(0, dispatch=False)

    state = State()

    computed = state.source.map(lambda v: v * 2)
    assert computed._dispatch_to_ui is False, "map inherits the source's opt-out"
    # This test is about the computed's marshalling, so put it back on just it.
    computed._dispatch_to_ui = True

    updates = []
    computed.subscribe(lambda v: updates.append(v))

    def worker():
        for i in range(1, 6):
            state.source = i

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    # Five notifications in, one scheduled flush out.
    assert len(mock_clock.events) == 1

    mock_clock.flush()

    assert updates == [10]
