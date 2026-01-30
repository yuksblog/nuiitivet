from __future__ import annotations

import logging
import threading
import warnings
from typing import Any, Callable, Generic, List, Optional, TypeVar, TYPE_CHECKING

from nuiitivet.common.logging_once import debug_once

from .contexts import _batch_context, _tracking_context
from .protocols import CompareFunc, Disposable, ReadOnlyObservableProtocol
from . import runtime

if TYPE_CHECKING:
    from .combine import CombineBuilder
    from .computed import ComputedObservable
    from .timed import DebouncedObservable, ThrottledObservable

T = TypeVar("T")


logger = logging.getLogger(__name__)

_UNSET = object()


class _ObservableValue(Generic[T]):
    def __init__(
        self,
        initial: T,
        owner: Optional[Any] = None,
        name: Optional[str] = None,
        compare: Optional[CompareFunc[T]] = None,
    ):
        self._value = initial
        self._subs: List[Callable[[T], None]] = []
        self._owner = owner
        self._name = name
        self._compare = compare
        self._dispatch_to_ui = False

        self._lock = threading.Lock()
        self._pending_value: Any = _UNSET
        self._is_scheduled = False

    def _is_equal(self, candidate: T) -> bool:
        owner_name = type(self._owner).__name__ if self._owner is not None else "ObservableOwner"
        if self._compare is not None:
            try:
                return bool(self._compare(self._value, candidate))
            except Exception as exc:
                msg = f"Observable compare failed for '{self._name}' on {owner_name}: {exc}"
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
                return False
        try:
            result = self._value == candidate
        except Exception as exc:  # pragma: no cover
            msg = f"Observable equality failed for '{self._name}' on {owner_name}: {exc}"
            warnings.warn(msg, RuntimeWarning, stacklevel=2)
            return False
        if isinstance(result, bool):
            return result
        msg = f"Observable equality for '{self._name}' on {owner_name} returned non-bool {result!r}"
        warnings.warn(msg, RuntimeWarning, stacklevel=2)
        return False

    @property
    def value(self) -> T:
        tracker = _tracking_context.get()
        if tracker is not None:
            tracker._register_dependency(self)
        with self._lock:
            return self._value

    @value.setter
    def value(self, v: T) -> None:
        should_dispatch = self._dispatch_to_ui and threading.current_thread() is not threading.main_thread()

        if should_dispatch:
            with self._lock:
                self._pending_value = v
                if not self._is_scheduled:
                    self._is_scheduled = True
                    runtime.clock.schedule_once(self._process_pending_update, 0)
            return

        if self._is_equal(v):
            return

        self._value = v
        self._notify_subs()

        batch_ctx = _batch_context.get()
        if batch_ctx is not None:
            batch_ctx.record_change(self)

    def _process_pending_update(self, dt: float) -> None:
        with self._lock:
            if self._pending_value is _UNSET:
                self._is_scheduled = False
                return
            v = self._pending_value
            self._pending_value = _UNSET
            self._is_scheduled = False

        self.value = v

    def _notify_subs(self) -> None:
        for cb in list(self._subs):
            cb(self._value)

    def dispatch_to_ui(self) -> "_ObservableValue[T]":
        """Enable UI thread dispatching (chainable)."""
        self._dispatch_to_ui = True
        return self

    def map(self, fn: Callable[[T], Any]) -> "ComputedObservable[Any]":
        from .computed import ComputedObservable

        def compute_fn() -> Any:
            return fn(self.value)

        return ComputedObservable(compute_fn, dispatch_to_ui=self._dispatch_to_ui)

    def combine(self, *others: ReadOnlyObservableProtocol[Any]) -> "CombineBuilder":
        from .combine import CombineBuilder

        return CombineBuilder(self, *others)

    def debounce(self, seconds: float) -> "DebouncedObservable[T]":
        from .timed import DebouncedObservable

        return DebouncedObservable(self, seconds)

    def throttle(self, seconds: float) -> "ThrottledObservable[T]":
        from .timed import ThrottledObservable

        return ThrottledObservable(self, seconds)

    def subscribe(self, cb: Callable[[T], None]) -> Disposable:
        self._subs.append(cb)

        def _dispose() -> None:
            try:
                self._subs.remove(cb)
            except ValueError:
                debug_once(logger, "value_observable_dispose_remove_missing", "Subscriber callback was already removed")

        return Disposable(_dispose)

    def changes(self) -> ReadOnlyObservableProtocol[T]:
        return self


class Observable(_ObservableValue[T]):
    """Descriptor for a per-instance observable that can also be used standalone."""

    def __init__(self, default: T, *, compare: Optional[CompareFunc[T]] = None):
        super().__init__(initial=default, owner=None, name=None, compare=compare)
        self.default = default
        self.name: Optional[str] = None
        self.compare = compare

    def __set_name__(self, owner, name):
        self._name = name
        self.name = name

    def _ensure(self, instance) -> _ObservableValue[T]:
        storage_name = "_obs_" + (self.name if self.name is not None else "")
        storage = instance.__dict__.get(storage_name)
        if storage is None:
            storage = _ObservableValue(self.default, owner=instance, name=self.name, compare=self.compare)
            instance.__dict__[storage_name] = storage
        return storage

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self._ensure(instance)

    def __set__(self, instance, value: T) -> None:
        self._ensure(instance).value = value

    @staticmethod
    def compute(fn: Callable[[], T], *, dispatch_to_ui: bool = False) -> "ComputedObservable[T]":
        from .computed import ComputedObservable

        return ComputedObservable(fn, dispatch_to_ui=dispatch_to_ui)
