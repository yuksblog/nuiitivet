"""Test Observable Phase 1: combine() and CombineBuilder"""

from nuiitivet.observable import Observable, combine


def test_combine_basic():
    """Test basic combine functionality"""

    class State:
        x = Observable(1)
        y = Observable(2)

    state = State()

    # Combine two observables
    sum_obs = state.x.combine(state.y).compute(lambda x, y: x + y)
    assert sum_obs.value == 3

    # Change x
    state.x.value = 10
    assert sum_obs.value == 12

    # Change y
    state.y.value = 20
    assert sum_obs.value == 30


def test_combine_function():
    """Test combine() function"""

    class State:
        x = Observable(1)
        y = Observable(2)
        z = Observable(3)

    state = State()

    # Use combine function
    sum_obs = combine(state.x, state.y, state.z).compute(lambda x, y, z: x + y + z)
    assert sum_obs.value == 6

    state.x.value = 10
    assert sum_obs.value == 15


def test_combine_dispatch_ui():
    """Test combine with dispatch_to_ui"""

    class State:
        x = Observable(1)
        y = Observable(2)

    state = State()

    # Combine with dispatch_to_ui
    sum_obs = state.x.combine(state.y).dispatch_to_ui().compute(lambda x, y: x + y)
    assert sum_obs.value == 3
    assert sum_obs._dispatch_to_ui is True

    state.x.value = 10
    assert sum_obs.value == 12


def test_combine_subscription():
    """Test combine with subscription"""

    class State:
        x = Observable(1)
        y = Observable(2)

    state = State()

    sum_obs = state.x.combine(state.y).compute(lambda x, y: x + y)

    # Subscribe
    calls = []

    def callback(v):
        calls.append(v)

    sum_obs.subscribe(callback)

    # Change x
    state.x.value = 10
    assert calls == [12]

    # Change y
    state.y.value = 20
    assert calls == [12, 30]


def test_observable_compute_static():
    """Test Observable.compute() static method"""

    class State:
        x = Observable(1)
        y = Observable(2)

    state = State()

    # Use static compute method
    sum_obs = Observable.compute(lambda: state.x.value + state.y.value)
    assert sum_obs.value == 3

    state.x.value = 10
    assert sum_obs.value == 12

    state.y.value = 20
    assert sum_obs.value == 30


def test_observable_compute_dispatch_ui():
    """Test Observable.compute() with dispatch_to_ui"""

    class State:
        x = Observable(1)
        y = Observable(2)

    state = State()

    sum_obs = Observable.compute(lambda: state.x.value + state.y.value, dispatch_to_ui=True)
    assert sum_obs.value == 3
    assert sum_obs._dispatch_to_ui is True


def test_batch_with_combine():
    """Test batch with combined observables"""
    from nuiitivet.observable import batch

    class State:
        x = Observable(1)
        y = Observable(2)

    state = State()

    sum_obs = state.x.combine(state.y).compute(lambda x, y: x + y)

    calls = []

    def callback(v):
        calls.append(v)

    sum_obs.subscribe(callback)

    # Use batch
    with batch():
        state.x.value = 10
        state.y.value = 20
        # Should not notify yet

    # After batch, should notify once with final value
    assert calls == [30]
