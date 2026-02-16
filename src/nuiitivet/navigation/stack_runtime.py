from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from nuiitivet.navigation.route import Route


class EntryLifecycle(str, Enum):
    """Lifecycle state for a route entry in a navigation stack."""

    ENTERING = "entering"
    ACTIVE = "active"
    EXITING = "exiting"
    DISPOSED = "disposed"


@dataclass(slots=True)
class RouteStackEntry:
    """Mutable stack entry used by the shared route stack runtime."""

    route: Route
    state: EntryLifecycle


class RouteStackRuntime:
    """Shared route stack runtime for Navigator and Overlay modal stack.

    This runtime centralizes route stack state transitions and disposal timing.
    Rendering/animation concerns stay in host widgets.
    """

    def __init__(
        self,
        *,
        initial_routes: Iterable[Route] | None = None,
        pinned_routes: Iterable[Route] | None = None,
    ) -> None:
        self._entries: list[RouteStackEntry] = []
        self._pinned_route_ids: set[int] = {id(route) for route in list(pinned_routes or ())}

        for route in list(initial_routes or ()):  # keep deterministic order
            entry = RouteStackEntry(route=route, state=EntryLifecycle.ACTIVE)
            self._entries.append(entry)

    @property
    def entries(self) -> tuple[RouteStackEntry, ...]:
        return tuple(self._entries)

    @property
    def routes(self) -> list[Route]:
        return [entry.route for entry in self._entries if entry.state is not EntryLifecycle.DISPOSED]

    def can_pop(self, *, min_routes: int = 1) -> bool:
        return len(self.routes) > max(0, int(min_routes))

    def push(self, route: Route) -> RouteStackEntry:
        entry = RouteStackEntry(route=route, state=EntryLifecycle.ENTERING)
        self._entries.append(entry)
        return entry

    def mark_active(self, route: Route) -> bool:
        entry = self._find_entry(route)
        if entry is None:
            return False
        if entry.state is EntryLifecycle.DISPOSED:
            return False
        entry.state = EntryLifecycle.ACTIVE
        return True

    def mark_exiting(self, route: Route) -> bool:
        entry = self._find_entry(route)
        if entry is None:
            return False
        if id(route) in self._pinned_route_ids:
            return False
        if entry.state is EntryLifecycle.DISPOSED:
            return False
        entry.state = EntryLifecycle.EXITING
        return True

    def begin_pop(self) -> Route | None:
        for entry in reversed(self._entries):
            if entry.state is EntryLifecycle.DISPOSED:
                continue
            if id(entry.route) in self._pinned_route_ids:
                continue
            if entry.state is EntryLifecycle.EXITING:
                return entry.route
            entry.state = EntryLifecycle.EXITING
            return entry.route
        return None

    def complete_exit(self, route: Route) -> bool:
        entry = self._find_entry(route)
        if entry is None:
            return False

        entry.state = EntryLifecycle.DISPOSED
        try:
            route.dispose()
        finally:
            self._entries = [item for item in self._entries if item.route is not route]
        return True

    def remove(self, route: Route) -> bool:
        if not self.mark_exiting(route):
            return False
        return self.complete_exit(route)

    def top(self) -> Route | None:
        for entry in reversed(self._entries):
            if entry.state is EntryLifecycle.DISPOSED:
                continue
            return entry.route
        return None

    def _find_entry(self, route: Route) -> RouteStackEntry | None:
        for entry in self._entries:
            if entry.route is route:
                return entry
        return None


__all__ = ["EntryLifecycle", "RouteStackEntry", "RouteStackRuntime"]
