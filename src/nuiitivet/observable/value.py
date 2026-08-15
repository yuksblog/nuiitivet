from __future__ import annotations

import logging
import threading
import warnings
from typing import Any, Callable, List, Optional, TypeVar, TYPE_CHECKING

from nuiitivet.common.logging_once import debug_once
from nuiitivet.runtime.threading import is_ui_thread

from ._sentinel import UNSET, _Unset
from .contexts import _batch_context, _tracking_context
from .protocols import CompareFunc, Disposable, MutableObservableBase, ReadOnlyObservableProtocol
from . import runtime

if TYPE_CHECKING:
    from .combine import CombineBuilder
    from .computed import ComputedObservable
    from .filtered import FilteredObservable
    from .switched import CancelToken, SwitchMappedObservable
    from .timed import DebouncedObservable, ThrottledObservable

T = TypeVar("T")
_R = TypeVar("_R")


logger = logging.getLogger(__name__)


class _ObservableValue(MutableObservableBase[T]):
    def __init__(
        self,
        initial: T,
        owner: Optional[Any] = None,
        name: Optional[str] = None,
        compare: Optional[CompareFunc[T]] = None,
        dispatch: bool = True,
    ):
        self._value = initial
        self._subs: List[Callable[[T], None]] = []
        self._owner = owner
        self._name = name
        self._compare = compare
        self._dispatch_to_ui = dispatch

        self._lock = threading.Lock()
        self._pending_value: T | _Unset = UNSET
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
        should_dispatch = self._dispatch_to_ui and not is_ui_thread()

        if should_dispatch:
            with self._lock:
                self._pending_value = v
                if not self._is_scheduled:
                    self._is_scheduled = True
                    runtime.clock.schedule_once(self._process_pending_update, 0)
            return

        self._apply(v)

    def _apply(self, v: T) -> None:
        """Store ``v`` and notify, skipping the dispatch decision entirely.

        The setter routes here once it has decided not to dispatch, and the
        deferred flush routes here because the decision was already made when
        the write was queued. Re-entering the setter instead would re-evaluate
        ``should_dispatch`` on whatever thread the clock used, and a clock that
        fires off the main thread would queue the value again, forever.
        """
        if self._is_equal(v):
            return

        self._value = v
        self._notify_subs()

        batch_ctx = _batch_context.get()
        if batch_ctx is not None:
            batch_ctx.record_change(self)

    def _process_pending_update(self, dt: float) -> None:
        with self._lock:
            pending = self._pending_value
            if pending is UNSET:
                self._is_scheduled = False
                return
            self._pending_value = UNSET
            self._is_scheduled = False

        self._apply(pending)

    def _notify_subs(self) -> None:
        for cb in list(self._subs):
            cb(self._value)

    def map(self, fn: Callable[[T], Any]) -> "ComputedObservable[Any]":
        from .computed import ComputedObservable

        def compute_fn() -> Any:
            return fn(self.value)

        # The opt-out propagates: a logic-layer observable's derivations are
        # logic-layer too, and re-enabling dispatch here would silently start
        # coalescing values the source was declared to deliver in full.
        return ComputedObservable(compute_fn, dispatch=self._dispatch_to_ui)

    def combine(self, *others: ReadOnlyObservableProtocol[Any]) -> "CombineBuilder":
        from .combine import CombineBuilder

        return CombineBuilder(self, *others)

    def filter(self, pred: Callable[[T], bool], *, initial: T) -> "FilteredObservable[T]":
        """Observable of the values passing ``pred``, seeded with ``initial``.

        ``initial`` is required because a filtered observable has no value of
        its own until something passes; see
        :class:`~nuiitivet.observable.filtered.FilteredObservable`.
        """
        from .filtered import FilteredObservable

        return FilteredObservable(self, pred, initial=initial)

    def debounce(self, seconds: float) -> "DebouncedObservable[T]":
        from .timed import DebouncedObservable

        return DebouncedObservable(self, seconds)

    def throttle(self, seconds: float) -> "ThrottledObservable[T]":
        from .timed import ThrottledObservable

        return ThrottledObservable(self, seconds)

    def switch_map(
        self,
        fn: Callable[[T, "CancelToken"], _R],
        *,
        initial: _R,
    ) -> "SwitchMappedObservable[T, _R]":
        """Asynchronous :meth:`map`: the newest run's result, older runs discarded.

        See :class:`~nuiitivet.observable.switched.SwitchMappedObservable`.
        """
        from .switched import SwitchMappedObservable

        return SwitchMappedObservable(self, fn, initial=initial)

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
    """Descriptor for a per-instance observable that can also be used standalone.

    Writes from a thread other than the UI thread are marshalled onto it and
    coalesced, so a subscriber may safely touch widgets whichever thread set
    the value. Pass ``dispatch=False`` for an observable no widget will ever
    bind to: notification then stays synchronous on the writing thread, and
    every intermediate value is delivered rather than only the latest per tick.
    """

    def __init__(
        self,
        default: T,
        *,
        compare: Optional[CompareFunc[T]] = None,
        dispatch: bool = True,
    ):
        super().__init__(initial=default, owner=None, name=None, compare=compare, dispatch=dispatch)
        self.default = default
        self.name: Optional[str] = None
        self.compare = compare
        self.dispatch = dispatch

    def __set_name__(self, owner, name):
        self._name = name
        self.name = name

    def _ensure(self, instance) -> _ObservableValue[T]:
        storage_name = "_obs_" + (self.name if self.name is not None else "")
        storage = instance.__dict__.get(storage_name)
        if storage is None:
            storage = _ObservableValue(
                self.default,
                owner=instance,
                name=self.name,
                compare=self.compare,
                dispatch=self.dispatch,
            )
            instance.__dict__[storage_name] = storage
        return storage

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self._ensure(instance)

    def __set__(self, instance, value: T) -> None:
        self._ensure(instance).value = value

    @staticmethod
    def compute(fn: Callable[[], T], *, dispatch: bool = True) -> "ComputedObservable[T]":
        from .computed import ComputedObservable

        return ComputedObservable(fn, dispatch=dispatch)
