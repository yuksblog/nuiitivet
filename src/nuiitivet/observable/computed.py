from __future__ import annotations

import logging
import threading
from typing import Any, Callable, List, Optional, Set, TypeVar, TYPE_CHECKING

from nuiitivet.common.logging_once import debug_once, exception_once, exception_once_per_exc
from nuiitivet.runtime.threading import is_ui_thread

from ._notify import notify_all
from ._sentinel import UNSET, _Unset
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
        """Re-run the derivation, re-arm its dependency edges, store the result.

        A derivation that raises is a bug in the caller's function rather than a
        value this observable could publish, so it is logged and the previous
        value kept (``OBSERVABLE.md`` §7). Nothing is raised at any caller: the
        thread that triggered the recompute is whichever one happened to write
        the source -- a clock callback, a ``debounce`` timer -- and none of them
        is a handler for the derivation's bug.

        The dependency edges are re-armed **whether or not the run succeeded**.
        They are torn down before the run, so leaving them down after a failure
        would make this observable permanently deaf: the derivation would never
        be retried, not even once the source that fixes it changes. A run that
        raised before reading anything registers no edge to re-arm, which is the
        one case that stays stuck -- and one that could not have recovered
        anyway, having no source to recover from.
        """
        if self._disposed:
            return

        for disp in self._dep_disposables:
            disp.dispose()
        self._dep_disposables.clear()
        self._deps = set()

        new_value: T | _Unset = UNSET
        token = _tracking_context.set(self)
        try:
            new_value = self._compute()
        except Exception:
            # Keyed by the failure itself, so two broken derivations are
            # reported separately and one that keeps failing stays a single
            # line -- the compute function's own name cannot do that job here,
            # every ``map`` sharing the one ``compute_fn`` closure below.
            exception_once_per_exc(
                logger,
                "computed_fn_raised",
                "Computed function raised; keeping the previous value",
            )
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

        if new_value is not UNSET:
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

    def _current_value(self) -> T:
        """What a subscriber is handed, read afresh for each one.

        ``_value`` is ``Optional[T]`` only because a derivation that raised at
        construction never produced one (§7); every read of it makes the same
        claim, which :attr:`value` already states the same way.
        """
        return self._value  # type: ignore[return-value]

    def _notify_subs(self) -> None:
        should_dispatch = self._dispatch_to_ui and not is_ui_thread()

        if should_dispatch:

            def notify_on_ui(dt: float) -> None:
                notify_all(self._subs, self._current_value, logger=logger, key="computed")

            runtime.clock.schedule_once(notify_on_ui, 0)
            return

        notify_all(self._subs, self._current_value, logger=logger, key="computed")

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
