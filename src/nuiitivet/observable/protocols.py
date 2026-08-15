from __future__ import annotations

from typing import Callable, Generic, Optional, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
CompareFunc = Callable[[T, T], bool]

# The read-only protocol only ever hands a value *out* -- from ``value``, and
# into the callback ``subscribe`` is given -- so it is covariant, and a
# ``ReadOnlyObservableProtocol[Dog]`` is usable where one of ``Animal`` is
# wanted. ``ObservableProtocol`` re-declares the parameter as invariant,
# because writing ``value`` puts a T back in.
T_co = TypeVar("T_co", covariant=True)


# Called with every Disposable as it is constructed, when something is watching.
#
# ``None`` in production, and the ``is not None`` below is the whole cost there.
# It is installed by ``nuiitivet.testing`` alone
# (``testing/_leaks.py``), which is the only place that can do anything with a
# subscription: a widget that forgets to dispose one keeps mutating an unmounted
# tree, and this is the one point every subscription passes through. Every
# ``subscribe`` implementation in the package -- ``value.py``, ``computed.py``,
# and both in ``timed.py`` -- returns a ``Disposable`` built here, and
# ``Animatable.subscribe`` delegates to the first, so watching this constructor
# watches all of them without patching any.
_subscription_tracker: Optional[Callable[["Disposable"], None]] = None


def _set_subscription_tracker(tracker: Optional[Callable[["Disposable"], None]]) -> None:
    """Test-support only: install or clear the subscription tracker."""
    global _subscription_tracker
    _subscription_tracker = tracker


# Set on a subscriber callback that is an edge of the observable graph itself --
# a wrapper's subscription to its source, a computed's to a dependency -- rather
# than an app or widget subscribing to observe a value.
_INTERNAL_SUBSCRIPTION_ATTR = "_nuiitivet_internal_subscription"

_C = TypeVar("_C", bound=Callable[..., None])


def mark_internal_subscription(callback: _C) -> _C:
    """Tag ``callback`` as the observable graph subscribing to itself.

    The leak check reports subscriptions that outlive the widget that made them;
    these belong to no widget and are released with the observable that owns
    them, so they must be exempt. Marking is explicit rather than inferred
    because the shape these callbacks happen to have -- a closure over a
    ``weakref`` and nothing else -- is an implementation detail that has already
    drifted once: it left ``ComputedObservable``'s dependency edges classified as
    app subscriptions while ``debounce``'s were exempt, though the leak check
    documented both as exempt.
    """
    setattr(callback, _INTERNAL_SUBSCRIPTION_ATTR, True)
    return callback


def is_internal_subscription(callback: object) -> bool:
    """Whether ``callback`` was tagged by :func:`mark_internal_subscription`."""
    return getattr(callback, _INTERNAL_SUBSCRIPTION_ATTR, False) is True


def _already_disposed() -> None:
    """Stand-in installed by :meth:`Disposable.dispose`, so the real closure frees."""


class Disposable:
    def __init__(self, dispose_fn: Callable[[], None]):
        self._dispose_fn = dispose_fn
        self._disposed = False
        if _subscription_tracker is not None:
            _subscription_tracker(self)

    @property
    def is_disposed(self) -> bool:
        """Whether :meth:`dispose` has run.

        Public because a test asserting that a widget cleaned up after itself has
        no other way to ask, and the harness's own leak check reads it.
        """
        return self._disposed

    def dispose(self) -> None:
        if not self._disposed:
            self._dispose_fn()
            self._disposed = True
            # Drop the closure, which holds the observable and the subscriber --
            # and, for an operator chain, every wrapper between them. Keeping it
            # would pin all of that for as long as this object lives, which for a
            # widget's ``bind()`` list is until the widget itself is collected.
            # Safe because ``dispose`` never runs the closure twice, and the leak
            # check only reads ``_dispose_fn`` on subscriptions still undisposed.
            self._dispose_fn = _already_disposed


class ObservableBase(Generic[T]):
    """Concrete base for all observables (read-capable).

    Every built-in observable subclasses this so hot paths can use a pure-C
    ``isinstance(value, ObservableBase)`` check instead of the much slower
    ``@runtime_checkable`` Protocol instance check (which, on CPython < 3.12,
    runs the metaclass ``__instancecheck__`` in Python and ``hasattr``-probes
    every member on every call).

    The read interface is declared here so an ``ObservableBase`` value is also a
    structural :class:`ReadOnlyObservableProtocol`, letting callers keep the
    Protocol as the wider static type where duck typing is still wanted.
    Subclasses provide the real implementations; the stubs never run.
    """

    __slots__ = ()

    def subscribe(self, cb: Callable[[T], None]) -> Disposable:  # pragma: no cover - overridden
        raise NotImplementedError

    @property
    def value(self) -> T:  # pragma: no cover - overridden
        raise NotImplementedError


class MutableObservableBase(ObservableBase[T]):
    """Concrete base for observables whose ``value`` is writable.

    Runtime counterpart of :class:`ObservableProtocol` (mirrors what
    :class:`ObservableBase` is to :class:`ReadOnlyObservableProtocol`).
    """

    __slots__ = ()

    @property
    def value(self) -> T:  # pragma: no cover - overridden
        raise NotImplementedError

    @value.setter
    def value(self, v: T) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def set(self, value: T) -> None:
        """Write *value*, for places where a statement is not allowed.

        A Python lambda cannot assign, so writes in expression position - a
        callback prop, a ``subscribe`` lambda - would otherwise need
        ``setattr(obs, "value", v)``::

            on_click=lambda: expanded.set(not expanded.value)

        Prefer the plain ``obs.value = v`` wherever a statement fits; this is
        the same write, not a second write path, so equality de-duping,
        ``compare``, UI-thread dispatch and batching all behave identically.
        """
        self.value = value


@runtime_checkable
class ReadOnlyObservableProtocol(Protocol, Generic[T_co]):
    def subscribe(self, cb: Callable[[T_co], None]) -> Disposable: ...

    @property
    def value(self) -> T_co: ...


@runtime_checkable
class ObservableProtocol(ReadOnlyObservableProtocol[T], Protocol, Generic[T]):
    """Mutable observable protocol: supports reading and writing .value.

    Note:
        ``isinstance`` against a runtime-checkable protocol only inspects
        attribute *presence*, and a property's setter is invisible to it - so
        this check separates mutable from read-only only because ``set`` exists
        on one and not the other. A duck-typed observable that has a writable
        ``value`` but no ``set`` therefore does not match; subclass
        :class:`MutableObservableBase` to get both.
    """

    @property
    def value(self) -> T: ...

    @value.setter
    def value(self, v: T) -> None: ...

    def set(self, value: T) -> None: ...
