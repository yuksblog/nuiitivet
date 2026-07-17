"""Structural perception of a running app: a token-cheap JSON tree dump.

``describe_tree`` walks the mounted widget tree and emits, per node, its type,
any human-meaningful identity (``key`` / ``label`` / ``text``) and its
``global_layout_rect`` in root coordinates. This is the semantic, low-token view
an assistant reasons over -- "a ``Button`` labeled 'increment' at (x, y, w, h)"
-- and is what makes targeting for the (separate) action bridge possible.

It reuses :func:`nuiitivet.dev.snapshot.iter_child_widgets` so the description
descends exactly the nodes the reload snapshot considers part of the tree.
"""

from __future__ import annotations

from typing import Any, Optional

from .snapshot import iter_child_widgets

# Attributes probed, in order, for a node's display identity. The first that
# resolves to a non-empty string is reported.
_IDENTITY_ATTRS = ("key", "label", "text", "title")

# Cap on a single identity string so one giant text node cannot bloat the dump.
_MAX_IDENTITY_LEN = 120


def _coerce_display(value: Any) -> Optional[str]:
    """Return a short display string for ``value``, or ``None`` if unusable.

    Observables are unwrapped via ``.value``. Widgets and other non-scalar
    objects are ignored (a button's ``label`` may itself be a child widget), so
    only genuine text-like identities are surfaced.
    """
    if value is None:
        return None
    if hasattr(value, "value"):
        try:
            value = value.value
        except Exception:
            return None
    if not isinstance(value, (str, int, float, bool)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > _MAX_IDENTITY_LEN:
        text = text[: _MAX_IDENTITY_LEN - 1] + "…"
    return text


def _describe_node(node: Any, *, seen: set[int]) -> dict[str, Any]:
    """Build the JSON description for ``node`` and, recursively, its children."""
    info: dict[str, Any] = {"type": type(node).__name__}

    for attr in _IDENTITY_ATTRS:
        display = _coerce_display(getattr(node, attr, None))
        if display is not None:
            info[attr] = display

    rect = getattr(node, "global_layout_rect", None)
    if rect is not None:
        info["rect"] = list(rect)

    seen.add(id(node))
    children: list[dict[str, Any]] = []
    for child in iter_child_widgets(node):
        if child is None or id(child) in seen:
            continue
        children.append(_describe_node(child, seen=seen))
    if children:
        info["children"] = children

    return info


def describe_tree(root: Any) -> dict[str, Any]:
    """Return a nested JSON-serializable description of ``root``'s mounted tree.

    Must be called on the UI thread (it reads live layout state). Each node maps
    to ``{"type", optional "key"/"label"/"text"/"title", optional "rect",
    optional "children"}`` where ``rect`` is ``[x, y, w, h]`` in root coordinates.

    Args:
        root: The mounted root widget (``App.root``).

    Returns:
        The root node's description, or ``{}`` if ``root`` is ``None``.
    """
    if root is None:
        return {}
    return _describe_node(root, seen=set())
