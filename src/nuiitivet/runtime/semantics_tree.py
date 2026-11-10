"""The semantics tree a window assembles from what its widgets say."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Mapping, Optional

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.interaction import (
    FocusNode,
    FocusScope,
    FocusSource,
    FocusTraversalBlocker,
    InteractionHostMixin,
)
from nuiitivet.widgets.semantics import (
    CONTAINER_ROLES,
    Semantics,
    SemanticsAction,
    SemanticsNode,
    SemanticsRole,
)

if TYPE_CHECKING:
    from .window import Window

logger = logging.getLogger(__name__)

#: The id of the entry that stands for the window itself.
ROOT_ID = 0

Rect = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class SemanticsEntry:
    """One entry of a :class:`SemanticsTree`.

    Attributes:
        id: The entry's identity, the same for as long as its node lives.
        semantics: What the entry says.
        rect: Where it is painted, ``(x, y, width, height)`` in the window's
            logical pixels.
        children: The ids of the entries beneath it, in reading order.
        actions: What assistive technology can ask of it.
    """

    id: int
    semantics: Semantics
    rect: Rect
    children: tuple[int, ...] = ()
    actions: frozenset[SemanticsAction] = frozenset()


@dataclass(frozen=True, slots=True)
class SemanticsTree:
    """What a window says to assistive technology at one moment.

    Attributes:
        entries: Every entry by id. The window's own is :data:`ROOT_ID`.
        focus: The id of the entry that holds the keyboard focus, the window's
            own when no widget does.
    """

    entries: Mapping[int, SemanticsEntry]
    focus: int = ROOT_ID


# Where an entry came from: its node, and the index of the part it stands for
# (``-1`` for the widget itself).
_Source = tuple[SemanticsNode, int]


class _Builder:
    """One walk of the window, collecting the entries and where they came from."""

    def __init__(self, window: "Window") -> None:
        self._window = window
        self.entries: dict[int, SemanticsEntry] = {}
        self.sources: dict[int, _Source] = {}
        self._open: set[int] = set()

    def build(self) -> SemanticsTree:
        window = self._window
        top: list[int] = []
        root = window._focus_traversal_root()
        if root is not None:
            self._walk(root, top, None)
        self.entries[ROOT_ID] = SemanticsEntry(
            id=ROOT_ID,
            semantics=Semantics(role=SemanticsRole.GROUP, label=window.title),
            rect=_rect_of(root),
            children=tuple(top),
        )
        return SemanticsTree(entries=self.entries, focus=self._focused_entry())

    def _walk(self, widget: Widget, siblings: list[int], folded: Optional[list[str]]) -> None:
        """Add ``widget``'s subtree beneath ``siblings``.

        ``folded`` collects the text an enclosing control takes as its label;
        ``None`` when no control encloses the widget.
        """
        node = widget.semantics_node
        # A widget that answers with a descendant's node meets it again below.
        said = _describe(node) if node is None or node.id not in self._open else None
        if node is None or said is None:
            if _blocks(widget):
                return
            for child in self._window._focus_traversal_descendants(widget):
                self._walk(child, siblings, folded)
            return

        if said.role is SemanticsRole.TEXT and folded is not None:
            if said.label:
                folded.append(said.label)
            return

        folds = said.label is not None or said.role not in CONTAINER_ROLES
        children: list[int] = []
        text: Optional[list[str]] = [] if folds else None
        if _blocks(widget):
            # Nothing beneath a blocked host is reachable; only its label is read.
            if text is not None:
                self._collect_text(widget, text)
        else:
            self._open.add(node.id)
            for child in self._window._focus_traversal_descendants(widget):
                self._walk(child, children, text)
            self._open.discard(node.id)
        if said.label is None and text:
            said = replace(said, label=" ".join(text))

        rect = _rect_of(widget)
        for index, part in enumerate(_parts(node)):
            part_id = node.part_id(index)
            self._add(part_id, part, rect, (), node, index)
            children.append(part_id)
        self._add(node.id, said, rect, tuple(children), node, -1)
        siblings.append(node.id)

    def _collect_text(self, widget: Widget, text: list[str]) -> None:
        """Append the text beneath ``widget`` to ``text``, adding no entry."""
        for child in self._window._focus_traversal_descendants(widget):
            said = _describe(child.semantics_node)
            if said is not None and said.role is SemanticsRole.TEXT:
                if said.label:
                    text.append(said.label)
            else:
                self._collect_text(child, text)

    def _add(
        self, entry_id: int, said: Semantics, rect: Rect, children: tuple[int, ...], node: SemanticsNode, part: int
    ) -> None:
        self.entries[entry_id] = SemanticsEntry(
            id=entry_id, semantics=said, rect=rect, children=children, actions=_actions(node, said)
        )
        self.sources[entry_id] = (node, part)

    def _focused_entry(self) -> int:
        focused = self._window._focused_node
        owner = focused.owner if focused is not None else None
        widget: Optional[Widget] = owner
        while widget is not None:
            node = widget.semantics_node
            if node is not None and node.id in self.entries:
                if widget is owner:
                    part = _current_stop(widget)
                    if 0 <= part < len(_parts(node)):
                        return node.part_id(part)
                return node.id
            widget = widget._parent  # type: ignore[assignment]
        return ROOT_ID


def _describe(node: Optional[SemanticsNode]) -> Optional[Semantics]:
    if node is None:
        return None
    try:
        return node.describe()
    except Exception:
        exception_once(logger, "semantics_describe_exc", "A widget's semantics raised")
        return None


def _parts(node: SemanticsNode) -> tuple[Semantics, ...]:
    try:
        return tuple(node.parts())
    except Exception:
        exception_once(logger, "semantics_parts_exc", "A widget's semantics parts raised")
        return ()


def _actions(node: SemanticsNode, said: Semantics) -> frozenset[SemanticsAction]:
    if said.disabled:
        return frozenset()
    actions = set()
    owner = node.owner
    if isinstance(owner, InteractionHostMixin) and owner.get_node(FocusNode) is not None:
        actions.add(SemanticsAction.FOCUS)
    if node.supports_activate:
        actions.add(SemanticsAction.ACTIVATE)
    if node.supports_adjust and said.role is SemanticsRole.SLIDER:
        actions.update((SemanticsAction.INCREMENT, SemanticsAction.DECREMENT))
    return frozenset(actions)


def _blocks(widget: Widget) -> bool:
    try:
        return isinstance(widget, FocusTraversalBlocker) and widget.blocks_focus_traversal
    except Exception:
        exception_once(logger, "semantics_blocker_exc", "blocks_focus_traversal raised")
        return False


def _rect_of(widget: Optional[Widget]) -> Rect:
    rect = widget.global_visual_rect if widget is not None else None
    if rect is None:
        return (0.0, 0.0, 0.0, 0.0)
    x, y, w, h = rect
    return (float(x), float(y), float(w), float(h))


def _scope_of(widget: Widget) -> Optional[FocusScope]:
    if not isinstance(widget, InteractionHostMixin):
        return None
    scope = widget.get_node(FocusScope)
    return scope if isinstance(scope, FocusScope) else None


def _current_stop(widget: Widget) -> int:
    scope = _scope_of(widget)
    return scope.policy.current_index() if scope is not None else -1


def build_semantics_tree(window: "Window") -> SemanticsTree:
    """Return what ``window`` says to assistive technology now.

    Must be called on the UI thread, after a layout.
    """
    return _Builder(window).build()


def perform_semantics_action(window: "Window", entry_id: int, action: SemanticsAction) -> bool:
    """Do what assistive technology asked of one entry.

    The action counts as keyboard input: a menu it opens makes its first item
    current, and the focus it moves shows the focus ring.

    Args:
        window: The window the entry belongs to.
        entry_id: The entry's id in the window's current tree.
        action: What to do.

    Returns:
        Whether the entry exists and takes the action.
    """
    builder = _Builder(window)
    builder.build()
    entry = builder.entries.get(entry_id)
    source = builder.sources.get(entry_id)
    if entry is None or source is None or action not in entry.actions:
        return False
    node, part = source
    window._last_input_source = FocusSource.KEYBOARD

    if action is SemanticsAction.FOCUS:
        _focus(node, part)
    elif action is SemanticsAction.ACTIVATE:
        node.activate()
    else:
        node.adjust(part, 1 if action is SemanticsAction.INCREMENT else -1)
    return True


def _focus(node: SemanticsNode, part: int) -> None:
    owner = node.owner
    if not isinstance(owner, InteractionHostMixin):
        return
    focus = owner.get_node(FocusNode)
    if isinstance(focus, FocusNode):
        focus.request_focus(FocusSource.KEYBOARD)
    scope = _scope_of(owner)  # type: ignore[arg-type]
    if part >= 0 and scope is not None:
        scope.policy.set_current(part)


__all__ = [
    "ROOT_ID",
    "SemanticsEntry",
    "SemanticsTree",
    "build_semantics_tree",
    "perform_semantics_action",
]
