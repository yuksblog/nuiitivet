"""ignore_pointer() modifier - block hit-testing for the child subtree.

A single-responsibility primitive: while *condition* is truthy, the wrapped
widget (and its entire subtree) does not respond to pointer / hit events.
Layout and painting are unaffected.

Typical use cases:

* Disabled previews that must look interactive but ignore clicks.
* Drag-source ghosts that should not consume hover/click events.
* Composition target for higher-level modifiers such as :func:`visible`.

Usage::

    widget.modifier(ignore_pointer())              # always block input
    widget.modifier(ignore_pointer(self.vm.busy))  # observable-driven
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import ReadOnlyObservableProtocol
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)


IgnorePointerConditionLike = Union[bool, ReadOnlyObservableProtocol[bool]]


class IgnorePointerBox(Widget):
    """Wrapper widget that blocks hit-testing for its child while *active*."""

    def __init__(self, child: Widget, condition: IgnorePointerConditionLike = True) -> None:
        super().__init__(
            width=child.width_sizing,
            height=child.height_sizing,
            max_children=1,
            overflow_policy="replace_last",
        )
        self._condition: IgnorePointerConditionLike = condition
        self._active: bool = self._read_initial(condition)
        self.add_child(child)

    @staticmethod
    def _read_initial(condition: IgnorePointerConditionLike) -> bool:
        if isinstance(condition, ReadOnlyObservableProtocol):
            try:
                return bool(condition.value)
            except Exception:
                exception_once(
                    logger,
                    "ignore_pointer_initial_condition_exc",
                    "Failed to read ignore_pointer initial condition observable",
                )
                return True
        return bool(condition)

    def on_mount(self) -> None:
        super().on_mount()
        if isinstance(self._condition, ReadOnlyObservableProtocol):
            self.observe(self._condition, self._set_active)

    def _set_active(self, value: bool) -> None:
        next_active = bool(value)
        if next_active == self._active:
            return
        self._active = next_active
        self.invalidate()

    def _child(self) -> Optional[Widget]:
        if not self.children:
            return None
        child = self.children[0]
        if isinstance(child, Widget):
            return child
        return None

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        child = self._child()
        if child is None:
            return super().preferred_size(max_width=max_width, max_height=max_height)
        try:
            return child.preferred_size(max_width=max_width, max_height=max_height)
        except Exception:
            exception_once(
                logger,
                "ignore_pointer_preferred_size_exc",
                "Child preferred_size raised in IgnorePointerBox",
            )
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
            exception_once(
                logger,
                "ignore_pointer_layout_exc",
                "Child layout raised in IgnorePointerBox",
            )

    def hit_test(self, x: int, y: int):
        if self._active:
            return None
        return super().hit_test(x, y)


@dataclass(slots=True)
class IgnorePointerModifier(ModifierElement):
    """Modifier that blocks hit-testing for the wrapped subtree when *condition* is truthy."""

    condition: IgnorePointerConditionLike = True

    def apply(self, widget: Widget) -> Widget:
        return IgnorePointerBox(widget, self.condition)


def ignore_pointer(condition: IgnorePointerConditionLike = True) -> IgnorePointerModifier:
    """Return a modifier that blocks hit-testing for the child subtree.

    Args:
        condition: Static ``bool`` or an ``Observable[bool]``. When truthy the
            child subtree does not receive pointer / hit events. Defaults to
            ``True`` (always block).

    Returns:
        An :class:`IgnorePointerModifier` to apply via ``widget.modifier(...)``.

    Note:
        This modifier only affects hit-testing. Layout space, painting, focus
        traversal and keyboard handling are unaffected. Combine with
        :func:`opacity` to also hide the widget visually.
    """
    return IgnorePointerModifier(condition=condition)


__all__ = [
    "IgnorePointerBox",
    "IgnorePointerModifier",
    "ignore_pointer",
]
