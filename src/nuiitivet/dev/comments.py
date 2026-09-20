"""The human's comments: the widgets and areas they marked, and what they wrote on each, for the assistant to pull.

A mark is a node (a widget is the subject) or a region (an area is, whatever
occupies it), numbered in one sequence; each may carry an instruction, and a
bare number is a whole comment. Members are held weakly, matched on object
identity, and re-resolved by structural path after a hot reload, with misses
counted in ``lost``. A region stores only its rect: what it covers is derived
on every read. Written on the UI thread and read on HTTP worker threads, so the
buffer takes a lock.
"""

from __future__ import annotations

import logging
import threading
import weakref
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Optional

from nuiitivet._interaction.perception import (
    _visible_children,
    ancestors,
    describe_state,
    describe_tree,
    enclosing_container,
    intersecting_subtree,
    visible_rect,
)

from .interaction import own_identity, resolve_target
from .source import payload as source_payload
from .snapshot import Path, path_of, widgets_by_path

logger = logging.getLogger(__name__)

Rect = tuple[float, float, float, float]


def _weak_ref(obj: Any) -> Optional[Callable[[], Any]]:
    """Return a weak reference to ``obj``, or ``None`` if it cannot take one."""
    try:
        return weakref.ref(obj)
    except TypeError:
        return None


@dataclass
class _Member:
    """One marked widget."""

    #: Weak, so a mark never keeps a detached subtree alive.
    ref: Callable[[], Any]
    #: ``resolve_target()``-shaped. Never the set key: two keyless siblings share one.
    identity: dict[str, Any]
    #: Structural path, for finding the member again after a reload.
    path: Optional[Path]
    #: ``None`` when the number is the whole comment.
    instruction: Optional[str] = None

    def widget(self) -> Optional[Any]:
        return self.ref()


@dataclass
class _Region:
    """One marked area: the rect the human drew."""

    rect: Rect
    instruction: Optional[str] = None


@dataclass
class Comments:
    """The comment buffer for one running app.

    The marks in order, whether comment mode is on, and a ``seq`` that bumps on
    every change so a poll of ``status`` notices one.
    """

    _marks: list[Any] = field(default_factory=list)
    #: The marks at session start, for :meth:`discard`; ``None`` outside a session.
    _pending: Optional[list[Any]] = None
    #: Snapshots behind and ahead of the marks, for undo and redo. Empty outside a session.
    _history: list[list[Any]] = field(default_factory=list)
    _future: list[list[Any]] = field(default_factory=list)
    _seq: int = 0
    #: ``seq`` at the last change to the marks, and at the last full read.
    _changed_seq: int = 0
    _served_seq: int = 0
    _active: bool = False
    _lost: int = 0
    _lock: threading.RLock = field(default_factory=threading.RLock)

    # --- mode -------------------------------------------------------------

    @property
    def active(self) -> bool:
        """Whether comment mode is on, so the marks may still change."""
        with self._lock:
            return self._active

    def enter(self) -> None:
        """Latch comment mode on. The marks as they stand are what :meth:`discard` returns to."""
        with self._lock:
            if self._active:
                return
            self._pending = list(self._marks)
            self._history, self._future = [], []
            self._active = True
            self._seq += 1

    def commit(self) -> None:
        """Latch comment mode off, keeping what the session marked and wrote."""
        with self._lock:
            if not self._active:
                return
            self._pending = None
            self._history, self._future = [], []
            self._active = False
            self._seq += 1

    def discard(self) -> None:
        """Latch comment mode off, returning the marks to where the session started.

        ``seq`` bumps: a reader mid-session may have seen a mark this removes.
        """
        with self._lock:
            if not self._active:
                return
            self._seq += 1
            if self._pending is not None and self._pending != self._marks:
                self._marks = self._pending
                self._changed_seq = self._seq
            self._pending = None
            self._history, self._future = [], []
            self._active = False

    def undo(self) -> bool:
        """Step the open session back one change. ``False`` when there is none to undo."""
        return self._step(self._history, self._future)

    def redo(self) -> bool:
        """Reapply the change the last undo stepped over. ``False`` when there is none."""
        return self._step(self._future, self._history)

    @property
    def undoable(self) -> bool:
        """Whether the open session has a change to undo."""
        with self._lock:
            return bool(self._history)

    @property
    def redoable(self) -> bool:
        """Whether an undo can be reapplied."""
        with self._lock:
            return bool(self._future)

    def _step(self, source: list[list[Any]], sink: list[list[Any]]) -> bool:
        with self._lock:
            if not self._active or not source:
                return False
            sink.append(self._marks)
            self._marks = source.pop()
            self._seq += 1
            self._changed_seq = self._seq
            return True

    # --- marking ----------------------------------------------------------

    def toggle(self, node: Any, *, root: Any = None) -> bool:
        """Mark ``node``, or remove its mark. Returns ``True`` if it was added.

        Matched on object identity. Without ``root`` the member has no structural
        path and is ``lost`` at the next reload.
        """
        if node is None:
            return False
        with self._lock:
            for index, mark in enumerate(self._marks):
                if isinstance(mark, _Member) and mark.widget() is node:
                    self._checkpoint()
                    del self._marks[index]
                    self._bump()
                    return False
            added = self._make_member(node, root)
            if added is None:
                return False
            self._checkpoint()
            self._marks.append(added)
            self._bump()
            return True

    def add_region(self, rect: Rect) -> None:
        """Mark an area of the screen. A zero-area rect is ignored."""
        x, y, width, height = (float(value) for value in rect)
        if width <= 0 or height <= 0:
            return
        with self._lock:
            self._checkpoint()
            self._marks.append(_Region(rect=(x, y, width, height)))
            self._bump()

    def replace_last(self, node: Any, *, root: Any = None) -> None:
        """Replace the most recently marked widget with ``node``, keeping its text.

        Regions are skipped, so one drawn afterwards does not end the walk. ``root``
        as for :meth:`toggle`.
        """
        if node is None:
            return
        with self._lock:
            replacement = self._make_member(node, root)
            if replacement is None:
                return
            self._checkpoint()
            for index in range(len(self._marks) - 1, -1, -1):
                current = self._marks[index]
                if isinstance(current, _Member):
                    self._marks[index] = replace(replacement, instruction=current.instruction)
                    self._bump()
                    return
            self._marks.append(replacement)
            self._bump()

    def clear(self) -> None:
        """Drop every mark and reset the lost count."""
        with self._lock:
            if not self._marks and not self._lost:
                return
            self._checkpoint()
            self._marks = []
            self._lost = 0
            self._bump()

    def set_instruction(self, index: int, text: str) -> bool:
        """Write ``text`` on the mark numbered ``index``; blank text clears it.

        Returns ``False`` when no live mark has that number.
        """
        instruction = text.strip() or None
        with self._lock:
            for position, mark in self._positions():
                if position == index:
                    if mark.instruction != instruction:
                        self._checkpoint()
                        self._marks[self._marks.index(mark)] = replace(mark, instruction=instruction)
                        self._bump()
                    return True
            return False

    def instruction(self, index: int) -> Optional[str]:
        """What is written on the mark numbered ``index``, or ``None``."""
        with self._lock:
            for position, mark in self._positions():
                if position == index:
                    return mark.instruction
            return None

    def _positions(self) -> list[tuple[int, Any]]:
        """Every live mark with its on-screen number."""
        out: list[tuple[int, Any]] = []
        for mark in self._marks:
            if isinstance(mark, _Member) and mark.widget() is None:
                continue
            out.append((len(out) + 1, mark))
        return out

    def _checkpoint(self) -> None:
        """Snapshot the marks ahead of a change, inside a session."""
        if self._active:
            self._history.append(list(self._marks))
            self._future = []

    def _bump(self) -> None:
        self._seq += 1
        self._changed_seq = self._seq

    def _make_member(self, node: Any, root: Any) -> Optional[_Member]:
        ref = _weak_ref(node)
        if ref is None:
            logger.debug("comments: %s cannot be weakly referenced", type(node).__name__)
            return None
        path: Optional[Path] = None
        if root is not None:
            try:
                path = path_of(root, node)
            except Exception:
                logger.debug("comments: capturing a structural path failed", exc_info=True)
        return _Member(ref=ref, identity=resolve_target(node), path=path)

    # --- reading ----------------------------------------------------------

    def marks(self) -> list[tuple[int, str, Any]]:
        """Return ``(index, kind, mark)`` for every live mark, in order.

        ``kind`` is ``"node"`` (``mark`` is the widget) or ``"region"`` (its rect);
        ``index`` is the 1-based number on the badge. A member whose widget has been
        collected is dropped and the rest renumber.
        """
        with self._lock:
            return [
                (index, "node", mark.widget()) if isinstance(mark, _Member) else (index, "region", mark.rect)
                for index, mark in self._positions()
            ]

    def members(self) -> list[Any]:
        """Return the marked widgets still alive, in order."""
        return [mark for _index, kind, mark in self.marks() if kind == "node"]

    def regions(self) -> list[Rect]:
        """Return the marked areas, in order."""
        return [mark for _index, kind, mark in self.marks() if kind == "region"]

    def last(self) -> Optional[Any]:
        """Return the most recently marked widget, skipping regions, or ``None``."""
        with self._lock:
            for mark in reversed(self._marks):
                if isinstance(mark, _Member):
                    widget = mark.widget()
                    if widget is not None:
                        return widget
        return None

    def summary(self) -> dict[str, Any]:
        """Return the roll-up ``status`` carries.

        ``seq``, ``committed`` (false while comment mode is on), and separate counts
        of nodes, regions and marks with text.
        """
        with self._lock:
            nodes = sum(1 for mark in self._marks if isinstance(mark, _Member))
            return {
                "seq": self._seq,
                "committed": not self._active,
                "nodes": nodes,
                "regions": len(self._marks) - nodes,
                "instructions": sum(1 for mark in self._marks if mark.instruction is not None),
            }

    # --- read receipts ----------------------------------------------------

    @property
    def unread(self) -> bool:
        """Whether the marks changed since the assistant last read them.

        ``False`` while a session is open, and unaffected by a hot reload.
        """
        with self._lock:
            return not self._active and bool(self._marks) and self._changed_seq > self._served_seq

    def served(self) -> None:
        """Record that the full payload was just read."""
        with self._lock:
            self._served_seq = self._seq

    # --- hot reload -------------------------------------------------------

    def restore(self, root: Any) -> int:
        """Re-resolve every marked widget against the rebuilt ``root``; return how many were found.

        Members that cannot be found are dropped and counted in ``lost``. Regions
        are untouched.
        """
        with self._lock:
            if not any(isinstance(mark, _Member) for mark in self._marks):
                return 0
            try:
                by_path = widgets_by_path(root)
            except Exception:
                logger.debug("comments: walking the rebuilt tree failed", exc_info=True)
                return 0

            kept, restored, lost = _remap(self._marks, by_path)
            self._marks = kept
            # The snapshots hold the old objects too; unmapped, a discard or an
            # undo after a reload would bring back members that are gone.
            if self._pending is not None:
                self._pending = _remap(self._pending, by_path)[0]
            self._history = [_remap(marks, by_path)[0] for marks in self._history]
            self._future = [_remap(marks, by_path)[0] for marks in self._future]
            self._lost = lost
            self._seq += 1
            return restored

    @property
    def lost(self) -> int:
        """How many members the last reload failed to re-resolve."""
        with self._lock:
            return self._lost


def _remap(marks: list[Any], by_path: dict[Path, Any]) -> tuple[list[Any], int, int]:
    """Re-resolve the members in ``marks``; return the survivors, how many were found, and how many were lost."""
    kept: list[Any] = []
    restored = 0
    lost = 0
    for mark in marks:
        if isinstance(mark, _Region):
            kept.append(mark)
            continue
        widget = by_path.get(mark.path) if mark.path is not None else None
        ref = _weak_ref(widget) if widget is not None else None
        if ref is None:
            lost += 1
            continue
        kept.append(_Member(ref=ref, identity=resolve_target(widget), path=mark.path, instruction=mark.instruction))
        restored += 1
    return (kept, restored, lost)


def _type_path(node: Any) -> list[str]:
    """Return the root -> node chain of type names, for locating the node in ``describe_tree``."""
    chain = [type(ancestor).__name__ for ancestor in ancestors(node)]
    chain.reverse()
    chain.append(type(node).__name__)
    return chain


def _rect_payload(node: Any) -> Optional[list[float]]:
    # Visible, not layout: a clipped node must not report an area it is not painted in.
    rect = visible_rect(node)
    return None if rect is None else [round(value, 2) for value in rect]


def _brief(node: Any, *, relation: Optional[str] = None) -> dict[str, Any]:
    """Identity and rect of a node named as context.

    ``relation`` is ``None`` for a node that is only on the path to a match.
    """
    info = own_identity(node)
    rect = _rect_payload(node)
    if rect is not None:
        info["rect"] = rect
    if relation is not None:
        info["relation"] = relation
    return info


def _node_payload(index: int, widget: Any, instruction: Optional[str]) -> dict[str, Any]:
    info: dict[str, Any] = {"index": index}
    if instruction is not None:
        # First: the one field in the human's own words.
        info["instruction"] = instruction
    own = own_identity(widget)
    info.update(own)
    # The ``window=`` selector for follow-up calls; absent for a tree no Window owns.
    from nuiitivet.widgeting.context_lookup import find_window

    owner = find_window(widget)
    if owner is not None:
        info["window"] = getattr(owner, "id", None)
    info["path"] = _type_path(widget)
    rect = _rect_payload(widget)
    if rect is not None:
        info["rect"] = rect
    # Absent when sites are not recorded, or no user frame built the widget.
    source = source_payload(widget)
    if source is not None:
        info["source"] = source
    info["tree"] = describe_tree(widget)
    info["state"] = describe_state(widget)
    # How to drive the node, when that differs from what it is: a Text inside a keyed Button.
    target = resolve_target(widget)
    if target != own:
        info["target"] = target
    return info


def _contents_payload(entry: tuple[Any, Optional[str], list[Any]]) -> dict[str, Any]:
    """Render one node of the intersection subtree, recursively."""
    node, relation, children = entry
    info = _brief(node, relation=relation)
    if children:
        info["children"] = [_contents_payload(child) for child in children]
    return info


def _region_payload(index: int, root: Any, rect: Rect, instruction: Optional[str]) -> dict[str, Any]:
    """Describe an area from the tree as it is now.

    ``container`` is the innermost node enclosing the region, with its immediate
    children; ``contents`` is the pruned subtree the box crosses, each node tagged
    ``contained`` or ``clipped``. Both are reported: geometry cannot tell "the gap
    between these" from "these things".
    """
    info: dict[str, Any] = {"index": index}
    if instruction is not None:
        info["instruction"] = instruction
    info["rect"] = [round(value, 2) for value in rect]
    container = enclosing_container(root, rect)
    if container is None:
        info["contents"] = []
        return info
    described = _brief(container)
    described["path"] = _type_path(container)
    described["children"] = [
        _brief(child) for child in _visible_children(container) if child is not None
    ]
    info["container"] = described
    info["contents"] = [
        _contents_payload(entry) for entry in intersecting_subtree(container, rect)
    ]
    return info


def see_comments(root: Any, comments: Optional[Comments]) -> dict[str, Any]:
    """Return the payload the ``see_comments`` tool serves, and count it as read.

    ``nodes`` and ``regions`` are independent lists sharing one ``index``
    sequence, the number on the badge. A member carries ``instruction`` only when
    the human wrote one. Each node carries ``describe_tree`` / ``describe_state``
    scoped to it; each region is derived from the current tree. Call on the UI
    thread.
    """
    if comments is None:
        return {"seq": 0, "committed": True, "nodes": [], "regions": [], "lost_marks": 0}

    summary = comments.summary()
    nodes: list[dict[str, Any]] = []
    regions: list[dict[str, Any]] = []
    for index, kind, mark in comments.marks():
        instruction = comments.instruction(index)
        if kind == "region":
            regions.append(_region_payload(index, root, mark, instruction))
        else:
            nodes.append(_node_payload(index, mark, instruction))
    comments.served()

    return {
        "seq": summary["seq"],
        "committed": summary["committed"],
        "nodes": nodes,
        "regions": regions,
        "lost_marks": comments.lost,
    }


__all__ = ["Comments", "see_comments"]
