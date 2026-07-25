"""block_pointer() modifier - catch on the whole surface, block what's behind.

One of the four pointer-participation modifiers. While *condition* is truthy the
wrapped widget catches a pointer anywhere on its own rectangle — including
transparent, unpainted areas (self takes, S = all) — so nothing behind it
receives the click. Hit-testing still descends into the subtree first (C), so
the widget's own children remain fully interactive; only points not covered by a
child are caught by the widget itself.

Typical uses are scrims, modal blockers, and expanded (invisible) hit targets
that must swallow background clicks while their contents still work.

Posture pairing: ``block_pointer`` is the opposite of :func:`passthrough_pointer`
(nothing catches and every click passes through to behind). It differs from
:func:`absorb_pointer` only in that children stay clickable, and from the
``auto`` default in that it catches transparent areas too.

Usage::

    widget.modifier(block_pointer())               # always block what's behind
    widget.modifier(block_pointer(self.vm.is_modal)) # observable-driven
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

from ._hit_participation import HitConditionLike, HitParticipationBox

BlockPointerConditionLike = HitConditionLike


class BlockPointerBox(HitParticipationBox):
    """Wrapper whose whole surface catches (S = all) while children still catch (C)."""

    def __init__(self, child: Widget, condition: BlockPointerConditionLike = True) -> None:
        super().__init__(child, condition, descend_children=True, self_opaque=True)


@dataclass(slots=True)
class BlockPointerModifier(ModifierElement):
    """Modifier that makes the widget's whole surface catch, blocking what's behind."""

    condition: BlockPointerConditionLike = True

    def apply(self, widget: Widget) -> Widget:
        return BlockPointerBox(widget, self.condition)


def block_pointer(condition: BlockPointerConditionLike = True) -> BlockPointerModifier:
    """Return a modifier that catches on the whole surface to block widgets behind.

    Args:
        condition: Static ``bool`` or an ``Observable[bool]``. When truthy the
            widget's whole rectangle catches (including transparent areas), so
            nothing behind receives the pointer; children are still hit-tested
            first. Defaults to ``True``. Read and validated at construction /
            mount, not at first click.

    Returns:
        A :class:`BlockPointerModifier` to apply via ``widget.modifier(...)``.

    Note:
        Only the widget's **own surface** (S) is widened; the subtree (C) stays
        interactive. Use :func:`passthrough_pointer` to open the whole subtree,
        or :func:`absorb_pointer` to also take clicks away from children.
    """
    return BlockPointerModifier(condition=condition)


__all__ = [
    "BlockPointerBox",
    "BlockPointerModifier",
    "block_pointer",
]
