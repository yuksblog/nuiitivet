"""ToastRoute for overlay toasts."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.navigation.route import Route


@dataclass(slots=True)
class ToastRoute(Route):
    """A non-modal route shown on the Overlay layer."""

    duration: float = 3.0
