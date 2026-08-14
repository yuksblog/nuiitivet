from __future__ import annotations

from typing import Callable, Optional, Sequence, TypeVar

from .protocols import ReadOnlyObservableProtocol
from .wrapper import SourceSubscribingObservable
from . import runtime

T = TypeVar("T")


class DebouncedObservable(SourceSubscribingObservable[T]):
    """Debounced observable that emits value only after delay with no new changes.

    Lifetime follows the contract in
    :mod:`~nuiitivet.observable.wrapper`: hold this object, or the ``Disposable``
    from :meth:`subscribe`, for as long as the emissions are wanted.
    """

    def __init__(self, source: ReadOnlyObservableProtocol[T], seconds: float):
        self._seconds = seconds
        self._pending_value: Optional[T] = None
        self._scheduled = False
        super().__init__(source)

    def _clock_callbacks(self) -> Sequence[Callable[[float], None]]:
        return (self._emit,)

    def _on_source_changed(self, value: T) -> None:
        self._pending_value = value

        if self._scheduled:
            runtime.clock.unschedule(self._emit)

        runtime.clock.schedule_once(self._emit, self._seconds)
        self._scheduled = True

    def _emit(self, dt: float) -> None:
        self._scheduled = False
        if self._pending_value is not None:
            self._emit_to_subscribers(self._pending_value)

    def _current_value(self) -> T:
        return self._source.value


class ThrottledObservable(SourceSubscribingObservable[T]):
    """Throttled observable that emits first value then ignores changes for duration.

    Lifetime follows the contract in
    :mod:`~nuiitivet.observable.wrapper`: hold this object, or the ``Disposable``
    from :meth:`subscribe`, for as long as the emissions are wanted.
    """

    def __init__(self, source: ReadOnlyObservableProtocol[T], seconds: float):
        self._seconds = seconds
        self._throttling = False
        self._pending_value: Optional[T] = None
        super().__init__(source)

    def _clock_callbacks(self) -> Sequence[Callable[[float], None]]:
        return (self._emit_pending,)

    def _on_source_changed(self, value: T) -> None:
        if not self._throttling:
            self._emit_to_subscribers(value)
            self._throttling = True
            runtime.clock.schedule_once(self._emit_pending, self._seconds)
            return

        self._pending_value = value

    def _emit_pending(self, dt: float) -> None:
        if self._pending_value is not None:
            self._emit_to_subscribers(self._pending_value)
            self._pending_value = None
            runtime.clock.schedule_once(self._emit_pending, self._seconds)
            return

        self._throttling = False

    def _current_value(self) -> T:
        return self._source.value
