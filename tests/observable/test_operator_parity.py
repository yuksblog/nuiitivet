"""Every State offers the same operators, so a chain never dead-ends.

``_StateValue``, ``ComputedState`` and ``SourceSubscribingState``
each define the operator set themselves — they cannot share a mixin, because the
first two propagate the ``dispatch=False`` opt-out into what they build and a
wrapper has none to propagate. Three copies drift, and the
drift is invisible until someone writes ``debounce(...).filter(...)`` and finds
the method missing, which is exactly how ``filter`` was once left off the
wrappers. This
test is the cheap guard: add an operator to one, add it to all three.
"""

import inspect

import pytest

from nuiitivet.observable import State
from nuiitivet.observable.computed import ComputedState
from nuiitivet.observable.value import _StateValue
from nuiitivet.observable.wrapper import SourceSubscribingState


OPERATORS = ("map", "combine", "filter", "debounce", "throttle", "switch_map", "scan")

OPERATOR_HOSTS = (_StateValue, ComputedState, SourceSubscribingState)


@pytest.mark.parametrize("host", OPERATOR_HOSTS, ids=lambda cls: cls.__name__)
@pytest.mark.parametrize("operator", OPERATORS)
def test_every_state_defines_every_operator(host, operator):
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
    # read interface every State also has.
    read_interface = {"subscribe", "value", "set", "dispose"}
    candidates = {
        name
        for name in dir(_StateValue)
        if not name.startswith("_") and name not in read_interface
    }
    shared = {
        name
        for name in candidates
        if all(callable(getattr(host, name, None)) for host in OPERATOR_HOSTS)
    }

    assert shared <= known, f"undeclared operators shared by every State: {shared - known}"


def test_the_chain_actually_composes():
    """The parity is about real chains, so build one that touches every hop."""
    source = State(0)

    chained = (
        source.map(lambda n: n + 1)
        .filter(lambda n: n > 0, initial=0)
        .debounce(0.1)
        .throttle(0.1)
        .filter(lambda n: n < 100, initial=0)
    )

    assert chained.value == 1
