"""Every observable offers the same operators, so a chain never dead-ends.

``_ObservableValue``, ``ComputedObservable`` and ``SourceSubscribingObservable``
each define the operator set themselves — they cannot share a mixin, because the
first two propagate the ``dispatch=False`` opt-out into what they build and a
wrapper has none to propagate (``OBSERVABLE.md`` §3). Three copies drift, and the
drift is invisible until someone writes ``debounce(...).filter(...)`` and finds
the method missing, which is exactly what happened between #555 and #554. This
test is the cheap guard: add an operator to one, add it to all three.
"""

import inspect

import pytest

from nuiitivet.observable import Observable
from nuiitivet.observable.computed import ComputedObservable
from nuiitivet.observable.value import _ObservableValue
from nuiitivet.observable.wrapper import SourceSubscribingObservable


OPERATORS = ("map", "combine", "filter", "debounce", "throttle", "switch_map")

OPERATOR_HOSTS = (_ObservableValue, ComputedObservable, SourceSubscribingObservable)


@pytest.mark.parametrize("host", OPERATOR_HOSTS, ids=lambda cls: cls.__name__)
@pytest.mark.parametrize("operator", OPERATORS)
def test_every_observable_defines_every_operator(host, operator):
    assert callable(getattr(host, operator, None)), (
        f"{host.__name__} is missing .{operator}() — a chain reaching it stops there"
    )


@pytest.mark.parametrize("operator", OPERATORS)
def test_the_signatures_agree(operator):
    """Same name, same parameters — otherwise the parity above is cosmetic."""
    signatures = {
        host.__name__: [
            (name, parameter.kind)
            for name, parameter in inspect.signature(getattr(host, operator)).parameters.items()
            if name != "self"
        ]
        for host in OPERATOR_HOSTS
    }

    distinct = {tuple(params) for params in signatures.values()}
    assert len(distinct) == 1, f".{operator}() signatures differ: {signatures}"


def test_no_operator_is_missing_from_the_list():
    """Guards the guard: a new public operator must be added to ``OPERATORS``."""
    known = set(OPERATORS)
    # Everything public and callable on all three that is not part of the
    # read interface every observable also has.
    read_interface = {"subscribe", "changes", "value", "set", "dispose"}
    candidates = {
        name
        for name in dir(_ObservableValue)
        if not name.startswith("_") and name not in read_interface
    }
    shared = {
        name
        for name in candidates
        if all(callable(getattr(host, name, None)) for host in OPERATOR_HOSTS)
    }

    assert shared <= known, f"undeclared operators shared by every observable: {shared - known}"


def test_the_chain_actually_composes():
    """The parity is about real chains, so build one that touches every hop."""
    source = Observable(0)

    chained = (
        source.map(lambda n: n + 1)
        .filter(lambda n: n > 0, initial=0)
        .debounce(0.1)
        .throttle(0.1)
        .filter(lambda n: n < 100, initial=0)
    )

    assert chained.value == 1
