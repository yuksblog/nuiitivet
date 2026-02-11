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


@runtime_checkable
class ReadOnlyObservableProtocol(Protocol, Generic[T]):
    def subscribe(self, cb: Callable[[T], None]) -> Disposable: ...

    def changes(self) -> "ReadOnlyObservableProtocol[T]": ...

    @property
    def value(self) -> T: ...


class ObservableProtocol(ReadOnlyObservableProtocol[T], Protocol, Generic[T]):
    """Mutable observable protocol: supports reading and writing .value."""

    @property
    def value(self) -> T: ...

    @value.setter
    def value(self, v: T) -> None: ...
