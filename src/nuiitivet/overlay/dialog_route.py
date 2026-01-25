"""DialogRoute for modal overlay dialogs."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.navigation.route import Route


@dataclass(slots=True)
class DialogRoute(Route):
    """A modal route shown on the Overlay layer."""

    barrier_color: tuple[int, int, int, int] = (0, 0, 0, 128)
    barrier_dismissible: bool = True
