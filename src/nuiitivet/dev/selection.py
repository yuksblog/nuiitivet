"""The human's designation buffer: what they *pointed at*, for the assistant to pull.

The dev bridge already carries perception (``describe_tree`` / ``describe_state``
/ ``screenshot``), action (``click`` / ``scroll`` / ``type`` / ``key``) and the
journals that let an assistant catch up on what the human *did*. This module adds
the one thing missing in the human -> assistant direction: a record of what the
human *means*. The human enters inspect mode, designates widgets and areas, and
leaves; the assistant reads the result on its own turn. Nothing is pushed.

It is an **annotation** surface, not an inspector: the audience is another party,
so a designation is deliberately multiple, persistent, and has to survive until
that party reads it -- including across the hot reload that the assistant's own
fix triggers.

**Two kinds of designation, not two modes.** A node says "*these widgets* are the
subject" and its rect is incidental; a region says "*this area* is the subject"
and whatever happens to be there is context. They are independent and
simultaneous, sharing one ordinal sequence because they share one on-screen
numbering.

Three boundaries are load-bearing:

* **Members are held weakly and keyed on object identity.** Two anonymous
  siblings resolve to the same ``{"type", "label"}`` dict, so keying the set on
  the resolved identity would make picking the second one deselect the first --
  the trap ``InteractionRecorder.on_mouse_scroll`` already avoids with
  ``coalesce=previous is handler``. The resolved identity is kept alongside, for
  display and payload only.
* **A reload is the normal case, not an edge case.** The whole point is
  "designate, then have the assistant fix it", so a rebuild lands in the middle
  of essentially every use. Members are therefore re-resolved by the same
  key-preferring structural path :mod:`nuiitivet.dev.snapshot` restores state
  with, and any that fail are counted in ``lost`` rather
  than silently dropped -- an assistant reasoning over a quietly truncated set is
  the worst available outcome.
* **Leaving is a decision, not a side effect.** ``Enter`` keeps what the session
  designated, ``Esc`` rolls it back to where the session started -- the reading
  those keys have everywhere. An earlier design made leaving an implicit commit,
  on the grounds that a designation is a note rather than a transaction; that
  reasoning missed the plain absence of a way to throw a session away.
* **A region stores only its rect.** What it contains is derived on every read,
  never frozen when it was drawn. That is what carries it across a reload for
  free, and what turns it into a continuing observation point: read it again
  after a fix and it reports what occupies the area now.

Designation happens on the UI thread (the input handlers the human drives);
reads happen on HTTP worker threads, so the buffer is guarded by a lock -- the
same shape as the reload and interaction journals.
"""

from __future__ import annotations

import logging
import threading
import weakref
from dataclasses import dataclass, field
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
    """One designated widget, held weakly with its identity kept separately."""

    #: Weak, so a designation never keeps a detached subtree alive. A dead
    #: referent reads as a member that is simply gone.
    ref: Callable[[], Any]
    #: ``resolve_target()``-shaped, so a member is directly usable as a
    #: ``click --key`` target. Display and payload only -- never the set key.
    identity: dict[str, Any]
    #: Structural path, captured at designation time so the member can be found
    #: again in the tree a reload rebuilds.
    path: Optional[Path]

    def widget(self) -> Optional[Any]:
        return self.ref()


@dataclass
class _Region:
    """One designated area, held as the rect the human drew, and nothing else."""

    rect: Rect


@dataclass
class Selection:
    """The designation buffer for one running app.

    Holds the marks the human made -- widgets and areas, in one ordered
    sequence -- whether inspect mode is currently on, and a monotonic ``seq``
    that bumps on every change, which is what lets an assistant notice a
    designation happened by polling the cheap ``status`` summary rather than the
    full payload.

    Nodes and regions share one order because they share one on-screen numbering:
    the human says "the second one" and means the second mark they made,
    whichever kind it was.
    """

    _marks: list[Any] = field(default_factory=list)
    #: The marks as they stood when inspect mode was entered, so leaving can
    #: either keep the session's work or throw it away. ``None`` when the mode is
    #: off, which is also what makes :meth:`discard` a no-op outside a session.
    _pending: Optional[list[Any]] = None
    _seq: int = 0
    _active: bool = False
    _lost: int = 0
    _lock: threading.RLock = field(default_factory=threading.RLock)

    # --- mode -------------------------------------------------------------

    @property
    def active(self) -> bool:
        """Whether inspect mode is on, i.e. the set may still be growing."""
        with self._lock:
            return self._active

    def enter(self) -> None:
        """Latch inspect mode on, remembering what to fall back to.

        The snapshot is what makes :meth:`discard` mean "this session", not
        "everything". Re-entering to add one more mark and then changing your
        mind must not take the earlier marks with it.
        """
        with self._lock:
            if self._active:
                return
            self._pending = list(self._marks)
            self._active = True
            self._seq += 1

    def commit(self) -> None:
        """Latch inspect mode off, keeping what the session designated."""
        with self._lock:
            if not self._active:
                return
            self._pending = None
            self._active = False
            self._seq += 1

    def discard(self) -> None:
        """Latch inspect mode off, rolling the session back.

        A rollback rather than an undo of history: marks go live the moment they
        are made, so an assistant reading mid-session may have seen one that this
        removes. ``seq`` bumps here too, so it can tell the state moved.
        """
        with self._lock:
            if not self._active:
                return
            if self._pending is not None:
                self._marks = self._pending
            self._pending = None
            self._active = False
            self._seq += 1

    # --- designation ------------------------------------------------------

    def toggle(self, node: Any, *, root: Any = None) -> bool:
        """Add ``node`` to the designation, or remove it if already designated.

        Keyed on **object identity**, not on the resolved identity: two keyless
        siblings of the same type resolve identically, and keying on that would
        make designating the second one remove the first.

        Args:
            node: The widget the human picked.
            root: The mounted root, used to capture the member's structural path
                for reload re-resolution. **A member designated without one
                cannot survive a reload** and is reported in ``lost``; omit it
                only where no reload can intervene (tests).

        Returns:
            ``True`` if the node was added, ``False`` if it was removed.
        """
        if node is None:
            return False
        with self._lock:
            for index, mark in enumerate(self._marks):
                if isinstance(mark, _Member) and mark.widget() is node:
                    del self._marks[index]
                    self._seq += 1
                    return False
            added = self._make_member(node, root)
            if added is None:
                return False
            self._marks.append(added)
            self._seq += 1
            return True

    def add_region(self, rect: Rect) -> None:
        """Designate an area of the screen.

        The case node picking cannot express: a region with no widget in it. A
        zero-area rect is ignored -- that is a click the gesture layer failed to
        classify, not an area.
        """
        x, y, width, height = (float(value) for value in rect)
        if width <= 0 or height <= 0:
            return
        with self._lock:
            self._marks.append(_Region(rect=(x, y, width, height)))
            self._seq += 1

    def replace_last(self, node: Any, *, root: Any = None) -> None:
        """Replace the most recently designated **widget** with ``node``.

        The ancestor / descendant walk: the human designated roughly the right
        place and is now moving up or down the chain from it, which reads as one
        designation being refined rather than several being made. Regions are
        skipped -- a walk has no meaning for an area, so one drawn afterwards
        does not put the walk out of reach.

        Takes ``root`` for the same reason :meth:`toggle` does, and it is just as
        load-bearing: a refined member without a structural path is silently
        unable to survive the reload the assistant's own fix triggers.
        """
        if node is None:
            return
        with self._lock:
            replacement = self._make_member(node, root)
            if replacement is None:
                return
            for index in range(len(self._marks) - 1, -1, -1):
                if isinstance(self._marks[index], _Member):
                    self._marks[index] = replacement
                    self._seq += 1
                    return
            self._marks.append(replacement)
            self._seq += 1

    def remove_last(self) -> None:
        """Drop the most recent designation, whichever kind it was."""
        with self._lock:
            if not self._marks:
                return
            self._marks.pop()
            self._seq += 1

    def clear(self) -> None:
        """Drop every designation and reset the lost count."""
        with self._lock:
            if not self._marks and not self._lost:
                return
            self._marks.clear()
            self._lost = 0
            self._seq += 1

    def _make_member(self, node: Any, root: Any) -> Optional[_Member]:
        ref = _weak_ref(node)
        if ref is None:
            logger.debug("selection: %s cannot be weakly referenced", type(node).__name__)
            return None
        path: Optional[Path] = None
        if root is not None:
            try:
                path = path_of(root, node)
            except Exception:
                logger.debug("selection: capturing a structural path failed", exc_info=True)
        return _Member(ref=ref, identity=resolve_target(node), path=path)

    # --- reading ----------------------------------------------------------

    def marks(self) -> list[tuple[int, str, Any]]:
        """Return ``(index, kind, mark)`` for every live designation, in order.

        ``kind`` is ``"node"`` (``mark`` is the widget) or ``"region"`` (``mark``
        is its rect). ``index`` is the shared 1-based ordinal the on-screen badge
        shows, so it stays meaningful across both kinds. A member whose referent
        has been collected is dropped and the rest close ranks -- the numbering
        describes what is on screen now, not what once was.
        """
        with self._lock:
            out: list[tuple[int, str, Any]] = []
            for mark in self._marks:
                if isinstance(mark, _Member):
                    widget = mark.widget()
                    if widget is None:
                        continue
                    out.append((len(out) + 1, "node", widget))
                else:
                    out.append((len(out) + 1, "region", mark.rect))
            return out

    def members(self) -> list[Any]:
        """Return the designated widgets that are still alive, in designation order."""
        return [mark for _index, kind, mark in self.marks() if kind == "node"]

    def regions(self) -> list[Rect]:
        """Return the designated areas, in designation order."""
        return [mark for _index, kind, mark in self.marks() if kind == "region"]

    def last(self) -> Optional[Any]:
        """Return the most recently designated widget, or ``None``.

        Regions are skipped: this answers the ancestor walk, which has meaning
        only for a node.
        """
        with self._lock:
            for mark in reversed(self._marks):
                if isinstance(mark, _Member):
                    widget = mark.widget()
                    if widget is not None:
                        return widget
        return None

    def summary(self) -> dict[str, Any]:
        """Return the cheap roll-up ``status`` carries.

        The counts are kept separate rather than summed: "3 nodes" and "3
        regions" mean different things to whoever reads it.
        """
        with self._lock:
            nodes = sum(1 for mark in self._marks if isinstance(mark, _Member))
            return {
                "seq": self._seq,
                "active": self._active,
                "nodes": nodes,
                "regions": len(self._marks) - nodes,
            }

    # --- hot reload -------------------------------------------------------

    def restore(self, root: Any) -> int:
        """Re-resolve every designated widget against the freshly rebuilt ``root``.

        A reload replaces every live object, so a weakly-held member is gone by
        the time the assistant reads it. Members are matched back by the
        structural path captured at designation time; those that fail to match
        are dropped and counted in ``lost``, so the assistant can say the
        designation was partly lost instead of reasoning over a set that quietly
        shrank.

        Regions need none of this and pass through untouched: a rect is stable
        across a rebuild by construction, and what it covers is derived at read
        time anyway.

        Returns:
            The number of members re-resolved.
        """
        with self._lock:
            if not any(isinstance(mark, _Member) for mark in self._marks):
                return 0
            try:
                by_path = widgets_by_path(root)
            except Exception:
                logger.debug("selection: walking the rebuilt tree failed", exc_info=True)
                return 0

            kept, restored, lost = _remap(self._marks, by_path)
            self._marks = kept
            # The fallback a discard would restore holds the *old* objects too,
            # so it is remapped alongside -- otherwise cancelling after a reload
            # would quietly restore members whose referents are already gone.
            if self._pending is not None:
                self._pending = _remap(self._pending, by_path)[0]
            self._lost = lost
            self._seq += 1
            return restored

    @property
    def lost(self) -> int:
        """How many members the last reload failed to re-resolve."""
        with self._lock:
            return self._lost


def _remap(marks: list[Any], by_path: dict[Path, Any]) -> tuple[list[Any], int, int]:
    """Re-resolve every member in ``marks`` against a rebuilt tree.

    Returns the surviving marks, how many members were re-resolved, and how many
    could not be found. Regions pass through untouched -- a rect does not move
    when the tree is rebuilt.
    """
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
        kept.append(_Member(ref=ref, identity=resolve_target(widget), path=mark.path))
        restored += 1
    return (kept, restored, lost)


def _type_path(node: Any) -> list[str]:
    """Return the root -> node chain of type names, for locating it in ``describe_tree``.

    Distinct from the *structural* path used to survive a reload: this one is
    for whoever reads the payload, and mirrors the ancestor breadcrumb a
    browser's element inspector shows.
    """
    chain = [type(ancestor).__name__ for ancestor in ancestors(node)]
    chain.reverse()
    chain.append(type(node).__name__)
    return chain


def _rect_payload(node: Any) -> Optional[list[float]]:
    # The visible rect, not the layout one: a node trimmed by a clipping
    # ancestor must not report an area it is painted nowhere in.
    rect = visible_rect(node)
    return None if rect is None else [round(value, 2) for value in rect]


def _brief(node: Any, *, relation: Optional[str] = None) -> dict[str, Any]:
    """Identity + rect for a node named as *context*, not as a designation.

    ``relation`` is omitted for a node kept only because a descendant of it
    matched -- it is on the path to the answer, not part of it.
    """
    info = own_identity(node)
    rect = _rect_payload(node)
    if rect is not None:
        info["rect"] = rect
    if relation is not None:
        info["relation"] = relation
    return info


def _node_payload(index: int, widget: Any) -> dict[str, Any]:
    info: dict[str, Any] = {"index": index}
    own = own_identity(widget)
    info.update(own)
    # Which window the node lives in — the selection spans windows, so a
    # follow-up describe_tree/action needs the ``window=`` selector this names.
    # Absent for a tree no Window owns (bare test mounts).
    from nuiitivet.widgeting.context_lookup import find_window

    owner = find_window(widget)
    if owner is not None:
        info["window"] = getattr(owner, "id", None)
    info["path"] = _type_path(widget)
    rect = _rect_payload(widget)
    if rect is not None:
        info["rect"] = rect
    # Where the widget was built. Absent when the dev runner is not
    # recording sites, and for the few widgets framework scaffolding builds with
    # no user frame in the stack -- both of which read as "unknown", not "none".
    source = source_payload(widget)
    if source is not None:
        info["source"] = source
    info["tree"] = describe_tree(widget)
    info["state"] = describe_state(widget)
    # How to *drive* the designated node, which is a different question from
    # what it is: an anonymous Text inside a keyed Button answers to the button's
    # key. Reported only when it names something other than the node itself, so
    # it never restates what is already above it.
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


def _region_payload(index: int, root: Any, rect: Rect) -> dict[str, Any]:
    """Describe an area, deriving what it covers from the tree as it is *now*.

    The two halves answer the two readings a rectangle can carry, because
    geometry cannot tell them apart:

    * ``container`` -- the innermost node that *encloses* the region, plus its
      immediate children. This is the "I mean the space between things" reading,
      and the whole answer when nothing is painted there: it names the widget
      that should have put something in that gap, and shows what it put there
      instead.
    * ``contents`` -- the pruned subtree of what the box actually crosses, each
      node tagged ``contained`` or ``clipped``. This is the "I mean these things"
      reading.

    Neither is collapsed into the other. The caller knows what the human said;
    this only reports what is there.
    """
    info: dict[str, Any] = {"index": index, "rect": [round(value, 2) for value in rect]}
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


def describe_selection(root: Any, selection: Optional[Selection]) -> dict[str, Any]:
    """Return the designation payload the ``describe_selection`` tool serves.

    Two independent lists, deliberately not a mode. "These widgets are the
    subject" and "this area is the subject" are different intents, and a human
    may hold both at once; either list may be empty. ``index`` is a single
    ordinal sequence across both, matching the badge on screen, so "the second
    one" is unambiguous.

    Each node carries its own identity, its rect, the type chain locating it in
    ``describe_tree``, and ``describe_tree`` / ``describe_state`` **scoped to
    that node** -- which is where most of the value is: "this ``Text`` shows a
    stale value" becomes a direct read of the backing ``Observable`` instead of a
    hunt through a whole-tree dump.

    Each region is derived **now**, not frozen when it was drawn, so it answers
    against whatever tree is current -- surviving a reload for free, and letting
    the same region be read again after a fix to see what occupies it.

    Must be called on the UI thread (it reads live layout and observable state).
    """
    if selection is None:
        return {"seq": 0, "active": False, "nodes": [], "regions": [], "lost": 0}

    summary = selection.summary()
    nodes: list[dict[str, Any]] = []
    regions: list[dict[str, Any]] = []
    for index, kind, mark in selection.marks():
        if kind == "region":
            regions.append(_region_payload(index, root, mark))
        else:
            nodes.append(_node_payload(index, mark))

    return {
        "seq": summary["seq"],
        "active": summary["active"],
        "nodes": nodes,
        "regions": regions,
        "lost": selection.lost,
    }


__all__ = ["Selection", "describe_selection"]
