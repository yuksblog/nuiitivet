"""Snapshot & restore ``Observable`` state across a reload (§8 of HOT_RELOAD.md).

A reload rebuilds the whole widget tree from the factory, so no live object is
carried over. "Preserving state" therefore means: read the *values* of every
mutable ``Observable`` in the old tree, keyed by a structural path, then write
them back into the matching observables of the freshly built tree.

Paths prefer a widget's stable ``key`` and otherwise fall back to position + type.
When the tree structure is unchanged (the common "tweak a padding" case) every
path matches and state is fully restored. A widget given a ``key`` keeps its path
across a reorder or a sibling insertion, so its state survives such edits too;
keyless widgets that move lose their state — unmatched paths keep the new tree's
initial values, the documented, acceptable degradation (§9.5).

Only in-tree observables (held as widget instance attributes) are handled;
module-level observables are out of scope (§9.5).
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional

from nuiitivet.observable.protocols import MutableObservableBase

logger = logging.getLogger(__name__)

# A structural path: a tuple of segments from the root, plus a trailing attribute
# name for the observable itself.
Path = tuple[str, ...]


def _segment(node: Any, positional: str) -> str:
    """Return the path segment for ``node``, preferring its stable ``key``.

    A widget given a ``key`` (§7.4/#375) anchors its state to that identifier
    rather than its position, so restore survives a reorder or the insertion of a
    sibling before it. Without a key the segment falls back to ``positional``
    (index/slot + type), the original position-based identity — so a keyless
    reorder still breaks the match rather than mis-restoring.
    """
    key = getattr(node, "key", None)
    if isinstance(key, str) and key:
        return f"@{key}:{type(node).__name__}"
    return positional


def _walk(widget: Any) -> Iterator[tuple[Path, Any]]:
    """Yield ``(path, widget)`` for every widget in the mounted tree.

    Traverses both ``children`` (containers) and ``built_child`` (the subtree a
    :class:`ComposableWidget` produced), which is where composable state lives.
    Path segments prefer a widget's stable ``key`` and otherwise fall back to the
    child index/slot plus the widget class name, so a reordering or type change of
    keyless widgets breaks the match rather than mis-restoring.
    """
    seen: set[int] = set()

    def visit(node: Any, path: Path) -> Iterator[tuple[Path, Any]]:
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        yield path, node

        children = getattr(node, "children", ()) or ()
        for index, child in enumerate(children):
            seg = _segment(child, f"{index}:{type(child).__name__}")
            yield from visit(child, path + (seg,))

        built = getattr(node, "built_child", None)
        if built is not None and built is not node and id(built) not in seen:
            seg = _segment(built, f"#built:{type(built).__name__}")
            yield from visit(built, path + (seg,))

    yield from visit(widget, ())


def path_of(root: Any, node: Any) -> Optional[Path]:
    """Return ``node``'s structural path within ``root``'s tree, or ``None``.

    The same key-preferring path :func:`snapshot_observables` builds, exposed for
    anything that has to survive a reload by naming *where* a widget was rather
    than holding the object -- the inspect-mode selection (#591) re-resolves its
    members this way, for the same reason and with the same degradation: a
    keyless widget that moves loses its match.
    """
    for candidate, widget in _walk(root):
        if widget is node:
            return candidate
    return None


def widgets_by_path(root: Any) -> dict[Path, Any]:
    """Return every widget in ``root``'s tree, keyed by its structural path.

    The lookup side of :func:`path_of`: one walk answers any number of paths, so
    re-resolving a whole selection after a reload costs a single traversal.
    """
    return {path: widget for path, widget in _walk(root)}


def snapshot_observables(root: Any) -> dict[Path, Any]:
    """Capture the value of every mutable observable in ``root``'s tree."""
    snapshot: dict[Path, Any] = {}
    for path, widget in _walk(root):
        state = getattr(widget, "__dict__", None)
        if not state:
            continue
        for attr, value in state.items():
            if isinstance(value, MutableObservableBase):
                try:
                    snapshot[path + (attr,)] = value.value
                except Exception:
                    # A misbehaving getter must not abort the whole snapshot.
                    logger.debug("snapshot: reading %s.%s failed", type(widget).__name__, attr)
    return snapshot


def restore_observables(root: Any, snapshot: dict[Path, Any]) -> int:
    """Write snapshot values back into matching observables of ``root``'s tree.

    Args:
        root: The freshly built (and mounted) root.
        snapshot: The mapping from :func:`snapshot_observables`.

    Returns:
        The number of observables restored (matched paths).
    """
    if not snapshot:
        return 0
    restored = 0
    for path, widget in _walk(root):
        state = getattr(widget, "__dict__", None)
        if not state:
            continue
        for attr, value in state.items():
            if not isinstance(value, MutableObservableBase):
                continue
            key = path + (attr,)
            if key not in snapshot:
                continue
            try:
                value.value = snapshot[key]
                restored += 1
            except Exception:
                logger.debug("restore: writing %s.%s failed", type(widget).__name__, attr)
    return restored
