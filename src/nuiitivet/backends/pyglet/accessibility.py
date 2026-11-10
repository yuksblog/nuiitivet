"""The AccessKit bridge: a window's semantics tree, handed to the OS.

The OS side is an AccessKit adapter the platform module installs on the OS
window. This module turns a :class:`SemanticsTree` into the ``TreeUpdate``
the adapter takes, answers the adapter's two callbacks, and pushes an update
after a frame.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol

import accesskit

from nuiitivet.common.logging_once import exception_once
from nuiitivet.runtime.semantics_tree import ROOT_ID, SemanticsEntry, SemanticsTree
from nuiitivet.widgets.semantics import Semantics, SemanticsAction, SemanticsRole, ToggleState

if TYPE_CHECKING:
    from nuiitivet.runtime.window import Window

logger = logging.getLogger(__name__)

_ROLES = {
    SemanticsRole.BUTTON: accesskit.Role.BUTTON,
    SemanticsRole.CHECKBOX: accesskit.Role.CHECK_BOX,
    SemanticsRole.SWITCH: accesskit.Role.SWITCH,
    SemanticsRole.RADIO_BUTTON: accesskit.Role.RADIO_BUTTON,
    SemanticsRole.RADIO_GROUP: accesskit.Role.RADIO_GROUP,
    SemanticsRole.SLIDER: accesskit.Role.SLIDER,
    SemanticsRole.TEXT_FIELD: accesskit.Role.TEXT_INPUT,
    SemanticsRole.MENU: accesskit.Role.MENU,
    SemanticsRole.MENU_ITEM: accesskit.Role.MENU_ITEM,
    SemanticsRole.TEXT: accesskit.Role.LABEL,
    SemanticsRole.IMAGE: accesskit.Role.IMAGE,
    SemanticsRole.GROUP: accesskit.Role.GROUP,
}

_TOGGLED = {
    ToggleState.OFF: accesskit.Toggled.FALSE,
    ToggleState.ON: accesskit.Toggled.TRUE,
    ToggleState.MIXED: accesskit.Toggled.MIXED,
}

_ACTIONS = {
    SemanticsAction.FOCUS: accesskit.Action.FOCUS,
    SemanticsAction.ACTIVATE: accesskit.Action.CLICK,
    SemanticsAction.INCREMENT: accesskit.Action.INCREMENT,
    SemanticsAction.DECREMENT: accesskit.Action.DECREMENT,
}


def _action_of(requested: Any) -> Optional[SemanticsAction]:
    # An AccessKit action compares equal but does not hash.
    for action, ak_action in _ACTIONS.items():
        if ak_action == requested:
            return action
    return None


class Adapter(Protocol):
    """What the bridge needs of an AccessKit platform adapter."""

    def update_if_active(self, update_factory: Callable[[], Any]) -> Any: ...

    def update_view_focus_state(self, is_focused: bool) -> Any: ...


def _node(entry: SemanticsEntry) -> accesskit.Node:
    said = entry.semantics
    node = accesskit.Node(accesskit.Role.WINDOW if entry.id == ROOT_ID else _ROLES[said.role])
    if said.role is SemanticsRole.TEXT:
        # A static text's words are its value; VoiceOver reads a label's
        # value and a button's label.
        node.set_value(said.label or "")
    elif said.label is not None:
        node.set_label(said.label)
    if said.value is not None and said.role is not SemanticsRole.TEXT:
        node.set_value(said.value)
    if said.toggled is not None:
        node.set_toggled(_TOGGLED[said.toggled])
    if said.selected is not None:
        node.set_selected(said.selected)
    if said.disabled:
        node.set_disabled()
    if said.numeric_value is not None:
        node.set_numeric_value(float(said.numeric_value))
    if said.min_value is not None:
        node.set_min_numeric_value(float(said.min_value))
    if said.max_value is not None:
        node.set_max_numeric_value(float(said.max_value))
    x, y, w, h = entry.rect
    node.set_bounds(accesskit.Rect(x, y, x + w, y + h))
    node.set_children(list(entry.children))
    for action in entry.actions:
        node.add_action(_ACTIONS[action])
    return node


def tree_update(tree: SemanticsTree, pixel_ratio: float) -> accesskit.TreeUpdate:
    """Return ``tree`` as the whole-tree update AccessKit takes.

    Args:
        tree: What the window says now.
        pixel_ratio: Backing pixels per logical pixel; the rects go out in
            backing pixels through the root's transform.
    """
    update = accesskit.TreeUpdate(tree.focus)
    ak_tree = accesskit.Tree(ROOT_ID)
    ak_tree.toolkit_name = "nuiitivet"
    update.tree = ak_tree
    for entry_id, entry in tree.entries.items():
        node = _node(entry)
        if entry_id == ROOT_ID:
            scale = float(pixel_ratio)
            node.set_transform(accesskit.Affine([scale, 0.0, 0.0, scale, 0.0, 0.0]))
        update.nodes.append((entry_id, node))
    return update


class AccessKitBridge:
    """Keeps one window's tree in an AccessKit adapter.

    The adapter's callbacks run inside the adapter: one that raises aborts the
    process, and one that updates the tree deadlocks. So the two callbacks
    here catch everything and only queue. An action runs on the next loop
    turn, through ``defer``.
    """

    def __init__(
        self,
        window: "Window",
        *,
        pixel_ratio: Callable[[], float],
        defer: Callable[[Callable[[], None]], None],
    ) -> None:
        """Initialize the bridge.

        Args:
            window: The window whose tree is handed over.
            pixel_ratio: Returns the OS window's backing pixels per logical pixel.
            defer: Runs a callable on the next turn of the UI loop.
        """
        self._window = window
        self._pixel_ratio = pixel_ratio
        self._defer = defer
        self._adapter: Optional[Adapter] = None

    def attach(self, adapter: Adapter) -> None:
        """Hand the bridge the adapter installed with its callbacks."""
        self._adapter = adapter

    def build(self) -> accesskit.TreeUpdate:
        """Return the window's whole tree as an update, laying the window out first if it never was."""
        window = self._window
        root = window.root
        if root is not None and root.layout_rect is None:
            from nuiitivet._interaction.action import settle

            settle(window)
        return tree_update(window.semantics_tree(), self._pixel_ratio())

    def activation_handler(self) -> accesskit.TreeUpdate:
        """The adapter's first ask: the whole tree. Never raises."""
        try:
            return self.build()
        except Exception:
            exception_once(logger, "accesskit_activation_exc", "Building the semantics tree raised")
            # A tree without its root is one the adapter cannot take.
            empty = SemanticsEntry(id=ROOT_ID, semantics=Semantics(role=SemanticsRole.GROUP), rect=(0.0, 0.0, 0.0, 0.0))
            return tree_update(SemanticsTree(entries={ROOT_ID: empty}), 1.0)

    def action_handler(self, request: Any) -> None:
        """The adapter's action: queued for the next loop turn. Never raises."""
        try:
            action = _action_of(request.action)
            target = int(request.target)
        except Exception:
            exception_once(logger, "accesskit_action_request_exc", "Reading an accessibility action raised")
            return
        if action is None:
            return

        def perform() -> None:
            try:
                self._window.perform_semantics_action(target, action)
            except Exception:
                exception_once(logger, "accesskit_action_perform_exc", "Performing an accessibility action raised")
            self.sync()

        try:
            self._defer(perform)
        except Exception:
            exception_once(logger, "accesskit_action_defer_exc", "Queueing an accessibility action raised")

    def sync(self) -> None:
        """Push the tree, when an assistive technology is listening."""
        adapter = self._adapter
        if adapter is None:
            return
        try:
            events = adapter.update_if_active(self.build)
            if events is not None:
                events.raise_events()
        except Exception:
            exception_once(logger, "accesskit_sync_exc", "Pushing the semantics tree raised")

    def set_view_focused(self, focused: bool) -> None:
        """Tell the adapter whether the OS window holds the keyboard focus."""
        adapter = self._adapter
        if adapter is None:
            return
        try:
            events = adapter.update_view_focus_state(bool(focused))
            if events is not None:
                events.raise_events()
        except Exception:
            exception_once(logger, "accesskit_view_focus_exc", "Updating the view focus state raised")


__all__ = ["AccessKitBridge", "Adapter", "tree_update"]
