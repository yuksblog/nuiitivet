from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from .computed import ComputedState
from .protocols import ReadOnlyStateProtocol


class CombineBuilder:
    """Builder for combining multiple States."""

    def __init__(self, *states: ReadOnlyStateProtocol[Any]):
        self._states: Sequence[ReadOnlyStateProtocol[Any]] = states

    def compute(self, fn: Callable[..., Any], *, dispatch: Optional[bool] = None) -> ComputedState[Any]:
        """Derive a State from every source.

        ``dispatch`` defaults to what the sources say: the result marshals to
        the UI thread unless **every** source opted out, since one source that
        expects marshalling is enough to need it.
        """
        def compute_fn() -> Any:
            values = [obs.value for obs in self._states]
            return fn(*values)

        if dispatch is None:
            dispatch = any(getattr(obs, "_dispatch_to_ui", True) for obs in self._states)
        return ComputedState(compute_fn, dispatch=dispatch)


def combine(*states: ReadOnlyStateProtocol[Any]) -> CombineBuilder:
    """Combine multiple States."""
    return CombineBuilder(*states)
