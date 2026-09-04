"""Shared hit-participation wrapper box for the pointer-modifier family.

One mechanism, several intent-named entry points. The public modifiers
(:func:`passthrough_pointer`, :func:`defer_pointer`, :func:`block_pointer`,
:func:`absorb_pointer`) all wrap their child in a
:class:`HitParticipationBox` configured with two boolean axes:

* ``descend_children`` — the **C** axis: whether hit-testing descends into the
  wrapped subtree.
* ``self_opaque`` — the **S** axis: whether the box's own rectangle catches a
  hit that no child claimed.

These map onto the internal S / C hit-testing model without ever exposing the
S tri-state or any string enum publicly. Each modifier fixes the two flags to name one posture:

========================== ================ ================
Modifier                   ``descend``      ``self_opaque``
========================== ================ ================
``defer_pointer()``        ``True``         ``False``
``block_pointer()``        ``True``         ``True``
``absorb_pointer()``       ``False``        ``True``
``passthrough_pointer()``  ``False``        ``False``
========================== ================ ================

The box only overrides hit-testing while its *condition* is truthy; when the
condition is falsy it falls back to the ``auto`` default (a transparent wrapper
that defers to its child). Layout and painting are always pass-through.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import ObservableBase
from nuiitivet.widgeting.widget import Widget

logger = logging.getLogger(__name__)


HitConditionLike = Union[bool, ObservableBase[bool]]


class HitParticipationBox(Widget):
    """Single-child wrapper that overrides its subtree's hit participation.

    While *condition* is truthy the box resolves hits through the shared
    :meth:`WidgetKernel._resolve_hit` helper using the fixed ``descend_children``
    (C) and ``self_opaque`` (S) axes. While falsy it defers to the ``auto``
    default. Layout, painting, focus traversal and keyboard handling are
    unaffected.
    """

    def __init__(
        self,
        child: Widget,
        condition: HitConditionLike = True,
        *,
        descend_children: bool,
        self_opaque: bool,
    ) -> None:
        super().__init__(
            width=child.width_sizing,
            height=child.height_sizing,
            max_children=1,
            overflow_policy="replace_last",
        )
        self._condition: HitConditionLike = condition
        self._descend_children: bool = descend_children
        self._self_opaque: bool = self_opaque
        # Validate / read the condition now, at construction -- not at first click.
        self._active: bool = self._read_initial(condition)
        self.add_child(child)

    @staticmethod
    def _read_initial(condition: HitConditionLike) -> bool:
        if isinstance(condition, ObservableBase):
            try:
                return bool(condition.value)
            except Exception:
                exception_once(
                    logger,
                    "hit_participation_initial_condition_exc",
                    "Failed to read hit-participation initial condition observable",
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
                "hit_participation_preferred_size_exc",
                "Child preferred_size raised in HitParticipationBox",
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
                "hit_participation_layout_exc",
                "Child layout raised in HitParticipationBox",
            )

    def hit_test(self, x: int, y: int):
        if not self._active:
            # Inactive: behave as a transparent wrapper (the ``auto`` default),
            # deferring to the child's own hit_test (self + children).
            return super().hit_test(x, y)
        # The wrapped widget fills this box at the origin, so its C axis (its own
        # children) is reached with the same coordinates. Descending into the
        # child's *children* -- rather than the child itself -- lets the S axis
        # (the wrapped widget's own surface) be governed entirely by this box,
        # so e.g. ``defer_pointer`` suppresses a painted widget's self-catch.
        child_hit = None
        if self._descend_children:
            child = self._child()
            if child is not None:
                child_hit = child._hit_test_children(x, y)
        return self._resolve_hit(x, y, child_hit=child_hit, self_opaque=self._self_opaque)


__all__ = [
    "HitConditionLike",
    "HitParticipationBox",
]
