"""Scope predicates for keyboard-shortcut dispatch.

A shortcut's scope asks a question about the widget's place in the tree — is it
displayed? is it merely mounted? — and this module answers it. See
``docs/design/KEYBOARD_SHORTCUTS.md``.
"""

from __future__ import annotations

import logging
from typing import Optional

from nuiitivet.common.logging_once import exception_once
from ..widgeting.widget import Widget

logger = logging.getLogger(__name__)


def is_self_or_descendant(widget: Optional[Widget], ancestor: Widget) -> bool:
    """Return True if ``widget`` is ``ancestor`` or sits below it in the tree."""
    current: Optional[Widget] = widget
    while current is not None:
        if current is ancestor:
            return True
        current = getattr(current, "_parent", None)
    return False


def is_foreground(widget: Widget) -> bool:
    """Return True if ``widget`` is on the topmost interactable layer.

    Being in the tree is not enough. A widget is *not* in the foreground when it
    is hidden by ``visible(False)``, when it sits inside something that is
    currently closed or disabled, when a container keeps it mounted while showing
    other content (a ``Deck`` on another page, a covered navigation route), or
    when a blocking overlay entry is open above it. Each of those means the user
    cannot act on the widget, so its shortcuts must not fire.

    This is deliberately the same set of questions the Tab sequence asks, so a
    shortcut buried in hidden content and a Tab stop buried in hidden content
    agree about being out of reach.
    """
    try:
        if _is_occluded_by_overlay(widget):
            return False
        return _is_displayed(widget)
    except Exception:
        exception_once(logger, "shortcut_is_foreground_exc", "Foreground check raised")
        return False


def _is_occluded_by_overlay(widget: Widget) -> bool:
    from nuiitivet.overlay import Overlay

    try:
        overlay = Overlay.of(widget, root=True)
    except RuntimeError:
        # No App-installed overlay (e.g. a bare widget tree in a test).
        return False

    blocking = overlay.occluding_content_widget()
    if blocking is None:
        return False
    return not is_self_or_descendant(widget, blocking)


def _is_displayed(widget: Widget) -> bool:
    """Walk to the root, rejecting any ancestor that hides ``widget``."""
    from nuiitivet.modifiers.passthrough_pointer import PassthroughPointerBox
    from nuiitivet.widgets.interaction import FocusTraversalBlocker

    parent: Optional[Widget] = getattr(widget, "_parent", None)
    while parent is not None:
        # A blocking ancestor is closed, disabled, or otherwise inert — the same
        # test that drops its subtree out of the Tab sequence.
        if isinstance(parent, FocusTraversalBlocker) and parent.blocks_focus_traversal:
            return False
        # An inert subtree is not on the interactable layer. This is also how
        # visible(False) presents itself: it composes to opacity(0) +
        # passthrough_pointer(True).
        if isinstance(parent, PassthroughPointerBox) and parent._active:
            return False
        if _covers(parent, widget):
            return False
        if _keeps_offstage(parent, widget):
            return False
        parent = getattr(parent, "_parent", None)
    return True


def _keeps_offstage(parent: Widget, widget: Widget) -> bool:
    """Return True if ``parent`` keeps ``widget`` mounted but off its shown content.

    ``focus_traversal_children()`` is where a container declares which of its
    children it is currently showing — a ``Deck`` narrows to the selected page,
    a ``Navigator`` to the top route. Reusing it here is what keeps a
    ``FOREGROUND`` shortcut and a Tab stop from disagreeing about the same
    widget.

    The test is descendant-of-a-shown-child rather than identity, because the
    narrowed list is post-expansion: a ``Deck`` over a ``ForEach`` names the
    fragment it shows, not the ``ForEach`` that owns it.
    """
    try:
        mounted = parent.children_snapshot()
        shown = parent.focus_traversal_children()
    except Exception:
        exception_once(logger, "shortcut_traversal_children_exc", "focus_traversal_children raised")
        return False

    if len(shown) == len(mounted) and all(a is b for a, b in zip(shown, mounted)):
        return False  # Shows everything it owns; it hides nothing.
    if not any(is_self_or_descendant(widget, child) for child in mounted):
        return False  # ``widget`` reaches ``parent`` some other way (a built child).
    return not any(is_self_or_descendant(widget, child) for child in shown)


def _covers(parent: Widget, widget: Widget) -> bool:
    """Return True if ``parent`` is a navigator whose top route does not hold ``widget``.

    Covers both the app ``Navigator`` and the private navigator that stacks
    overlay entries: each keeps every route in the tree and paints only the top.
    The test is descendant-of-the-top-route rather than identity, because a
    navigator wraps each route's widget in transition layers before parenting it.
    """
    stack = getattr(parent, "_stack", None)
    top = getattr(stack, "top", None)
    if not callable(top):
        return False

    top_route = top()
    top_widget = getattr(top_route, "_widget", None)
    if top_widget is None:
        return False
    return not is_self_or_descendant(widget, top_widget)
