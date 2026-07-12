from __future__ import annotations

from ..input.shortcut import ShortcutBinding, ShortcutLike, to_shortcut
from ..widgeting.callbacks import VoidCallback
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import ShortcutNode, ensure_interaction_region


class KeyShortcutModifier(ModifierElement):
    """Bind a key gesture to a callback, scoped to the widget's subtree."""

    def __init__(self, binding: ShortcutBinding) -> None:
        self.binding = binding

    def apply(self, widget: Widget) -> Widget:
        region = ensure_interaction_region(widget)

        node = region.get_node(ShortcutNode)
        if not isinstance(node, ShortcutNode):
            node = ShortcutNode()
            region.add_node(node)
        node.bind(self.binding)

        return region


def key_shortcut(shortcut: ShortcutLike, *, on_trigger: VoidCallback) -> KeyShortcutModifier:
    """Trigger a command when a key gesture fires anywhere inside this subtree.

    The binding is **focus-scoped**: it fires only while the focused widget is
    inside the modified subtree, and only after the focused widget has declined
    the key press — so a focused ``TextField`` still eats a bare ``s`` while an
    unhandled ``Accel+S`` reaches the command here. When two nested subtrees bind
    the same gesture, the innermost one containing focus wins and the outer one
    does not also fire.

    That scoping is what decides *which* target a shortcut acts on: give each
    editor pane its own ``key_shortcut("Accel+S", on_trigger=self.save)`` and
    ``Accel+S`` saves the pane that currently holds focus, with no collision
    between panes.

    Bind the command where it is **owned**, not on whatever widget is nearest.
    A singular app-wide command (New Window, Open, Quit) that must fire with
    nothing focused does not belong here — hanging it off a leaf widget makes it
    silently depend on that widget's focus and mount state.

    Args:
        shortcut: The gesture, as a spec string (``"Accel+S"``, ``"Ctrl+Shift+Z"``)
            or a :class:`~nuiitivet.input.shortcut.Shortcut`. ``Accel`` is the
            primary modifier: Cmd on macOS, Ctrl elsewhere.
        on_trigger: Called with no arguments when the gesture fires. May be sync
            or async; exceptions are logged and contained, as with other key
            callbacks.

    Returns:
        A :class:`KeyShortcutModifier` to attach via ``.modifier(...)``.
    """
    return KeyShortcutModifier(ShortcutBinding(to_shortcut(shortcut), on_trigger))
