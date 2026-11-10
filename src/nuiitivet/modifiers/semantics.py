from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.semantics import SemanticsLabel, SemanticsNode, SemanticsRole, attach_semantics


@dataclass(slots=True)
class SemanticsModifier(ModifierElement):
    """Set what a widget says to assistive technology."""

    label: Optional[SemanticsLabel] = None
    role: Optional[SemanticsRole] = None

    def apply(self, widget: Widget) -> Widget:
        node = widget.semantics_node
        if node is None:
            node = SemanticsNode()
            attach_semantics(widget, node)
        # A part left out keeps what an earlier semantics() wrote.
        if self.label is not None:
            node.label = self.label
        if self.role is not None:
            node.role = self.role
        return widget


def semantics(label: Optional[SemanticsLabel] = None, *, role: Optional[SemanticsRole] = None) -> SemanticsModifier:
    """Set what assistive technology reads for the widget.

    The label and the role set here win over the widget's own. A widget with
    a label hides the text beneath it: the label is read in its place. On a
    widget that says nothing of its own, a layout or an icon, this makes it
    one entry, a group unless ``role`` says otherwise. A list of labels names
    the parts of a widget that has them, a range slider's two handles, in
    their order.

    Args:
        label: The name to read, a string or an observable of one; or one
            name per part, as a list.
        role: What kind of thing the widget is.

    Returns:
        A :class:`SemanticsModifier` to attach via ``.modifier(...)``.
    """
    return SemanticsModifier(label=label, role=role)
