"""Lifetime contract for observables that subscribe to an upstream source.

``map`` and ``compute`` derive a value and hold nothing; ``debounce``,
``throttle``, ``filter`` and anything else that shapes *when* or *whether* a
source's values are republished must stay subscribed to a source for as long as
they live. That subscription is an edge the garbage
collector can see, and pointing it the wrong way makes the whole chain
uncollectable. :class:`SourceSubscribingObservable` owns that edge so each
operator does not re-decide it.

**The source must not keep the wrapper alive.** ``source.subscribe(self._on_x)``
stores a *bound method*, which strongly references the wrapper, so the source
outliving the wrapper keeps it — and every observable it in turn holds —
reachable forever. The subscription therefore goes through a weak reference to
``self``, the same shape :class:`~nuiitivet.observable.computed.ComputedObservable`
already uses for its dependency edges.

**So a wrapper lives exactly as long as something holds it.** Either the object
itself (``self.results = query.debounce(0.3)``) or the ``Disposable`` that
:meth:`~SourceSubscribingObservable.subscribe` returns, whose closure holds the
wrapper. That second half is what makes the framework's own convention correct
without further thought::

    self.bind(self.query.debounce(0.3).subscribe(self._on_query))

``bind()`` retains the ``Disposable``, which retains the chain, and unmount
disposes it — after which nothing holds the chain and all of it is collectable.
Dropping the ``Disposable`` on the floor instead drops the chain with it, which
is the same rule ``compute`` and ``map`` already follow: a derived observable
nobody holds does not exist.

**A wrapper holds the value it last emitted.** Shaping is not a property of the
notification path alone: ``.value`` reports what this observable last emitted,
seeded from the source when the wrapper is constructed. That is what makes
``nv.Text(query.debounce(0.3))`` show debounced text — reading through to the
source instead would silently ignore the operator the caller asked for. Between
construction and the first emission a wrapper therefore reports the seed: for
``debounce``, the construction-time value until the input first settles.

**Teardown releases the source and disarms the clock.** :meth:`dispose` is
idempotent and runs from ``__del__`` as a backstop, so a wrapper that goes out of
scope with a timer armed does not fire into a dead chain.

**Two type parameters, because one operator changes the type.** ``debounce``,
``throttle`` and ``filter`` reshape *when* or *whether* a value is republished
and hand on what they were given, so their input and output types agree;
:class:`ShapingObservable` names that case and seeds them from the source.
``switch_map`` maps ``TIn`` to a different ``TOut`` and cannot be seeded from the
source at all, which is why the seed is a method rather than a line in
``__init__``.
"""

from __future__ import annotations

import logging
import weakref
from typing import Any, Callable, Generic, List, Optional, Sequence, TypeVar, TYPE_CHECKING

from nuiitivet.common.logging_once import debug_once

from .contexts import _tracking_context
from .protocols import (
    Disposable,
    ObservableBase,
    ReadOnlyObservableProtocol,
    mark_internal_subscription,
)
from . import runtime

if TYPE_CHECKING:
    from .combine import CombineBuilder
    from .computed import ComputedObservable
    from .filtered import FilteredObservable
    from .switched import CancelToken, SwitchMappedObservable
    from .timed import DebouncedObservable, ThrottledObservable

T = TypeVar("T")
TIn = TypeVar("TIn")
TOut = TypeVar("TOut")
_R = TypeVar("_R")


logger = logging.getLogger(__name__)


def _untracked(fn: Callable[[], _R]) -> _R:
    """Run ``fn`` with dependency tracking suppressed.

    Whatever a wrapper reads internally — its source, or a user callback that
    happens to read an observable — is read on behalf of the wrapper itself,
    never on behalf of whatever derivation is recording dependencies at the time.
    """
    token = _tracking_context.set(None)
    try:
        return fn()
    finally:
        _tracking_context.reset(token)


def _read_untracked(source: ReadOnlyObservableProtocol[T]) -> T:
    """Read ``source.value`` without registering it with the tracking context."""
    return _untracked(lambda: source.value)


class SourceSubscribingObservable(ObservableBase[TOut], Generic[TIn, TOut]):
    """Base for observables that hold a live subscription to an upstream source.

    Subclasses implement :meth:`_seed` (what :attr:`value` reports before the
    first emission) and :meth:`_on_source_changed` (what to do with an upstream
    value), and decide when to call :meth:`_emit_to_subscribers`, which is also
    what updates the value this wrapper reports. Any clock callbacks they arm go
    in :meth:`_clock_callbacks` so teardown can disarm them.

    ``TIn`` is what the source publishes, ``TOut`` what this observable does.
    Operators that hand values on unchanged subclass :class:`ShapingObservable`
    instead, which fixes the two together.
    """

    # Class-level defaults so ``__del__`` is safe on an instance whose
    # ``__init__`` raised before ``super().__init__()`` ran: ``dispose`` sees
    # ``_disposed`` already true and returns without touching what is missing.
    _disposed: bool = True
    _source_subscription: Optional[Disposable] = None

    def __init__(self, source: ReadOnlyObservableProtocol[TIn]):
        self._source = source
        self._subscribers: List[Callable[[TOut], None]] = []
        self._held_value: TOut = self._seed(source)
        self._disposed = False
        self._source_subscription = self._subscribe_weakly(source)

    def _seed(self, source: ReadOnlyObservableProtocol[TIn]) -> TOut:
        """What :attr:`value` reports before this observable has emitted anything.

        Called from ``__init__`` before the source subscription exists, so an
        implementation that reads the source sees its construction-time value.
        """
        raise NotImplementedError

    # -- lifetime ----------------------------------------------------------

    def _subscribe_weakly(self, source: ReadOnlyObservableProtocol[TIn]) -> Disposable:
        """Subscribe to ``source`` without letting it hold this object alive.

        The callback closes over a ``weakref`` and never over ``self``; once the
        wrapper is collected the callback becomes a no-op until :meth:`dispose`
        (from ``__del__``) removes it.
        """
        weak_self = weakref.ref(self)

        def on_source_changed(value: TIn) -> None:
            target = weak_self()
            if target is not None:
                target._on_source_changed(value)

        return source.subscribe(mark_internal_subscription(on_source_changed))

    # -- reading ------------------------------------------------------------

    @property
    def value(self) -> TOut:
        """Value this wrapper last emitted, registering **it** as the dependency.

        A derivation built on a wrapper must depend on the wrapper, not on what
        the wrapper reads. Letting an inner read register the source as well
        would hand the derivation a second edge that is unshaped and fires
        first, so the shaping would be bypassed entirely: ``q.debounce(0.3).map(f)``
        recomputed on the keystroke rather than 0.3 s after it. Reads inside
        :meth:`_current_value` are therefore untracked, which matters for any
        subclass that does read its source there.
        """
        tracker = _tracking_context.get()
        if tracker is not None and tracker is not self:
            tracker._register_dependency(self)
        token = _tracking_context.set(None)
        try:
            return self._current_value()
        finally:
            _tracking_context.reset(token)

    def _current_value(self) -> TOut:
        """What :attr:`value` reports: the last emitted value, or the seed.

        Reads made here are not tracked. A subclass that reports something other
        than what it emitted overrides this.
        """
        return self._held_value

    def _clock_callbacks(self) -> Sequence[Callable[[float], None]]:
        """Callbacks this observable may have armed, for :meth:`dispose` to disarm.

        Returned rather than tracked at schedule time because the clock matches
        by equality (see :func:`~nuiitivet.observable.runtime._same_callback`), so
        unscheduling a callback that was never armed is free and harmless.
        """
        return ()

    def dispose(self) -> None:
        """Release the source subscription, disarm timers, drop subscribers.

        Idempotent. After this the wrapper emits nothing and holds nothing.
        """
        if self._disposed:
            return
        self._disposed = True
        for callback in self._clock_callbacks():
            runtime.clock.unschedule(callback)
        if self._source_subscription is not None:
            self._source_subscription.dispose()
            self._source_subscription = None
        self._subscribers.clear()

    def __del__(self) -> None:
        # Interpreter shutdown can clear module globals out from under this, and
        # an exception in __del__ is printed and swallowed rather than raised —
        # noise on a path whose work no longer matters by then.
        try:
            self.dispose()
        except Exception:  # pragma: no cover - shutdown ordering
            pass

    # -- protocol ----------------------------------------------------------

    def _on_source_changed(self, value: TIn) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def _emit_to_subscribers(self, value: TOut) -> None:
        """Publish ``value`` and make it what :attr:`value` reports from now on.

        Held before the callbacks run, so a subscriber that reads back through
        the wrapper sees the value it was just handed.
        """
        self._held_value = value
        for callback in list(self._subscribers):
            callback(value)

    def subscribe(self, callback: Callable[[TOut], None]) -> Disposable:
        self._subscribers.append(callback)

        def _dispose() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                debug_once(
                    logger,
                    f"wrapper_dispose_remove_missing:{type(self).__name__}",
                    "Subscriber callback was already removed",
                )

        return Disposable(_dispose)

    # -- operators ---------------------------------------------------------
    #
    # The same set ``_ObservableValue`` and ``ComputedObservable`` expose, so a
    # chain does not run out of operators partway through. Deliberately not
    # factored into a shared mixin: those two propagate the ``dispatch=False``
    # opt-out into what they build and a wrapper has no opt-out to propagate
    # (§4.4 -- it emits inside a notification its source already marshalled), so
    # the bodies only look alike. ``tests/observable/test_operator_parity.py``
    # asserts the three surfaces stay equal instead.

    def map(self, fn: Callable[[TOut], Any]) -> "ComputedObservable[Any]":
        from .computed import ComputedObservable

        def compute_fn() -> Any:
            return fn(self.value)

        return ComputedObservable(compute_fn)

    def combine(self, *others: ReadOnlyObservableProtocol[Any]) -> "CombineBuilder":
        from .combine import CombineBuilder

        return CombineBuilder(self, *others)

    def filter(self, pred: Callable[[TOut], bool], *, initial: TOut) -> "FilteredObservable[TOut]":
        """Observable of the values passing ``pred``, seeded with ``initial``.

        ``initial`` is required because a filtered observable has no value of
        its own until something passes; see
        :class:`~nuiitivet.observable.filtered.FilteredObservable`.
        """
        from .filtered import FilteredObservable

        return FilteredObservable(self, pred, initial=initial)

    def debounce(self, seconds: float) -> "DebouncedObservable[TOut]":
        from .timed import DebouncedObservable

        return DebouncedObservable(self, seconds)

    def throttle(self, seconds: float) -> "ThrottledObservable[TOut]":
        from .timed import ThrottledObservable

        return ThrottledObservable(self, seconds)

    def switch_map(
        self,
        fn: Callable[[TOut, "CancelToken"], _R],
        *,
        initial: _R,
    ) -> "SwitchMappedObservable[TOut, _R]":
        """Asynchronous :meth:`map`: the newest run's result, older runs discarded.

        See :class:`~nuiitivet.observable.switched.SwitchMappedObservable`.
        """
        from .switched import SwitchMappedObservable

        return SwitchMappedObservable(self, fn, initial=initial)


class ShapingObservable(SourceSubscribingObservable[T, T]):
    """A wrapper that changes *when* or *whether* a value is republished, not what.

    ``debounce``, ``throttle`` and ``filter`` all hand the source's own values
    on, so their input and output types are the same one and the seed is simply
    the source's construction-time value. Naming that here keeps the rule in one
    place: reading the source to seed is correct **because** the types agree,
    which is exactly what ``switch_map`` cannot claim.
    """

    def _seed(self, source: ReadOnlyObservableProtocol[T]) -> T:
        return _read_untracked(source)
