"""Concrete State base classes back the hot-path isinstance fast path.

Every built-in State must subclass :class:`StateBase` (and the mutable
ones :class:`MutableStateBase`) so widget construction can use a pure-C
``isinstance`` check instead of the slow ``@runtime_checkable`` Protocol check,
while still satisfying the Protocols structurally.
"""

from nuiitivet.observable import State, combine
from nuiitivet.observable.computed import ComputedState
from nuiitivet.observable.protocols import (
    MutableStateBase,
    StateBase,
    StateProtocol,
    ReadOnlyStateProtocol,
)
from nuiitivet.observable.timed import DebouncedState, ThrottledState
from nuiitivet.observable.value import _StateValue


def test_mutable_states_are_mutable_base():
    obs = State(0)
    assert isinstance(obs, MutableStateBase)
    assert isinstance(obs, StateBase)
    assert isinstance(_StateValue(0), MutableStateBase)


def test_readonly_states_are_readonly_base_only():
    computed = ComputedState(lambda: 1)
    debounced = DebouncedState(State(0), 0.1)
    throttled = ThrottledState(State(0), 0.1)

    for ro in (computed, debounced, throttled):
        assert isinstance(ro, StateBase)
        # read-only States expose no writable ``value``
        assert not isinstance(ro, MutableStateBase)


def test_bases_still_satisfy_protocols_structurally():
    obs = State(0)
    computed = ComputedState(lambda: 1)
    assert isinstance(obs, StateProtocol)
    assert isinstance(obs, ReadOnlyStateProtocol)
    assert isinstance(computed, ReadOnlyStateProtocol)
    # A property's setter is invisible to a runtime-checkable Protocol, so this
    # separation rests on ``set`` existing only on the mutable side.
    assert not isinstance(computed, StateProtocol)


def test_plain_values_are_not_states():
    for value in (12, 1.5, "red", (1, 2, 3, 4), None):
        assert not isinstance(value, StateBase)
        assert not isinstance(value, MutableStateBase)


def test_combine_result_is_state_base():
    combined = combine(State(1), State(2)).compute(lambda a, b: a + b)
    assert isinstance(combined, StateBase)


def test_animatable_is_recognised_as_state():
    """Animatable is a duck-typed State; it must ride the fast path too.

    Regression guard: widget setters use ``isinstance(x, StateBase)``
    to decide whether to observe a value, so Animatable (passed e.g. to ``rotate``)
    must subclass StateBase or it would silently be treated as a plain value.
    """
    from nuiitivet.animation.animatable import Animatable

    anim = Animatable(0.0)
    assert isinstance(anim, StateBase)
    assert isinstance(anim, ReadOnlyStateProtocol)
    # read-only: no writable ``value``
    assert not isinstance(anim, MutableStateBase)
