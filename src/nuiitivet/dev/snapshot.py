"""Snapshot & restore ``Observable`` state across a reload (§8 of HOT_RELOAD.md).

A reload rebuilds the whole widget tree from the factory, so no live object is
carried over. "Preserving state" therefore means: read the *values* of every
mutable ``Observable`` in the old tree, keyed by a structural path, then write
them back into the matching observables of the freshly built tree.

Paths are position + type based. When the tree structure is unchanged (the common
"tweak a padding" case) every path matches and state is fully restored. When the
structure changes (widgets added/removed/reordered), unmatched paths simply keep
the new tree's initial values — the documented, acceptable degradation (§9.5).

Only in-tree observables (held as widget instance attributes) are handled;
module-level observables are out of scope (§9.5).
"""

from __future__ import annotations

import logging
from typing import Any, Iterator

from nuiitivet.observable.protocols import MutableObservableBase

logger = logging.getLogger(__name__)

# A structural path: a tuple of segments from the root, plus a trailing attribute
# name for the observable itself.
Path = tuple[str, ...]


def iter_child_widgets(node: Any) -> Iterator[Any]:
    """Yield the direct child widgets of ``node`` in traversal order.

    The mounted tree hangs off two attributes: ``children`` (the widgets a
    container laid out) and ``built_child`` (the subtree a
    :class:`ComposableWidget` produced). This is the single primitive both the
    snapshot walk and the dev-bridge tree description use to descend the tree, so
    they agree on exactly which nodes are "in" the mounted tree.
    """
    children = getattr(node, "children", ()) or ()
    for child in children:
        if child is not None:
            yield child
    built = getattr(node, "built_child", None)
    if built is not None and built is not node:
        yield built


def _walk(widget: Any) -> Iterator[tuple[Path, Any]]:
    """Yield ``(path, widget)`` for every widget in the mounted tree.

    Traverses both ``children`` (containers) and ``built_child`` (the subtree a
    :class:`ComposableWidget` produced), which is where composable state lives.
    Path segments include the child index/slot and the widget class name so a
    reordering or type change breaks the match rather than mis-restoring.
    """
    seen: set[int] = set()

    def visit(node: Any, path: Path) -> Iterator[tuple[Path, Any]]:
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        yield path, node

        children = getattr(node, "children", ()) or ()
        for index, child in enumerate(children):
            seg = f"{index}:{type(child).__name__}"
            yield from visit(child, path + (seg,))

        built = getattr(node, "built_child", None)
        if built is not None and built is not node and id(built) not in seen:
            yield from visit(built, path + (f"#built:{type(built).__name__}",))

    yield from visit(widget, ())


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
