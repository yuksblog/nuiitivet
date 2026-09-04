from __future__ import annotations

from ..input.shortcut import ShortcutBinding, ShortcutLike, ShortcutScope, to_shortcut
from ..widgeting.callbacks import VoidCallback
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..widgets.interaction import ShortcutNode, ensure_interaction_region


class KeyShortcutModifier(ModifierElement):
    """Bind a key gesture to a command, live while the widget's scope condition holds."""

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


def key_shortcut(
    shortcut: ShortcutLike,
    *,
    on_trigger: VoidCallback,
    scope: ShortcutScope = ShortcutScope.FOREGROUND,
) -> KeyShortcutModifier:
    """Trigger a command when a key gesture fires.

    A shortcut is a *command* bound to a gesture, which is a different thing from
    `focusable(on_key=...)` — that one delivers raw keys to the focused widget.
    By default a shortcut does **not** require focus: it is live whenever its
    subtree is on the topmost interactable layer, so a paint canvas gets its
    ``Accel+Z`` without anything being focused.

    The focused widget still gets first refusal on every key, so a focused
    ``TextField`` keeps eating the keys it uses before any shortcut is consulted.

    Bind the command where it is **owned**, not on whatever widget is nearest.
    The owner decides the scope.

    Args:
        shortcut: The gesture, as a spec string (``"Accel+S"``, ``"Ctrl+Shift+Z"``)
            or a :class:`~nuiitivet.input.shortcut.Shortcut`. ``Accel`` is the
            primary modifier: Cmd on macOS, Ctrl elsewhere.
        on_trigger: Called with no arguments when the gesture fires. May be sync
            or async; exceptions are logged and contained, as with other key
            callbacks.
        scope: When the binding is live.
            :attr:`~nuiitivet.input.shortcut.ShortcutScope.FOREGROUND` (default)
            covers almost everything.
            :attr:`~nuiitivet.input.shortcut.ShortcutScope.FOCUS` is for the case
            where the same command has several targets displayed at once (a
            dual-pane file manager, a split-view editor) and only focus can pick
            one. :attr:`~nuiitivet.input.shortcut.ShortcutScope.MOUNT` is for an
            app-wide command, bound on the content root so it survives navigation.

    Returns:
        A :class:`KeyShortcutModifier` to attach via ``.modifier(...)``.
    """
    return KeyShortcutModifier(ShortcutBinding(to_shortcut(shortcut), on_trigger, scope))
