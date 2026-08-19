"""The human's designation buffer: what they *pointed at*, for the assistant to pull (#591).

The dev bridge already carries perception (``describe_tree`` / ``describe_state``
/ ``screenshot``), action (``click`` / ``scroll`` / ``type`` / ``key``) and the
journals that let an assistant catch up on what the human *did*. This module adds
the one thing missing in the human -> assistant direction: a record of what the
human *means*. The human enters inspect mode, designates widgets, and leaves; the
assistant reads the result on its own turn. Nothing is pushed.

It is an **annotation** surface, not an inspector: the audience is another party,
so a designation is deliberately multiple, persistent, and has to survive until
that party reads it -- including across the hot reload that the assistant's own
fix triggers.

Two boundaries are load-bearing:

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
  with (HOT_RELOAD.md §7.4), and any that fail are counted in ``lost`` rather
  than silently dropped -- an assistant reasoning over a quietly truncated set is
  the worst available outcome.

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
    ancestors,
    describe_state,
    describe_tree,
    global_visual_rect,
)

from .interaction import own_identity, resolve_target
from .snapshot import Path, path_of, widgets_by_path

logger = logging.getLogger(__name__)


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
class Selection:
    """The designation buffer for one running app.

    Holds the nodes the human designated, whether inspect mode is currently on,
    and a monotonic ``seq`` that bumps on every change -- which is what lets an
    assistant notice a designation happened by polling the cheap ``status``
    summary rather than the full payload.
    """

    _nodes: list[_Member] = field(default_factory=list)
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
        """Latch inspect mode on."""
        with self._lock:
            if self._active:
                return
            self._active = True
            self._seq += 1

    def leave(self) -> None:
        """Latch inspect mode off. **Leaving commits** -- the designation persists."""
        with self._lock:
            if not self._active:
                return
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
            for index, member in enumerate(self._nodes):
                if member.widget() is node:
                    del self._nodes[index]
                    self._seq += 1
                    return False
            added = self._make_member(node, root)
            if added is None:
                return False
            self._nodes.append(added)
            self._seq += 1
            return True

    def replace_last(self, node: Any, *, root: Any = None) -> None:
        """Replace the most recently designated member with ``node``.

        The ancestor / descendant walk: the human designated roughly the right
        place and is now moving up or down the chain from it, which reads as one
        designation being refined rather than several being made.

        Takes ``root`` for the same reason :meth:`toggle` does, and it is just as
        load-bearing: a refined member without a structural path is silently
        unable to survive the reload the assistant's own fix triggers.
        """
        if node is None:
            return
        with self._lock:
            member = self._make_member(node, root)
            if member is None:
                return
            if self._nodes:
                self._nodes[-1] = member
            else:
                self._nodes.append(member)
            self._seq += 1

    def remove_last(self) -> None:
        """Drop the most recent designation."""
        with self._lock:
            if not self._nodes:
                return
            self._nodes.pop()
            self._seq += 1

    def clear(self) -> None:
        """Drop every designation and reset the lost count."""
        with self._lock:
            if not self._nodes and not self._lost:
                return
            self._nodes.clear()
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

    def members(self) -> list[Any]:
        """Return the designated widgets that are still alive, in designation order."""
        with self._lock:
            return [widget for widget in (m.widget() for m in self._nodes) if widget is not None]

    def last(self) -> Optional[Any]:
        """Return the most recently designated widget, or ``None``."""
        with self._lock:
            for member in reversed(self._nodes):
                widget = member.widget()
                if widget is not None:
                    return widget
        return None

    def summary(self) -> dict[str, Any]:
        """Return the cheap roll-up ``status`` carries.

        The counts are kept separate rather than summed: "3 nodes" and "3
        regions" mean different things to whoever reads it.
        """
        with self._lock:
            return {
                "seq": self._seq,
                "active": self._active,
                "nodes": len(self._nodes),
                "regions": 0,
            }

    # --- hot reload -------------------------------------------------------

    def restore(self, root: Any) -> int:
        """Re-resolve every member against the freshly rebuilt ``root``.

        A reload replaces every live object, so a weakly-held member is gone by
        the time the assistant reads it. Members are matched back by the
        structural path captured at designation time; those that fail to match
        are dropped and counted in ``lost``, so the assistant can say the
        designation was partly lost instead of reasoning over a set that
        quietly shrank.

        Returns:
            The number of members re-resolved.
        """
        with self._lock:
            if not self._nodes:
                return 0
            try:
                by_path = widgets_by_path(root)
            except Exception:
                logger.debug("selection: walking the rebuilt tree failed", exc_info=True)
                return 0

            restored: list[_Member] = []
            lost = 0
            for member in self._nodes:
                widget = by_path.get(member.path) if member.path is not None else None
                if widget is None:
                    lost += 1
                    continue
                ref = _weak_ref(widget)
                if ref is None:
                    lost += 1
                    continue
                restored.append(
                    _Member(ref=ref, identity=resolve_target(widget), path=member.path)
                )

            self._nodes = restored
            self._lost = lost
            self._seq += 1
            return len(restored)

    @property
    def lost(self) -> int:
        """How many members the last reload failed to re-resolve."""
        with self._lock:
            return self._lost


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


def describe_selection(selection: Optional[Selection]) -> dict[str, Any]:
    """Return the designation payload the ``describe_selection`` tool serves.

    Each node carries its resolved identity (so it is directly usable as a
    ``click --key`` target), its rect, the type chain locating it in
    ``describe_tree``, and ``describe_tree`` / ``describe_state`` **scoped to
    that node** -- which is where most of the value is: "this ``Text`` shows a
    stale value" becomes a direct read of the backing ``Observable`` instead of a
    hunt through a whole-tree dump.

    ``regions`` is always present and empty for now; region designation is the
    second half of #591 and shares this payload rather than a second tool.

    Must be called on the UI thread (it reads live layout and observable state).
    """
    if selection is None:
        return {"seq": 0, "active": False, "nodes": [], "regions": [], "lost": 0}

    summary = selection.summary()
    nodes: list[dict[str, Any]] = []
    for index, widget in enumerate(selection.members(), start=1):
        info: dict[str, Any] = {"index": index}
        own = own_identity(widget)
        info.update(own)
        info["path"] = _type_path(widget)
        rect = global_visual_rect(widget)
        if rect is not None:
            info["rect"] = [round(value, 2) for value in rect]
        info["tree"] = describe_tree(widget)
        info["state"] = describe_state(widget)
        # How to *drive* the designated node, which is a different question from
        # what it is: an anonymous Text inside a keyed Button answers to the
        # button's key. Reported only when it names something other than the node
        # itself, so it never restates what is already above it.
        target = resolve_target(widget)
        if target != own:
            info["target"] = target
        nodes.append(info)

    return {
        "seq": summary["seq"],
        "active": summary["active"],
        "nodes": nodes,
        "regions": [],
        "lost": selection.lost,
    }


__all__ = ["Selection", "describe_selection"]
