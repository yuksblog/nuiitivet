"""defer_pointer() modifier - the widget's own surface yields; children still catch.

One of the four pointer-participation modifiers. While *condition* is truthy the
wrapped widget's own rectangle never becomes the hit target (self yields, S =
none), but hit-testing still descends into the subtree (C), so children keep
catching. Any point not covered by a child falls through to whatever is behind.

This is the explicit form of the ``auto`` default's pass-through posture, useful
when a widget *does* paint a surface (so ``auto`` would make it catch) yet you
still want it to behave like a transparent aligner or overlay — e.g. a decorated
full-size container that must let background clicks through while its children
remain interactive.

Posture pairing: ``defer_pointer`` is the opposite of :func:`absorb_pointer`
(self takes the whole surface and children are blocked). Both touch only the
routing between self and children; :func:`passthrough_pointer` additionally
opens the children.

Usage::

    widget.modifier(defer_pointer())               # always defer
    widget.modifier(defer_pointer(self.vm.overlay)) # observable-driven
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

from ._hit_participation import HitConditionLike, HitParticipationBox

DeferPointerConditionLike = HitConditionLike


class DeferPointerBox(HitParticipationBox):
    """Wrapper whose own surface yields (S = none) while children still catch (C)."""

    def __init__(self, child: Widget, condition: DeferPointerConditionLike = True) -> None:
        super().__init__(child, condition, descend_children=True, self_opaque=False)


@dataclass(slots=True)
class DeferPointerModifier(ModifierElement):
    """Modifier that makes the widget's own surface yield to its children."""

    condition: DeferPointerConditionLike = True

    def apply(self, widget: Widget) -> Widget:
        return DeferPointerBox(widget, self.condition)


def defer_pointer(condition: DeferPointerConditionLike = True) -> DeferPointerModifier:
    """Return a modifier that yields the widget's own surface so children catch.

    Args:
        condition: Static ``bool`` or an ``Observable[bool]``. When truthy the
            widget's own rectangle never catches; children are still hit-tested
            normally. Defaults to ``True``. Read and validated at construction /
            mount, not at first click.

    Returns:
        A :class:`DeferPointerModifier` to apply via ``widget.modifier(...)``.

    Note:
        Only the widget's **own surface** (S) yields; the subtree (C) stays
        interactive. Use :func:`passthrough_pointer` to open the whole subtree.
    """
    return DeferPointerModifier(condition=condition)


__all__ = [
    "DeferPointerBox",
    "DeferPointerModifier",
    "defer_pointer",
]
