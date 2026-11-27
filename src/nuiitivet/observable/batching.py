from __future__ import annotations

import heapq
import itertools
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Set, Tuple

from nuiitivet.runtime.threading import is_ui_thread

from .contexts import _batch_context
from . import runtime

if TYPE_CHECKING:
    from .computed import ComputedState

_MAX_RUNS_PER_FLUSH = 100


class BatchContext:
    def __init__(self):
        self._depth = 0
        self._flushing = False
        self._pending_states: Set[Any] = set()
        self._pending_computeds: Set[Any] = set()

    def __enter__(self):
        self._depth += 1
        _batch_context.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._depth -= 1
        if self._depth == 0:
            self._flushing = True
            try:
                if exc_type is None:
                    self._flush()
            finally:
                self._flushing = False
                _batch_context.set(None)
                self._pending_states.clear()
                self._pending_computeds.clear()

    @property
    def is_open(self) -> bool:
        """Whether a write here is deferred: from the outermost enter until its flush returns.

        A task or callback scheduled inside the batch copies the context that
        points here. Its writes after the exit notify at once.
        """
        return self._depth > 0 or self._flushing

    def nested(self):
        """Return a context manager that increments/decrements depth without creating a new context."""
        return self

    def record_change(self, state: Any) -> None:
        self._pending_states.add(state)

    def record_computed(self, computed: Any) -> None:
        if len(self._pending_computeds) > 1000:
            raise RuntimeError(
                "Batch computed queue size limit exceeded (>1000). "
                "Possible infinite loop in ComputedState dependencies."
            )
        self._pending_computeds.add(computed)

    def _flush(self) -> None:
        first = list(self._pending_computeds)
        self._pending_computeds.clear()

        needs_ui_dispatch = any(getattr(obs, "_dispatch_to_ui", True) for obs in self._pending_states)

        if needs_ui_dispatch and not is_ui_thread():
            runtime.clock.schedule_once(lambda dt: self._recompute_in_depth_order(first), 0)
            return

        self._recompute_in_depth_order(first)

    def _recompute_in_depth_order(self, first: List[ComputedState[Any]]) -> None:
        """Recompute the queued derivations, the shallowest first.

        A derivation notified after its run read an old value, so it runs again.

        Raises:
            RuntimeError: A derivation ran more than ``_MAX_RUNS_PER_FLUSH``
                times: a subscriber keeps writing a State the derivation reads.
        """
        heap: List[Tuple[int, int, ComputedState[Any]]] = []
        queued: Set[ComputedState[Any]] = set()
        runs: Dict[ComputedState[Any], int] = {}
        arrival = itertools.count()

        def push(computeds: Iterable[ComputedState[Any]]) -> None:
            for computed in computeds:
                if computed not in queued:
                    queued.add(computed)
                    heapq.heappush(heap, (computed._flush_depth(), next(arrival), computed))

        push(first)
        while heap:
            _, _, computed = heapq.heappop(heap)
            queued.discard(computed)
            runs[computed] = runs.get(computed, 0) + 1
            if runs[computed] > _MAX_RUNS_PER_FLUSH:
                raise RuntimeError(
                    f"A derivation recomputed more than {_MAX_RUNS_PER_FLUSH} times in one batch flush. "
                    "Possible feedback loop: a subscriber writes a State the derivation reads."
                )
            computed._recompute_and_notify()

            notified = list(self._pending_computeds)
            self._pending_computeds.clear()
            push(notified)


def batch() -> BatchContext:
    """Context manager for batching State updates.

    Inside an open batch it returns that batch, which flushes at the outermost exit.
    """
    current: Optional[Any] = _batch_context.get()
    if current is not None and current.is_open:
        return current
    return BatchContext()


def detach_batch() -> None:
    """Detach the current execution context from any active batch.

    This is useful for async tasks spawned from within a batch that should
    not inherit the batch context (as they will outlive the batch scope).
    """
    _batch_context.set(None)
