from __future__ import annotations

from typing import Any, Callable, Sequence

from .computed import ComputedObservable
from .protocols import ReadOnlyObservableProtocol


class CombineBuilder:
    """Builder for combining multiple observables."""

    def __init__(self, *observables: ReadOnlyObservableProtocol[Any]):
        self._observables: Sequence[ReadOnlyObservableProtocol[Any]] = observables
        self._dispatch_to_ui = False

    def dispatch_to_ui(self) -> "CombineBuilder":
        self._dispatch_to_ui = True
        return self

    def compute(self, fn: Callable[..., Any]) -> ComputedObservable[Any]:
        def compute_fn() -> Any:
            values = [obs.value for obs in self._observables]
            return fn(*values)

        return ComputedObservable(compute_fn, dispatch_to_ui=self._dispatch_to_ui)


def combine(*observables: ReadOnlyObservableProtocol[Any]) -> CombineBuilder:
    """Combine multiple observables."""
    return CombineBuilder(*observables)
