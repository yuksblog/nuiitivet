"""Concrete observable base classes back the hot-path isinstance fast path.

Every built-in observable must subclass :class:`ObservableBase` (and the mutable
ones :class:`MutableObservableBase`) so widget construction can use a pure-C
``isinstance`` check instead of the slow ``@runtime_checkable`` Protocol check,
while still satisfying the Protocols structurally.
"""

from nuiitivet.observable import Observable, combine
from nuiitivet.observable.computed import ComputedObservable
from nuiitivet.observable.protocols import (
    MutableObservableBase,
    ObservableBase,
    ObservableProtocol,
    ReadOnlyObservableProtocol,
)
from nuiitivet.observable.timed import DebouncedObservable, ThrottledObservable
from nuiitivet.observable.value import _ObservableValue


def test_mutable_observables_are_mutable_base():
    obs = Observable(0)
    assert isinstance(obs, MutableObservableBase)
    assert isinstance(obs, ObservableBase)
    assert isinstance(_ObservableValue(0), MutableObservableBase)


def test_readonly_observables_are_readonly_base_only():
    computed = ComputedObservable(lambda: 1)
    debounced = DebouncedObservable(Observable(0), 0.1)
    throttled = ThrottledObservable(Observable(0), 0.1)

    for ro in (computed, debounced, throttled):
        assert isinstance(ro, ObservableBase)
        # read-only observables expose no writable ``value``
        assert not isinstance(ro, MutableObservableBase)


def test_bases_still_satisfy_protocols_structurally():
    obs = Observable(0)
    computed = ComputedObservable(lambda: 1)
    assert isinstance(obs, ObservableProtocol)
    assert isinstance(obs, ReadOnlyObservableProtocol)
    assert isinstance(computed, ReadOnlyObservableProtocol)
    # A property's setter is invisible to a runtime-checkable Protocol, so this
    # separation rests on ``set`` existing only on the mutable side.
    assert not isinstance(computed, ObservableProtocol)


def test_plain_values_are_not_observables():
    for value in (12, 1.5, "red", (1, 2, 3, 4), None):
        assert not isinstance(value, ObservableBase)
        assert not isinstance(value, MutableObservableBase)


def test_combine_result_is_observable_base():
    combined = combine(Observable(1), Observable(2)).compute(lambda a, b: a + b)
    assert isinstance(combined, ObservableBase)


def test_animatable_is_recognised_as_observable():
    """Animatable is a duck-typed observable; it must ride the fast path too.

    Regression guard: widget setters use ``isinstance(x, ObservableBase)``
    to decide whether to observe a value, so Animatable (passed e.g. to ``rotate``)
    must subclass ObservableBase or it would silently be treated as a plain value.
    """
    from nuiitivet.animation.animatable import Animatable

    anim = Animatable(0.0)
    assert isinstance(anim, ObservableBase)
    assert isinstance(anim, ReadOnlyObservableProtocol)
    # read-only: no writable ``value``
    assert not isinstance(anim, MutableObservableBase)
