import warnings

from nuiitivet.observable import State


class S:
    x = State(0)


def test_state_basic():
    s = S()
    obs = s.x
    assert obs.value == 0

    captured = []
    disp = obs.subscribe(lambda v: captured.append(v))

    s.x = 3
    assert obs.value == 3
    assert captured == [3]

    disp.dispose()
    s.x = 4
    assert obs.value == 4
    assert captured == [3]


def test_state_skips_equal_assignments():
    class Model:
        value = State("ready")

    state = Model()
    events = []
    state.value.subscribe(events.append)

    state.value = "ready"
    assert events == []

    state.value = "go"
    assert events == ["go"]


def test_state_custom_compare_and_warning():
    class Model:
        metric = State(0.0, compare=lambda old, new: abs(old - new) < 0.5)

    state = Model()
    events = []
    state.metric.subscribe(events.append)

    state.metric = 0.1
    assert events == []

    state.metric = 1.0
    assert events == [1.0]

    class BadState:
        metric = State(_NonComparable())

    bad = BadState()

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        bad.metric = _NonComparable()
    assert captured


class _NonComparable:
    def __eq__(self, other):
        raise RuntimeError("cannot compare")
