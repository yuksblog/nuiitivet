"""The one primitive every walk of the mounted tree descends through."""

from __future__ import annotations

from typing import Any, Iterator


def iter_child_widgets(node: Any) -> Iterator[Any]:
    """Yield the direct child widgets of ``node`` in traversal order.

    The mounted tree hangs off two attributes: ``children`` (the widgets a
    container laid out) and ``built_child`` (the subtree a
    :class:`ComposableWidget` produced). Every walk in :mod:`.perception`
    descends through this, so the tree description and the target search agree on
    exactly which nodes are "in" the mounted tree.
    """
    children = getattr(node, "children", ()) or ()
    for child in children:
        if child is not None:
            yield child
    built = getattr(node, "built_child", None)
    if built is not None and built is not node:
        yield built
