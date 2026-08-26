from __future__ import annotations

from typing import Optional

from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import (
    FileDropCallback,
    InteractionRegion,
    ensure_interaction_region,
)


class DropTargetModifier(ModifierElement):
    """Opt a widget into receiving OS file drops.

    The window routes a file drop (pyglet ``on_file_drop``) to the innermost
    widget under the drop point that accepts drops; ancestors only receive it
    when no descendant consumed it first.
    """

    def __init__(self, *, on_drop: Optional[FileDropCallback] = None) -> None:
        self.on_drop = on_drop

    def apply(self, widget: Widget) -> Widget:
        region: InteractionRegion = ensure_interaction_region(widget)
        region.enable_file_drop(on_drop=self.on_drop)
        return region


def drop_target(on_drop: Optional[FileDropCallback] = None) -> DropTargetModifier:
    """Receive OS file paths dropped onto the widget.

    The callback may be sync or async and receives a
    :class:`~nuiitivet.input.events.FileDropEvent` whose ``paths`` holds the
    dropped files as :class:`~pathlib.Path` objects. The event's ``local_x`` /
    ``local_y`` are relative to the widget's top-left; ``x`` / ``y`` are window
    coordinates of the drop point.

    Args:
        on_drop: Called when files are dropped on the widget.

    Returns:
        A :class:`DropTargetModifier` to attach via ``.modifier(...)``.
    """
    return DropTargetModifier(on_drop=on_drop)
