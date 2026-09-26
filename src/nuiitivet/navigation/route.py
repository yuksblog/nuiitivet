from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.transition.spec import TransitionSpec
from nuiitivet.widgeting.widget import Widget


@dataclass(slots=True)
class Route:
    """One screen on a Navigator's stack: its widget and the transition it moves with.

    Internal to ``navigation``; callers push a widget and an optional transition.

    Attributes:
        widget: The screen.
        transition: Enter and exit animation for this screen, kept until it is disposed.
    """

    widget: Widget
    transition: TransitionSpec

    def dispose(self) -> None:
        self.widget.unmount()
