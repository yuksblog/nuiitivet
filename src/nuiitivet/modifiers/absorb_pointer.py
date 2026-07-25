"""absorb_pointer() modifier - one-piece surface that takes clicks from children.

One of the four pointer-participation modifiers. While *condition* is truthy the
wrapped widget catches every pointer on its own rectangle (self takes, S = all)
and does **not** descend into its children (C = none): the whole subtree behaves
as a single opaque piece. Clicks that would otherwise land on a child are
absorbed by the widget itself, and nothing behind receives them.

The canonical use is a disabled or "one-piece" overlay: a composite that should
present as a single non-interactive slab even though it is built from
interactive children.

Posture pairing: ``absorb_pointer`` is the opposite of :func:`defer_pointer`
(self yields and children keep catching). Contrast with :func:`block_pointer`,
which also catches the whole surface but keeps children clickable, and with
:func:`passthrough_pointer`, which lets clicks fall **through** the whole subtree
rather than absorbing them.

Usage::

    widget.modifier(absorb_pointer())                # always absorb
    widget.modifier(absorb_pointer(self.vm.disabled)) # observable-driven
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

from ._hit_participation import HitConditionLike, HitParticipationBox

AbsorbPointerConditionLike = HitConditionLike


class AbsorbPointerBox(HitParticipationBox):
    """Wrapper whose whole surface catches (S = all) and does not descend (C = none)."""

    def __init__(self, child: Widget, condition: AbsorbPointerConditionLike = True) -> None:
        super().__init__(child, condition, descend_children=False, self_opaque=True)


@dataclass(slots=True)
class AbsorbPointerModifier(ModifierElement):
    """Modifier that catches on the whole surface and takes clicks from children."""

    condition: AbsorbPointerConditionLike = True

    def apply(self, widget: Widget) -> Widget:
        return AbsorbPointerBox(widget, self.condition)


def absorb_pointer(
    condition: AbsorbPointerConditionLike = True,
) -> AbsorbPointerModifier:
    """Return a modifier that makes the subtree a single opaque, click-absorbing piece.

    Args:
        condition: Static ``bool`` or an ``Observable[bool]``. When truthy the
            widget's whole rectangle catches and hit-testing does not descend
            into children, so the subtree acts as one opaque slab. Defaults to
            ``True``. Read and validated at construction / mount, not at first
            click.

    Returns:
        An :class:`AbsorbPointerModifier` to apply via ``widget.modifier(...)``.

    Note:
        Both the self surface (S = all) and children (C = none) are affected,
        but the widget still catches — clicks are **absorbed**, not passed
        through. Use :func:`passthrough_pointer` to make the subtree
        click-through instead.
    """
    return AbsorbPointerModifier(condition=condition)


__all__ = [
    "AbsorbPointerBox",
    "AbsorbPointerModifier",
    "absorb_pointer",
]
