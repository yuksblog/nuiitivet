"""Links back to an owner that do not keep the owner alive."""

from __future__ import annotations

import weakref
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


def back_reference(target: Optional[T]) -> Callable[[], Optional[T]]:
    """Return a callable that yields ``target`` while it lives, ``None`` after.

    A parent holds its children, a widget holds its engines and nodes; the
    link in the other direction is this one, so a subtree nobody holds any
    more is freed by reference counting alone, with no cycle for the
    collector to find. An object that cannot be weakly referenced is held
    strongly.

    Args:
        target: The owner to link back to, or ``None``.
    """
    if target is None:
        return _none
    try:
        return weakref.ref(target)
    except TypeError:
        return lambda: target


def _none() -> None:
    return None


class weak_method_call:
    """A bound method, called while its instance lives and a no-op after.

    For a callback an owner handed to an object it holds: kept this way, the
    callback does not hold the owner back.
    """

    __slots__ = ("_method",)

    def __init__(self, method: Any) -> None:
        """
        Args:
            method: A bound method.
        """
        self._method = weakref.WeakMethod(method)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        method = self._method()
        if method is None:
            return None
        return method(*args, **kwargs)

    # Equal to the method it stands for, so a list that holds the wrapper
    # still finds and removes the method itself.
    def __eq__(self, other: object) -> bool:
        if isinstance(other, weak_method_call):
            other = other._method()
        method = self._method()
        return method is not None and method == other

    def __hash__(self) -> int:
        method = self._method()
        return hash(method) if method is not None else 0


def is_bound_to(value: Any, owner: Any) -> bool:
    """Whether ``value`` is a method bound to ``owner``."""
    return getattr(value, "__func__", None) is not None and getattr(value, "__self__", None) is owner
