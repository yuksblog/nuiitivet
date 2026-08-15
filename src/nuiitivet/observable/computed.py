from __future__ import annotations

import logging
import threading
from typing import Any, Callable, List, Optional, Set, TypeVar, TYPE_CHECKING

from nuiitivet.common.logging_once import debug_once, exception_once
from nuiitivet.runtime.threading import is_ui_thread

from .contexts import _batch_context, _tracking_context
from .protocols import (
    Disposable,
    ObservableBase,
    ReadOnlyObservableProtocol,
    mark_internal_subscription,
)
from . import runtime

if TYPE_CHECKING:
    from .combine import CombineBuilder
    from .filtered import FilteredObservable
    from .switched import CancelToken, SwitchMappedObservable
    from .timed import DebouncedObservable, ThrottledObservable

T = TypeVar("T")
_R = TypeVar("_R")


logger = logging.getLogger(__name__)


class ComputedObservable(ObservableBase[T]):
    """Computed observable with automatic dependency tracking (Signals pattern)."""

    def __init__(
        self,
        compute: Callable[[], T],
        dispatch: bool = True,
    ):
        self._compute = compute
        self._value: Optional[T] = None
        self._subs: List[Callable[[T], None]] = []
        self._deps: Set[Any] = set()
        self._dep_disposables: List[Disposable] = []
        self._dispatch_to_ui = dispatch
        self._disposed = False

        self._lock = threading.Lock()
        self._is_scheduled = False

        self._recompute()

    def _register_dependency(self, dep: Any) -> None:
        with self._lock:
            self._deps.add(dep)

    def _recompute(self) -> None:
        if self._disposed:
            return

        for disp in self._dep_disposables:
            disp.dispose()
        self._dep_disposables.clear()
        self._deps = set()

        token = _tracking_context.set(self)
        try:
            new_value = self._compute()
        finally:
            _tracking_context.reset(token)

        for dep in self._deps:
            import weakref

            def make_callback(weak_self):
                def callback(v):
                    self_obj = weak_self()
                    if self_obj is not None:
                        self_obj._on_dep(v)

                return callback

            weak_ref = weakref.ref(self)
            cb = mark_internal_subscription(make_callback(weak_ref))

            disp = dep.subscribe(cb)
            self._dep_disposables.append(disp)

        self._value = new_value

    @property
    def value(self) -> T:
        tracker = _tracking_context.get()
        if tracker is not None and tracker is not self:
            tracker._register_dependency(self)
        with self._lock:
            return self._value  # type: ignore[return-value]

    def _on_dep(self, _v: Any) -> None:
        batch_ctx = _batch_context.get()
        if batch_ctx is not None:
            batch_ctx.record_computed(self)
            return

        should_dispatch = self._dispatch_to_ui and not is_ui_thread()

        if should_dispatch:
            with self._lock:
                if not self._is_scheduled:
                    self._is_scheduled = True
                    runtime.clock.schedule_once(self._process_pending_update, 0)
            return

        self._recompute_and_notify()

    def _process_pending_update(self, dt: float) -> None:
        with self._lock:
            self._is_scheduled = False
        self._recompute_and_notify()

    def _recompute_and_notify(self) -> None:
        old_value = self._value
        self._recompute()
        new_value = self._value

        try:
            is_equal = new_value == old_value
            if not isinstance(is_equal, bool):
                is_equal = False
        except Exception:
            exception_once(logger, "computed_value_eq_exc", "Computed value equality check raised")
            is_equal = False

        if not is_equal:
            self._notify_subs()

    def _notify_subs(self) -> None:
        should_dispatch = self._dispatch_to_ui and not is_ui_thread()

        if should_dispatch:

            def notify_on_ui(dt: float) -> None:
                for cb in list(self._subs):
                    cb(self._value)  # type: ignore[arg-type]

            runtime.clock.schedule_once(notify_on_ui, 0)
            return

        for cb in list(self._subs):
            cb(self._value)  # type: ignore[arg-type]

    def subscribe(self, cb: Callable[[T], None]) -> Disposable:
        self._subs.append(cb)

        def _dispose() -> None:
            try:
                self._subs.remove(cb)
            except ValueError:
                debug_once(logger, "computed_dispose_remove_missing", "Subscriber callback was already removed")

        return Disposable(_dispose)

    def map(self, fn: Callable[[T], Any]) -> "ComputedObservable[Any]":
        def compute_fn() -> Any:
            return fn(self.value)

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

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        for disp in self._dep_disposables:
            disp.dispose()
        self._dep_disposables.clear()
        self._deps.clear()
        self._subs.clear()

    def __del__(self):
        self.dispose()
