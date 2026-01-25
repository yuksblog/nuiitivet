from __future__ import annotations

import threading
from typing import Any, Optional, Set

from .contexts import _batch_context
from . import runtime


class BatchContext:
    def __init__(self):
        self._depth = 0
        self._pending_observables: Set[Any] = set()
        self._pending_computeds: Set[Any] = set()

    def __enter__(self):
        self._depth += 1
        _batch_context.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._depth -= 1
        if self._depth == 0:
            try:
                if exc_type is None:
                    self._flush()
            finally:
                _batch_context.set(None)
                self._pending_observables.clear()
                self._pending_computeds.clear()

    def nested(self):
        """Return a context manager that increments/decrements depth without creating a new context."""
        return self

    def record_change(self, observable: Any) -> None:
        self._pending_observables.add(observable)

    def record_computed(self, computed: Any) -> None:
        if len(self._pending_computeds) > 1000:
            raise RuntimeError(
                "Batch computed queue size limit exceeded (>1000). "
                "Possible infinite loop in ComputedObservable dependencies."
            )
        self._pending_computeds.add(computed)

    def _flush(self) -> None:
        queue = list(self._pending_computeds)
        self._pending_computeds.clear()

        processed = set()

        needs_ui_dispatch = any(getattr(obs, "_dispatch_to_ui", False) for obs in self._pending_observables)

        def do_flush() -> None:
            while queue:
                computed = queue.pop(0)
                if computed in processed:
                    continue
                processed.add(computed)

                computed._recompute_and_notify()

                if self._pending_computeds:
                    for c in self._pending_computeds:
                        if c not in processed:
                            queue.append(c)
                    self._pending_computeds.clear()

        if needs_ui_dispatch and threading.current_thread() is not threading.main_thread():
            runtime.clock.schedule_once(lambda dt: do_flush(), 0)
            return

        do_flush()


def batch() -> BatchContext:
    """Context manager for batching Observable updates."""
    current: Optional[Any] = _batch_context.get()
    if current is not None:
        return current
    return BatchContext()


def detach_batch() -> None:
    """Detach the current execution context from any active batch.

    This is useful for async tasks spawned from within a batch that should
    not inherit the batch context (as they will outlive the batch scope).
    """
    _batch_context.set(None)
