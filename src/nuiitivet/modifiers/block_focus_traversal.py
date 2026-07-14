"""block_focus_traversal() modifier - keep a subtree out of the Tab sequence.

A single-responsibility primitive: while *condition* is truthy, the wrapped
widget (and its entire subtree) is skipped by Tab / Shift+Tab traversal, and
focus currently held inside it is released. Layout, painting and hit-testing
are unaffected.

Typical use cases:

* Content that is on screen but not reachable by keyboard (a hidden panel that
  keeps its layout space).
* Composition target for higher-level modifiers such as :func:`visible`.

Usage::

    widget.modifier(block_focus_traversal())              # always block
    widget.modifier(block_focus_traversal(self.vm.busy))  # observable-driven
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import ObservableBase
from nuiitivet.widgets.interaction import FocusTraversalBlocker
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)


BlockFocusTraversalConditionLike = Union[bool, ObservableBase[bool]]


class BlockFocusTraversalBox(FocusTraversalBlocker, Widget):
    """Wrapper widget that hides its child subtree from focus traversal while *active*."""

    def __init__(self, child: Widget, condition: BlockFocusTraversalConditionLike = True) -> None:
        super().__init__(
            width=child.width_sizing,
            height=child.height_sizing,
            max_children=1,
            overflow_policy="replace_last",
        )
        self._condition: BlockFocusTraversalConditionLike = condition
        self._active: bool = self._read_initial(condition)
        self.add_child(child)

    @staticmethod
    def _read_initial(condition: BlockFocusTraversalConditionLike) -> bool:
        if isinstance(condition, ObservableBase):
            try:
                return bool(condition.value)
            except Exception:
                exception_once(
                    logger,
                    "block_focus_traversal_initial_condition_exc",
                    "Failed to read block_focus_traversal initial condition observable",
                )
                return True
        return bool(condition)

    def on_mount(self) -> None:
        super().on_mount()
        if isinstance(self._condition, ObservableBase):
            self.observe(self._condition, self._set_active)

    def _set_active(self, value: bool) -> None:
        next_active = bool(value)
        if next_active == self._active:
            return
        self._active = next_active
        self.invalidate()

    @property
    def blocks_focus_traversal(self) -> bool:
        return self._active

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
                "block_focus_traversal_preferred_size_exc",
                "Child preferred_size raised in BlockFocusTraversalBox",
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
                "block_focus_traversal_layout_exc",
                "Child layout raised in BlockFocusTraversalBox",
            )


@dataclass(slots=True)
class BlockFocusTraversalModifier(ModifierElement):
    """Modifier that removes the wrapped subtree from Tab traversal when *condition* is truthy."""

    condition: BlockFocusTraversalConditionLike = True

    def apply(self, widget: Widget) -> Widget:
        return BlockFocusTraversalBox(widget, self.condition)


def block_focus_traversal(
    condition: BlockFocusTraversalConditionLike = True,
) -> BlockFocusTraversalModifier:
    """Return a modifier that removes the child subtree from focus traversal.

    Args:
        condition: Static ``bool`` or an ``Observable[bool]``. When truthy the
            child subtree is skipped by Tab / Shift+Tab, and focus held inside
            it is released. Defaults to ``True`` (always block).

    Returns:
        A :class:`BlockFocusTraversalModifier` to apply via ``widget.modifier(...)``.

    Note:
        This modifier only affects keyboard traversal. Layout, painting and
        hit-testing are unaffected; combine with :func:`ignore_pointer` and
        :func:`opacity` (or simply use :func:`visible`) to hide a subtree from
        every input path.
    """
    return BlockFocusTraversalModifier(condition=condition)


__all__ = [
    "BlockFocusTraversalBox",
    "BlockFocusTraversalModifier",
    "block_focus_traversal",
]
