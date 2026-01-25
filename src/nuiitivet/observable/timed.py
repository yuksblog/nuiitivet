from __future__ import annotations

import logging
from typing import Any, Callable, Generic, List, Optional, TypeVar

from nuiitivet.common.logging_once import debug_once

from .combine import CombineBuilder
from .computed import ComputedObservable
from .protocols import Disposable, ReadOnlyObservableProtocol
from . import runtime

T = TypeVar("T")


logger = logging.getLogger(__name__)


class DebouncedObservable(Generic[T]):
    """Debounced observable that emits value only after delay with no new changes."""

    def __init__(self, source: ReadOnlyObservableProtocol[T], seconds: float):
        self._source = source
        self._seconds = seconds
        self._pending_value: Optional[T] = None
        self._scheduled = False
        self._subscribers: List[Callable[[T], None]] = []
        self._dispatch_to_ui = False

        self._source_subscription = source.subscribe(self._on_source_changed)

    def _on_source_changed(self, value: T) -> None:
        self._pending_value = value

        if self._scheduled:
            runtime.clock.unschedule(self._emit)

        runtime.clock.schedule_once(self._emit, self._seconds)
        self._scheduled = True

    def _emit(self, dt: float) -> None:
        self._scheduled = False
        if self._pending_value is not None:
            for callback in list(self._subscribers):
                callback(self._pending_value)

    def subscribe(self, callback: Callable[[T], None]) -> Disposable:
        self._subscribers.append(callback)

        def _dispose() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                debug_once(logger, "debounced_dispose_remove_missing", "Subscriber callback was already removed")

        return Disposable(_dispose)

    def dispatch_to_ui(self) -> "DebouncedObservable[T]":
        self._dispatch_to_ui = True
        return self

    @property
    def value(self) -> T:
        return self._source.value

    def map(self, fn: Callable[[T], Any]) -> ComputedObservable[Any]:
        def compute_fn() -> Any:
            return fn(self.value)

        return ComputedObservable(compute_fn)

    def combine(self, other: ReadOnlyObservableProtocol[Any]) -> CombineBuilder:
        return CombineBuilder(self, other)

    def changes(self) -> ReadOnlyObservableProtocol[T]:
        return self


class ThrottledObservable(Generic[T]):
    """Throttled observable that emits first value then ignores changes for duration."""

    def __init__(self, source: ReadOnlyObservableProtocol[T], seconds: float):
        self._source = source
        self._seconds = seconds
        self._last_emit_scheduled_time: Optional[float] = None
        self._pending_value: Optional[T] = None
        self._scheduled_callback: Optional[Callable[[float], None]] = None
        self._subscribers: List[Callable[[T], None]] = []
        self._dispatch_to_ui = False

        self._source_subscription = source.subscribe(self._on_source_changed)

    def _on_source_changed(self, value: T) -> None:
        if self._last_emit_scheduled_time is None:
            self._emit_now(value)
            self._last_emit_scheduled_time = 0.0
            self._scheduled_callback = self._emit_pending
            runtime.clock.schedule_once(self._scheduled_callback, self._seconds)
            return

        self._pending_value = value

    def _emit_now(self, value: T) -> None:
        for callback in list(self._subscribers):
            callback(value)

    def _emit_pending(self, dt: float) -> None:
        self._scheduled_callback = None

        if self._pending_value is not None:
            self._emit_now(self._pending_value)
            self._pending_value = None
            self._scheduled_callback = self._emit_pending
            runtime.clock.schedule_once(self._scheduled_callback, self._seconds)
            return

        self._last_emit_scheduled_time = None

    def subscribe(self, callback: Callable[[T], None]) -> Disposable:
        self._subscribers.append(callback)

        def _dispose() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                debug_once(logger, "throttled_dispose_remove_missing", "Subscriber callback was already removed")

        return Disposable(_dispose)

    def dispatch_to_ui(self) -> "ThrottledObservable[T]":
        self._dispatch_to_ui = True
        return self

    @property
    def value(self) -> T:
        return self._source.value

    def map(self, fn: Callable[[T], Any]) -> ComputedObservable[Any]:
        def compute_fn() -> Any:
            return fn(self.value)

        return ComputedObservable(compute_fn)

    def combine(self, other: ReadOnlyObservableProtocol[Any]) -> CombineBuilder:
        return CombineBuilder(self, other)

    def changes(self) -> ReadOnlyObservableProtocol[T]:
        return self
