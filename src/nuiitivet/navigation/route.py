from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final

from nuiitivet.widgeting.widget import Widget


TransitionName = str


@dataclass(slots=True)
class Route:
    """A unit of navigation.

    Notes:
        This is intentionally minimal for Phase 3.
    """

    builder: Callable[[], Widget]
    transition: TransitionName = "fade"

    _widget: Widget | None = None

    def build_widget(self) -> Widget:
        if self._widget is None:
            self._widget = self.builder()
        return self._widget

    def dispose(self) -> None:
        if self._widget is None:
            return

        self._widget.unmount()
        self._widget = None


class PageRoute(Route):
    """Route for a page widget."""

    DEFAULT_TRANSITION: Final[TransitionName] = "fade"

    def __init__(self, builder: Callable[[], Widget], transition: TransitionName | None = None) -> None:
        super().__init__(builder=builder, transition=transition or self.DEFAULT_TRANSITION)
