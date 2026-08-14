from __future__ import annotations

from typing import Callable, Sequence, TypeVar

from ._sentinel import UNSET, _Unset
from .protocols import ReadOnlyObservableProtocol
from .wrapper import SourceSubscribingObservable
from . import runtime

T = TypeVar("T")


class DebouncedObservable(SourceSubscribingObservable[T]):
    """Debounced observable that emits value only after delay with no new changes.

    ``value`` is the last debounced emission — the construction-time value of the
    source until the input first settles — so binding this straight into a widget
    shows debounced values. Lifetime follows the contract in
    :mod:`~nuiitivet.observable.wrapper`: hold this object, or the ``Disposable``
    from :meth:`subscribe`, for as long as the emissions are wanted.
    """

    def __init__(self, source: ReadOnlyObservableProtocol[T], seconds: float):
        self._seconds = seconds
        self._pending_value: T | _Unset = UNSET
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
        pending = self._pending_value
        if pending is UNSET:
            return

        self._pending_value = UNSET
        self._emit_to_subscribers(pending)


class ThrottledObservable(SourceSubscribingObservable[T]):
    """Throttled observable that emits first value then ignores changes for duration.

    ``value`` is the last throttled emission — the construction-time value of the
    source until the first change, which is emitted on the leading edge — so
    binding this straight into a widget shows throttled values. Lifetime follows
    the contract in :mod:`~nuiitivet.observable.wrapper`: hold this object, or the
    ``Disposable`` from :meth:`subscribe`, for as long as the emissions are wanted.
    """

    def __init__(self, source: ReadOnlyObservableProtocol[T], seconds: float):
        self._seconds = seconds
        self._throttling = False
        self._pending_value: T | _Unset = UNSET
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
        pending = self._pending_value
        if pending is UNSET:
            self._throttling = False
            return

        self._pending_value = UNSET
        self._emit_to_subscribers(pending)
        runtime.clock.schedule_once(self._emit_pending, self._seconds)
