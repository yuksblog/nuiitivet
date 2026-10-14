"""The human's comments: the marked widgets and areas, each with its thread, for the agent to pull and answer.

A mark is a widget or a region, numbered in one sequence, and carries a
thread: the human's lines and the agent's answers in order; a bare number is
a whole comment. The human sends the marks to the agent; a send ends the undo
session and wakes whoever waits on the buffer. Widgets are held weakly,
matched on object identity, and re-resolved by structural path after a hot
reload, with misses counted in ``lost``. A region stores only its rect; what
it covers is derived on every read. Written on the UI thread and read on HTTP
worker threads, so the buffer takes a lock.
"""

from __future__ import annotations

import logging
import threading
import time
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

#: What an agent's answer can say about a comment.
OUTCOMES = ("done", "refused", "question")


def _weak_ref(obj: Any) -> Optional[Callable[[], Any]]:
    """Return a weak reference to ``obj``, or ``None`` if it cannot take one."""
    try:
        return weakref.ref(obj)
    except TypeError:
        return None


@dataclass(frozen=True)
class Line:
    """One line of a mark's thread.

    Attributes:
        by: ``"human"`` or ``"agent"``.
        text: The line itself.
        outcome: On an agent's line, one of :data:`OUTCOMES`; ``None`` on the human's.
    """

    by: str
    text: str
    outcome: Optional[str] = None

    def payload(self) -> dict[str, Any]:
        """The line as ``see_comments`` serves it."""
        info: dict[str, Any] = {"by": self.by}
        if self.outcome is not None:
            info["outcome"] = self.outcome
        info["text"] = self.text
        return info


Thread = tuple[Line, ...]


@dataclass
class _Member:
    """One marked widget."""

    #: Weak, so a mark never keeps a detached subtree alive.
    ref: Callable[[], Any]
    #: ``resolve_target()``-shaped. Never the set key: two keyless siblings share one.
    identity: dict[str, Any]
    #: Structural path, for finding the member again after a reload.
    path: Optional[Path]
    #: Empty when the number is the whole comment.
    thread: Thread = ()
    #: Sent, and no answer yet.
    awaiting: bool = False

    def widget(self) -> Optional[Any]:
        return self.ref()


@dataclass
class _Region:
    """One marked area: the rect the human drew."""

    rect: Rect
    thread: Thread = ()
    awaiting: bool = False


def _outcome(mark: Any) -> Optional[str]:
    """The outcome of the agent's answer that ends the thread, or ``None`` while the human's turn stands."""
    if mark.thread and mark.thread[-1].by == "agent":
        return mark.thread[-1].outcome
    return None


def _same(a: Any, b: Any) -> bool:
    """Whether two mark records, possibly from different snapshots, are the same mark."""
    if isinstance(a, _Member) and isinstance(b, _Member):
        widget = a.widget()
        return widget is not None and widget is b.widget()
    return isinstance(a, _Region) and isinstance(b, _Region) and a.rect == b.rect


@dataclass
class Comments:
    """The comment buffer for one running app.

    The marks in order, whether comment mode is on, a ``seq`` that bumps on
    every change so a poll of ``status`` notices one, and ``sent``, the ``seq``
    the human last sent to the agent.
    """

    _marks: list[Any] = field(default_factory=list)
    #: Snapshots behind and ahead of the marks, for undo and redo. Cleared by a send.
    _history: list[list[Any]] = field(default_factory=list)
    _future: list[list[Any]] = field(default_factory=list)
    _seq: int = 0
    #: ``seq`` at the last change to the marks, and at the last send.
    _changed_seq: int = 0
    _sent_seq: int = 0
    _active: bool = False
    _lost: int = 0
    #: ``True`` once the app is going down, so a wait returns instead of holding its thread.
    _closed: bool = False
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _sent: threading.Condition = field(init=False)

    def __post_init__(self) -> None:
        self._sent = threading.Condition(self._lock)

    # --- mode -------------------------------------------------------------

    @property
    def active(self) -> bool:
        """Whether comment mode is on, so the marks may still change."""
        with self._lock:
            return self._active

    def enter(self) -> None:
        """Latch comment mode on. The marks, and what can be undone, are as they were left."""
        with self._lock:
            if self._active:
                return
            self._active = True
            self._seq += 1

    def leave(self) -> None:
        """Latch comment mode off. Every mark stays, sent or not, for the next session to go on from."""
        with self._lock:
            if not self._active:
                return
            self._active = False
            self._seq += 1

    def send(self) -> bool:
        """Send the marks to the agent: wake every :meth:`wait` and end the undo session.

        Every mark without an answer is ``awaiting`` one from here on.
        ``False``, and nothing done, when nothing changed since the last send.
        """
        with self._lock:
            if not self.unsent:
                return False
            self._marks = [replace(mark, awaiting=True) if _outcome(mark) is None else mark for mark in self._marks]
            self._sent_seq = self._seq
            self._history, self._future = [], []
            self._sent.notify_all()
            return True

    @property
    def unsent(self) -> bool:
        """Whether the marks changed since the last send."""
        with self._lock:
            return self._changed_seq > self._sent_seq

    def wait(self, since: int, timeout: float) -> bool:
        """Block until a send leaves ``sent`` above ``since``, or ``timeout`` seconds pass.

        ``True`` on a send, ``False`` on the timeout or once the buffer is
        closed. Call off the UI thread: the send comes from it.
        """
        deadline = time.monotonic() + max(0.0, timeout)
        with self._sent:
            while self._sent_seq <= since and not self._closed:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._sent.wait(remaining)
            return self._sent_seq > since

    def close(self) -> None:
        """Release every :meth:`wait`, as the app goes down."""
        with self._sent:
            self._closed = True
            self._sent.notify_all()

    def undo(self) -> bool:
        """Step the marks back one change, no further than the last send. ``False`` when there is none to undo."""
        return self._step(self._history, self._future)

    def redo(self) -> bool:
        """Reapply the change the last undo stepped over. ``False`` when there is none."""
        return self._step(self._future, self._history)

    @property
    def undoable(self) -> bool:
        """Whether there is a change since the last send to undo."""
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

    def add(self, node: Any, *, root: Any = None) -> bool:
        """Mark ``node``. Returns ``True`` if it was added; ``False`` when it was marked already.

        Matched on object identity. Without ``root`` the member has no structural
        path and is ``lost`` at the next reload.
        """
        if node is None:
            return False
        with self._lock:
            if any(isinstance(mark, _Member) and mark.widget() is node for mark in self._marks):
                return False
            added = self._make_member(node, root)
            if added is None:
                return False
            self._checkpoint()
            self._marks.append(added)
            self._bump()
            return True

    def remove(self, index: int) -> bool:
        """Drop the mark numbered ``index``. Returns ``True`` if there was one."""
        with self._lock:
            for position, mark in self._positions():
                if position == index:
                    self._checkpoint()
                    self._marks.remove(mark)
                    self._bump()
                    return True
            return False

    def index_of(self, node: Any) -> Optional[int]:
        """The number of the mark on ``node``, or ``None`` when it carries none."""
        with self._lock:
            for position, mark in self._positions():
                if isinstance(mark, _Member) and mark.widget() is node:
                    return position
            return None

    def add_region(self, rect: Rect) -> None:
        """Mark an area of the screen. A zero-area rect is ignored."""
        x, y, width, height = (float(value) for value in rect)
        if width <= 0 or height <= 0:
            return
        with self._lock:
            self._checkpoint()
            self._marks.append(_Region(rect=(x, y, width, height)))
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

    def write(self, index: int, text: str) -> bool:
        """Write ``text`` as the human's newest line on the mark numbered ``index``.

        A human line ending the thread is replaced, and blank text removes it;
        after an agent's answer the text is a new line, and blank text changes
        nothing. Returns ``False`` when no live mark has that number.
        """
        line = text.strip()
        with self._lock:
            for position, mark in self._positions():
                if position != index:
                    continue
                thread = mark.thread[:-1] if self.editable_line(index) is not None else mark.thread
                if line:
                    thread = thread + (Line("human", line),)
                if thread != mark.thread:
                    self._checkpoint()
                    self._marks[self._marks.index(mark)] = replace(mark, thread=thread, awaiting=False)
                    self._bump()
                return True
            return False

    def editable_line(self, index: int) -> Optional[str]:
        """The human's line ending the thread on mark ``index``, which the field opens with, or ``None``."""
        with self._lock:
            thread = self.thread(index)
            if thread and thread[-1].by == "human":
                return thread[-1].text
            return None

    def thread(self, index: int) -> Thread:
        """The lines on the mark numbered ``index``, oldest first; empty for a bare mark or no such mark."""
        with self._lock:
            for position, mark in self._positions():
                if position == index:
                    return mark.thread
            return ()

    def awaiting(self, index: int) -> bool:
        """Whether mark ``index`` was sent and has no answer yet; ``False`` too when no mark has that number."""
        with self._lock:
            for position, mark in self._positions():
                if position == index:
                    return bool(mark.awaiting)
            return False

    def outcome(self, index: int) -> Optional[str]:
        """The outcome of the agent's answer that ends the thread on mark ``index``.

        ``"done"``, ``"refused"`` or ``"question"``; ``None`` while the human's
        turn stands, or when no mark has that number.
        """
        with self._lock:
            for position, mark in self._positions():
                if position == index:
                    return _outcome(mark)
            return None

    # --- answering --------------------------------------------------------

    def answer(self, index: int, outcome: str, text: str) -> bool:
        """Append the agent's answer to the thread on mark ``index``. ``False`` when there is no such mark.

        ``seq`` does not bump, since the agent wrote it, and the answer is not
        the human's to undo: the undo history carries it too.
        """
        if outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {', '.join(OUTCOMES)}, not {outcome!r}")
        line = Line("agent", text.strip(), outcome)
        with self._lock:
            for position, mark in self._positions():
                if position != index:
                    continue
                self._marks = _answered(self._marks, mark, line)
                self._history = [_answered(marks, mark, line) for marks in self._history]
                self._future = [_answered(marks, mark, line) for marks in self._future]
                return True
            return False

    def _positions(self) -> list[tuple[int, Any]]:
        """Every live mark with its on-screen number."""
        out: list[tuple[int, Any]] = []
        for mark in self._marks:
            if isinstance(mark, _Member) and mark.widget() is None:
                continue
            out.append((len(out) + 1, mark))
        return out

    def _checkpoint(self) -> None:
        """Snapshot the marks ahead of a change, for undo."""
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

    def summary(self) -> dict[str, Any]:
        """Return the roll-up ``status`` carries.

        ``seq``, ``sent``, the ``seq`` the human last sent, and separate counts
        of nodes, regions and marks with text.
        """
        with self._lock:
            nodes = sum(1 for mark in self._marks if isinstance(mark, _Member))
            return {
                "seq": self._seq,
                "sent": self._sent_seq,
                "nodes": nodes,
                "regions": len(self._marks) - nodes,
                "instructions": sum(1 for mark in self._marks if any(line.by == "human" for line in mark.thread)),
            }

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
            # The snapshots hold the old objects too; unmapped, an undo after a
            # reload would bring back members that are gone.
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
        kept.append(replace(mark, ref=ref, identity=resolve_target(widget)))
        restored += 1
    return (kept, restored, lost)


def _answered(marks: list[Any], mark: Any, line: Line) -> list[Any]:
    """``marks`` with ``line`` appended to the thread of the record that is ``mark``, which awaits no more."""
    return [
        replace(entry, thread=entry.thread + (line,), awaiting=False) if _same(entry, mark) else entry
        for entry in marks
    ]


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


def _node_payload(index: int, widget: Any, thread: Thread, awaiting: bool) -> dict[str, Any]:
    # The thread first: the human's own words, and what was answered already.
    info: dict[str, Any] = {"index": index, "awaiting": awaiting, "thread": [line.payload() for line in thread]}
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


def _region_payload(index: int, root: Any, rect: Rect, thread: Thread, awaiting: bool) -> dict[str, Any]:
    """Describe an area from the tree as it is now.

    ``container`` is the innermost node enclosing the region, with its immediate
    children; ``contents`` is the pruned subtree the box crosses, each node tagged
    ``contained`` or ``clipped``.
    """
    info: dict[str, Any] = {"index": index, "awaiting": awaiting, "thread": [line.payload() for line in thread]}
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
    """Return the payload the ``see_comments`` tool serves.

    ``nodes`` and ``regions`` are independent lists sharing one ``index``
    sequence, the number on the badge. Each carries its ``thread``, the human's
    lines and the agent's answers in order, empty for a bare mark, and
    ``awaiting``, whether it was sent and has no answer yet. Each node carries
    ``describe_tree`` / ``describe_state`` scoped to it; each region is derived
    from the current tree. ``sent`` is what a wait for the next send starts
    from. Call on the UI thread.
    """
    if comments is None:
        return {"seq": 0, "sent": 0, "nodes": [], "regions": [], "lost_marks": 0}

    summary = comments.summary()
    nodes: list[dict[str, Any]] = []
    regions: list[dict[str, Any]] = []
    for index, kind, mark in comments.marks():
        thread = comments.thread(index)
        awaiting = comments.awaiting(index)
        if kind == "region":
            regions.append(_region_payload(index, root, mark, thread, awaiting))
        else:
            nodes.append(_node_payload(index, mark, thread, awaiting))

    return {
        "seq": summary["seq"],
        "sent": summary["sent"],
        "nodes": nodes,
        "regions": regions,
        "lost_marks": comments.lost,
    }


__all__ = ["OUTCOMES", "Comments", "Line", "see_comments"]
