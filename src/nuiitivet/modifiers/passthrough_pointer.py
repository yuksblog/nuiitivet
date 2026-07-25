"""passthrough_pointer() modifier - the whole subtree lets clicks pass through.

One of the four pointer-participation modifiers, and the whole-subtree end of the
family. While *condition* is truthy neither the wrapped widget nor its children
catch (self yields, S = none; children off, C = none), so every click passes
straight through to whatever is behind. Layout and painting are unaffected.

It is a thin alias over the shared :class:`HitParticipationBox` machinery with
both axes off. Contrast with :func:`defer_pointer` (only the self-surface yields;
children still catch) and :func:`block_pointer` (self catches; children still
work).

Posture pairing: ``passthrough_pointer`` is the opposite of :func:`block_pointer`
(the whole surface catches and nothing passes behind).

Typical use cases:

* Disabled previews that must look interactive but let clicks through.
* Drag-source ghosts that should not consume hover/click events.
* Composition target for higher-level modifiers such as :func:`visible`.

Usage::

    widget.modifier(passthrough_pointer())              # always pass through
    widget.modifier(passthrough_pointer(self.vm.busy))  # observable-driven
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

from ._hit_participation import HitConditionLike, HitParticipationBox

PassthroughPointerConditionLike = HitConditionLike


class PassthroughPointerBox(HitParticipationBox):
    """Wrapper widget whose whole subtree is click-through while *active*.

    A thin specialisation of :class:`HitParticipationBox` with both axes off
    (``descend_children=False``, ``self_opaque=False``): the whole subtree lets
    clicks pass through while the condition holds.
    """

    def __init__(self, child: Widget, condition: PassthroughPointerConditionLike = True) -> None:
        super().__init__(child, condition, descend_children=False, self_opaque=False)


@dataclass(slots=True)
class PassthroughPointerModifier(ModifierElement):
    """Modifier that lets clicks pass through the wrapped subtree when *condition* is truthy."""

    condition: PassthroughPointerConditionLike = True

    def apply(self, widget: Widget) -> Widget:
        return PassthroughPointerBox(widget, self.condition)


def passthrough_pointer(
    condition: PassthroughPointerConditionLike = True,
) -> PassthroughPointerModifier:
    """Return a modifier that lets clicks pass through the whole child subtree.

    Unlike :func:`defer_pointer` and :func:`block_pointer`, which only retune the
    widget's own surface (S) and keep descending into children (C), this modifier
    turns off the **whole subtree**: neither the child nor the wrapper catches, so
    clicks fall through to widgets behind.

    Args:
        condition: Static ``bool`` or an ``Observable[bool]``. When truthy the
            child subtree does not receive pointer / hit events, letting clicks
            pass through. Defaults to ``True`` (always pass through). Read and
            validated at construction / mount, not at first click.

    Returns:
        A :class:`PassthroughPointerModifier` to apply via ``widget.modifier(...)``.

    Note:
        This modifier only affects hit-testing. Layout space, painting, focus
        traversal and keyboard handling are unaffected. Combine with
        :func:`opacity` to also hide the widget visually.
    """
    return PassthroughPointerModifier(condition=condition)


__all__ = [
    "PassthroughPointerBox",
    "PassthroughPointerModifier",
    "passthrough_pointer",
]
