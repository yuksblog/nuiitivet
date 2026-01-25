from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable, Optional, Tuple

from nuiitivet.common.logging_once import exception_once

from ..rendering.sizing import SizingLike
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget


_logger = logging.getLogger(__name__)


WillPopCallback = Callable[[], bool]


class WillPopScope(Widget):
    """A wrapper widget that can intercept back navigation.

    This widget is created by the `will_pop()` modifier.
    """

    def __init__(
        self,
        child: Widget,
        *,
        on_will_pop: WillPopCallback,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Tuple[int, int, int, int]] = None,
    ) -> None:
        super().__init__(width=width, height=height, padding=padding, max_children=1, overflow_policy="replace_last")
        self._on_will_pop = on_will_pop
        self.add_child(child)

    def _child(self) -> Optional[Widget]:
        if not self.children:
            return None
        child = self.children[0]
        if isinstance(child, Widget):
            return child
        return None

    def handle_back_event(self) -> bool:
        """Return True to continue back action, False to cancel."""

        child = self._child()
        if child is not None:
            handler = getattr(child, "handle_back_event", None)
            if callable(handler):
                try:
                    if not bool(handler()):
                        return False
                except Exception:
                    # Fail open to avoid trapping navigation.
                    exception_once(_logger, "will_pop_child_handle_back_exc", "Child handle_back_event raised")
                    return True

        try:
            return bool(self._on_will_pop())
        except Exception:
            exception_once(_logger, "will_pop_callback_exc", "on_will_pop callback raised")
            return True

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        child = self._child()
        if child is None:
            return super().preferred_size(max_width=max_width, max_height=max_height)
        try:
            return child.preferred_size(max_width=max_width, max_height=max_height)
        except Exception:
            exception_once(_logger, "will_pop_child_preferred_size_exc", "Child preferred_size raised")
            return super().preferred_size(max_width=max_width, max_height=max_height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        child = self._child()
        if child is None:
            return
        try:
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)
        except Exception:
            exception_once(_logger, "will_pop_child_layout_exc", "Child layout/set_layout_rect raised")

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        child = self._child()
        if child is None:
            return

        if child.layout_rect is None:
            self.layout(width, height)
        try:
            child.set_last_rect(x, y, width, height)
            child.paint(canvas, x, y, width, height)
        except Exception:
            exception_once(_logger, "will_pop_child_paint_exc", "Child paint raised")

    def hit_test(self, x: int, y: int):
        child = self._child()
        if child is not None:
            hit = child.hit_test(x, y)
            if hit is not None:
                return hit
        return super().hit_test(x, y)


@dataclass(slots=True)
class WillPopModifier(ModifierElement):
    on_will_pop: WillPopCallback

    def apply(self, widget: Widget) -> Widget:
        return WillPopScope(
            widget,
            on_will_pop=self.on_will_pop,
            width=widget.width_sizing,
            height=widget.height_sizing,
            padding=widget.padding,
        )


def will_pop(on_will_pop: WillPopCallback) -> WillPopModifier:
    """Create a will-pop modifier.

    Args:
        on_will_pop: Callback that returns True to continue pop, False to cancel.
    """

    return WillPopModifier(on_will_pop=on_will_pop)
