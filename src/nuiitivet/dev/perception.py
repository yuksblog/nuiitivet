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

from nuiitivet.observable.protocols import MutableObservableBase, ObservableBase

from .snapshot import iter_child_widgets

# Attributes probed, in order, for a node's display identity. The first that
# resolves to a non-empty string is reported.
_IDENTITY_ATTRS = ("key", "label", "text", "title")

# Cap on a single identity string so one giant text node cannot bloat the dump.
_MAX_IDENTITY_LEN = 120

# Caps for ``describe_state`` value serialization: a single string/repr is
# truncated to this length, and a container reports at most this many items so
# one large collection cannot bloat the dump.
_MAX_VALUE_LEN = 200
_MAX_VALUE_ITEMS = 20
# How deep to recurse into nested containers before summarizing, so a
# self-referential or deeply nested value cannot recurse without bound.
_MAX_VALUE_DEPTH = 4

# Sentinel: an observable whose value could not be read is dropped rather than
# reported, so one misbehaving getter never aborts the whole state dump.
_UNREADABLE = object()


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


def _iter_tree(root: Any) -> Any:
    """Yield every widget in ``root``'s mounted tree, depth-first (pre-order).

    Shares :func:`iter_child_widgets` with :func:`describe_tree` so both agree on
    exactly which nodes are "in" the tree.
    """
    seen: set[int] = set()

    def visit(node: Any) -> Any:
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        yield node
        for child in iter_child_widgets(node):
            yield from visit(child)

    yield from visit(root)


def _identity_values(node: Any) -> list[str]:
    """Return the coerced display strings a ``label=`` target may match on."""
    values: list[str] = []
    for attr in ("label", "text", "title"):
        display = _coerce_display(getattr(node, attr, None))
        if display is not None:
            values.append(display)
    return values


def find_target(root: Any, *, key: Optional[str] = None, label: Optional[str] = None) -> Optional[Any]:
    """Return the first widget matching ``key`` or ``label``, or ``None``.

    Targets are stable identifiers, not pixels: ``key`` matches a widget's
    ``key`` exactly (the testID set at construction); ``label`` matches any of a
    node's human-visible identities (``label`` / ``text`` / ``title``). The tree
    is searched depth-first, so the first (topmost, outermost) match wins.

    Must be called on the UI thread (it reads live layout/observable state).
    """
    if root is None or (key is None and label is None):
        return None
    for node in _iter_tree(root):
        if key is not None and _coerce_display(getattr(node, "key", None)) == key:
            return node
        if label is not None and label in _identity_values(node):
            return node
    return None


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


def _truncate(text: str) -> str:
    """Return ``text`` capped at :data:`_MAX_VALUE_LEN` with an ellipsis marker."""
    if len(text) > _MAX_VALUE_LEN:
        return text[: _MAX_VALUE_LEN - 1] + "…"
    return text


def _coerce_value(value: Any, *, depth: int = 0) -> Any:
    """Return a JSON-safe, bounded representation of an observable's value.

    Scalars pass through; strings are length-capped; lists/tuples and dicts are
    recursed element-wise with both breadth (:data:`_MAX_VALUE_ITEMS`) and depth
    (:data:`_MAX_VALUE_DEPTH`) caps; anything else is rendered as a truncated
    ``type: repr`` so an opaque object is still identifiable without bloating the
    dump. Never raises -- a value whose ``repr`` fails degrades to its type name.
    """
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate(value)
    if depth >= _MAX_VALUE_DEPTH:
        return _opaque(value)
    if isinstance(value, (list, tuple)):
        items = list(value)
        out = [_coerce_value(item, depth=depth + 1) for item in items[:_MAX_VALUE_ITEMS]]
        if len(items) > _MAX_VALUE_ITEMS:
            out.append(f"… (+{len(items) - _MAX_VALUE_ITEMS} more)")
        return out
    if isinstance(value, dict):
        out_map: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= _MAX_VALUE_ITEMS:
                out_map["…"] = f"(+{len(value) - _MAX_VALUE_ITEMS} more)"
                break
            out_map[str(key)] = _coerce_value(item, depth=depth + 1)
        return out_map
    return _opaque(value)


def _opaque(value: Any) -> str:
    """Render a non-JSON value as a truncated ``type: repr``, never raising."""
    try:
        return _truncate(f"{type(value).__name__}: {value!r}")
    except Exception:
        return type(value).__name__


def _state_name(attr: str) -> str:
    """Map an instance-attribute name to the reported state key.

    Descriptor-backed observables live under ``_obs_<name>`` (see
    :class:`nuiitivet.observable.value.Observable`), so ``_obs_checked`` reports
    as ``checked``. Directly-assigned observable attributes drop a leading
    underscore (``_value`` -> ``value``) so the private-storage convention does
    not leak into the surfaced name.
    """
    if attr.startswith("_obs_"):
        return attr[len("_obs_") :] or attr
    return attr.lstrip("_") or attr


def _read_observable(obs: ObservableBase[Any]) -> Any:
    """Return the reported entry for one observable, or :data:`_UNREADABLE`.

    A mutable source observable reports its coerced value directly; a derived
    (non-mutable) one -- ``Observable.compute`` / ``map`` / ``combine`` -- is
    wrapped as ``{"value", "kind": "computed"}`` so the assistant can tell a
    value it can trace to an edit from one that is recomputed from others.
    """
    try:
        raw = obs.value
    except Exception:
        return _UNREADABLE
    coerced = _coerce_value(raw)
    if isinstance(obs, MutableObservableBase):
        return coerced
    return {"value": coerced, "kind": "computed"}


def _node_state(node: Any) -> dict[str, Any]:
    """Return the ``Observable`` state a single widget holds, keyed by name.

    Scans the widget's ``__dict__`` for observable-valued attributes -- both the
    descriptor storage of declared ``Observable`` fields and observables passed
    in and stored directly (the ``bool | ObservableProtocol`` binding pattern).
    Stateless widgets return ``{}``.
    """
    namespace = getattr(node, "__dict__", None)
    if not namespace:
        return {}
    state: dict[str, Any] = {}
    for attr, value in namespace.items():
        if not isinstance(value, ObservableBase):
            continue
        entry = _read_observable(value)
        if entry is _UNREADABLE:
            continue
        name = _state_name(attr)
        # Two attributes mapping to the same reported name would collide; keep
        # the raw attribute name for the later one so nothing is silently lost.
        state[attr if name in state else name] = entry
    return state


def _describe_state_node(node: Any, *, seen: set[int]) -> Optional[dict[str, Any]]:
    """Build the state description for ``node``, or ``None`` if it carries none.

    Mirrors :func:`describe_tree`'s shape (``type`` + identity + ``children``) so
    the two views join structurally, but prunes every node that neither holds
    observable state nor has a descendant that does -- keeping the dump focused
    on the reactive state while retaining the ancestor path to each stateful node.
    """
    seen.add(id(node))
    children: list[dict[str, Any]] = []
    for child in iter_child_widgets(node):
        if child is None or id(child) in seen:
            continue
        described = _describe_state_node(child, seen=seen)
        if described is not None:
            children.append(described)

    state = _node_state(node)
    if not state and not children:
        return None

    info: dict[str, Any] = {"type": type(node).__name__}
    for attr in _IDENTITY_ATTRS:
        display = _coerce_display(getattr(node, attr, None))
        if display is not None:
            info[attr] = display
    if state:
        info["state"] = state
    if children:
        info["children"] = children
    return info


def describe_state(root: Any) -> dict[str, Any]:
    """Return the reactive ``Observable`` state of ``root``'s mounted tree.

    The complement to :func:`describe_tree`: where that reports the *output*
    (types, identities, rects), this reports the *state that produced it* -- the
    live ``Observable`` values reachable from the mounted tree. The result mirrors
    ``describe_tree``'s nested shape (each node ``{"type", optional identity,
    optional "state", optional "children"}``) but is pruned to nodes that hold
    state or contain one that does, so the two can be joined structurally.

    Each ``state`` entry maps a name to a coerced current value; a derived
    (computed) observable is instead ``{"value", "kind": "computed"}``. Values are
    length- and depth-capped and opaque objects render as ``type: repr``, so no
    single value can bloat or break the dump.

    Must be called on the UI thread (it reads live observable state).

    Args:
        root: The mounted root widget (``App.root``).

    Returns:
        The pruned state tree, or ``{}`` if ``root`` is ``None`` or holds no
        reachable observable state.
    """
    if root is None:
        return {}
    described = _describe_state_node(root, seen=set())
    return described if described is not None else {}
