"""Test State Phase 1: combine() and CombineBuilder"""

from nuiitivet.observable import State, combine


def test_combine_basic():
    """Test basic combine functionality"""

    class Model:
        x = State(1)
        y = State(2)

    state = Model()

    # Combine two States
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

    class Model:
        x = State(1)
        y = State(2)
        z = State(3)

    state = Model()

    # Use combine function
    sum_obs = combine(state.x, state.y, state.z).compute(lambda x, y, z: x + y + z)
    assert sum_obs.value == 6

    state.x.value = 10
    assert sum_obs.value == 15


def test_combine_dispatches_unless_every_source_opted_out():
    """One source that expects marshalling is enough to need it."""

    class Model:
        x = State(1)
        y = State(2)
        internal_a = State(1, dispatch=False)
        internal_b = State(2, dispatch=False)

    state = Model()

    both_bound = state.x.combine(state.y).compute(lambda x, y: x + y)
    assert both_bound.value == 3
    assert both_bound._dispatch_to_ui is True

    mixed = state.internal_a.combine(state.y).compute(lambda x, y: x + y)
    assert mixed._dispatch_to_ui is True

    neither = state.internal_a.combine(state.internal_b).compute(lambda x, y: x + y)
    assert neither._dispatch_to_ui is False

    state.x.value = 10
    assert both_bound.value == 12


def test_combine_compute_takes_an_explicit_dispatch():
    """The inferred answer can be overridden either way."""

    class Model:
        x = State(1)
        internal = State(2, dispatch=False)

    state = Model()

    assert state.x.combine(state.x).compute(lambda a, b: a + b, dispatch=False)._dispatch_to_ui is False
    assert (
        state.internal.combine(state.internal).compute(lambda a, b: a + b, dispatch=True)._dispatch_to_ui
        is True
    )


def test_combine_subscription():
    """Test combine with subscription"""

    class Model:
        x = State(1)
        y = State(2)

    state = Model()

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


def test_state_compute_static():
    """Test State.compute() static method"""

    class Model:
        x = State(1)
        y = State(2)

    state = Model()

    # Use static compute method
    sum_obs = State.compute(lambda: state.x.value + state.y.value)
    assert sum_obs.value == 3

    state.x.value = 10
    assert sum_obs.value == 12

    state.y.value = 20
    assert sum_obs.value == 30


def test_state_compute_dispatch_flag():
    """``State.compute`` dispatches by default and takes the opt-out."""

    class Model:
        x = State(1)
        y = State(2)

    state = Model()

    sum_obs = State.compute(lambda: state.x.value + state.y.value)
    assert sum_obs.value == 3
    assert sum_obs._dispatch_to_ui is True

    internal = State.compute(lambda: state.x.value + state.y.value, dispatch=False)
    assert internal._dispatch_to_ui is False


def test_batch_with_combine():
    """Test batch with combined States"""
    from nuiitivet.observable import batch

    class Model:
        x = State(1)
        y = State(2)

    state = Model()

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
