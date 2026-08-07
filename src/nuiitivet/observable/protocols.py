from __future__ import annotations

from typing import Callable, Generic, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")
CompareFunc = Callable[[T, T], bool]


class Disposable:
    def __init__(self, dispose_fn: Callable[[], None]):
        self._dispose_fn = dispose_fn
        self._disposed = False

    def dispose(self) -> None:
        if not self._disposed:
            self._dispose_fn()
            self._disposed = True


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

    def changes(self) -> "ReadOnlyObservableProtocol[T]":  # pragma: no cover - overridden
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
        ``compare``, ``dispatch_to_ui`` and batching all behave identically.
        """
        self.value = value


@runtime_checkable
class ReadOnlyObservableProtocol(Protocol, Generic[T]):
    def subscribe(self, cb: Callable[[T], None]) -> Disposable: ...

    def changes(self) -> "ReadOnlyObservableProtocol[T]": ...

    @property
    def value(self) -> T: ...


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
