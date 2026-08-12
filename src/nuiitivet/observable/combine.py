from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from .computed import ComputedObservable
from .protocols import ReadOnlyObservableProtocol


class CombineBuilder:
    """Builder for combining multiple observables."""

    def __init__(self, *observables: ReadOnlyObservableProtocol[Any]):
        self._observables: Sequence[ReadOnlyObservableProtocol[Any]] = observables

    def compute(self, fn: Callable[..., Any], *, dispatch: Optional[bool] = None) -> ComputedObservable[Any]:
        """Derive an observable from every source.

        ``dispatch`` defaults to what the sources say: the result marshals to
        the UI thread unless **every** source opted out, since one source that
        expects marshalling is enough to need it.
        """
        def compute_fn() -> Any:
            values = [obs.value for obs in self._observables]
            return fn(*values)

        if dispatch is None:
            dispatch = any(getattr(obs, "_dispatch_to_ui", True) for obs in self._observables)
        return ComputedObservable(compute_fn, dispatch=dispatch)


def combine(*observables: ReadOnlyObservableProtocol[Any]) -> CombineBuilder:
    """Combine multiple observables."""
    return CombineBuilder(*observables)
