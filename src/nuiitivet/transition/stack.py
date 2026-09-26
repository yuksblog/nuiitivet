from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Iterable, Protocol, TypeVar


class Disposable(Protocol):
    """What the stack runtime needs from an element: a way to release it."""

    def dispose(self) -> None: ...


T = TypeVar("T", bound=Disposable)


class EntryLifecycle(str, Enum):
    """Lifecycle state for an element in a presentation stack."""

    ENTERING = "entering"
    ACTIVE = "active"
    EXITING = "exiting"
    DISPOSED = "disposed"


@dataclass(slots=True)
class StackEntry(Generic[T]):
    """Mutable stack entry used by the shared stack runtime."""

    element: T
    state: EntryLifecycle


class StackRuntime(Generic[T]):
    """Stack state and disposal timing shared by Navigator and Overlay.

    Elements are tracked by identity. Rendering and animation stay in the host
    widget.
    """

    def __init__(
        self,
        *,
        initial: Iterable[T] | None = None,
        pinned: Iterable[T] | None = None,
    ) -> None:
        self._entries: list[StackEntry[T]] = []
        self._pinned_ids: set[int] = {id(element) for element in list(pinned or ())}

        for element in list(initial or ()):  # keep deterministic order
            self._entries.append(StackEntry(element=element, state=EntryLifecycle.ACTIVE))

    @property
    def entries(self) -> tuple[StackEntry[T], ...]:
        return tuple(self._entries)

    @property
    def elements(self) -> list[T]:
        return [entry.element for entry in self._entries if entry.state is not EntryLifecycle.DISPOSED]

    def can_pop(self, *, min_elements: int = 1) -> bool:
        return len(self.elements) > max(0, int(min_elements))

    def push(self, element: T) -> StackEntry[T]:
        entry = StackEntry(element=element, state=EntryLifecycle.ENTERING)
        self._entries.append(entry)
        return entry

    def mark_active(self, element: T) -> bool:
        entry = self._find_entry(element)
        if entry is None:
            return False
        if entry.state is EntryLifecycle.DISPOSED:
            return False
        entry.state = EntryLifecycle.ACTIVE
        return True

    def mark_exiting(self, element: T) -> bool:
        entry = self._find_entry(element)
        if entry is None:
            return False
        if id(element) in self._pinned_ids:
            return False
        if entry.state is EntryLifecycle.DISPOSED:
            return False
        entry.state = EntryLifecycle.EXITING
        return True

    def begin_pop(self) -> T | None:
        for entry in reversed(self._entries):
            if entry.state is EntryLifecycle.DISPOSED:
                continue
            if id(entry.element) in self._pinned_ids:
                continue
            if entry.state is EntryLifecycle.EXITING:
                return entry.element
            entry.state = EntryLifecycle.EXITING
            return entry.element
        return None

    def complete_exit(self, element: T) -> bool:
        entry = self._find_entry(element)
        if entry is None:
            return False

        entry.state = EntryLifecycle.DISPOSED
        try:
            element.dispose()
        finally:
            self._entries = [item for item in self._entries if item.element is not element]
        return True

    def remove(self, element: T) -> bool:
        if not self.mark_exiting(element):
            return False
        return self.complete_exit(element)

    def top(self) -> T | None:
        for entry in reversed(self._entries):
            if entry.state is EntryLifecycle.DISPOSED:
                continue
            return entry.element
        return None

    def _find_entry(self, element: T) -> StackEntry[T] | None:
        for entry in self._entries:
            if entry.element is element:
                return entry
        return None


__all__ = ["Disposable", "EntryLifecycle", "StackEntry", "StackRuntime"]
