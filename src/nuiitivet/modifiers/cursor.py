from __future__ import annotations

from dataclasses import dataclass

from ..input.cursor import MouseCursor
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import InteractionRegion, ensure_interaction_region


@dataclass(slots=True)
class CursorModifier(ModifierElement):
    """Set the mouse cursor a widget shows while hovered."""

    cursor: MouseCursor

    def apply(self, widget: Widget) -> Widget:
        region: InteractionRegion = ensure_interaction_region(widget)
        region.mouse_cursor = self.cursor
        return region


def cursor(cursor: MouseCursor) -> CursorModifier:
    """Show ``cursor`` while the pointer rests on the widget.

    The cursor set here wins over the one the widget's role calls for: a
    button keeps its pointing hand unless this says otherwise, and keeps the
    one set here while disabled. A descendant with its own answer still
    wins inside its own bounds.

    Args:
        cursor: The shape to show.

    Returns:
        A :class:`CursorModifier` to attach via ``.modifier(...)``.
    """
    return CursorModifier(cursor=cursor)
