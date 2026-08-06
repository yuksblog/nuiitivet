"""Structural perception of a running app: a token-cheap JSON tree dump.

``describe_tree`` walks the mounted widget tree and emits, per node, its type,
any human-meaningful identity (``key`` / ``label`` / ``text``) and its
``global_layout_rect`` in root coordinates. This is the semantic, low-token view
an assistant reasons over -- "a ``Button`` labeled 'increment' at (x, y, w, h)"
-- and is what makes targeting for the (separate) action bridge possible.

It reuses :func:`nuiitivet.dev.snapshot.iter_child_widgets` so the description
descends exactly the nodes the reload snapshot considers part of the tree.

Alongside the dump it owns the *geometry* half of targeting -- resolving a node
to the point on screen the app's own pointer dispatch would deliver to
(:func:`global_visual_rect`) and deciding whether that point can reach it at all
(:func:`find_obstruction`) -- which is what keeps the action verbs honest.
"""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet.animation.animatable import Animatable
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


def ancestors(node: Any) -> list[Any]:
    """Return ``node``'s ancestors, nearest first (empty when it has no parent)."""
    chain: list[Any] = []
    seen: set[int] = set()
    current = getattr(node, "parent", None)
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        current = getattr(current, "parent", None)
    return chain


def _visual_offset(node: Any) -> tuple[float, float]:
    """Return the displacement ``node`` applies to its painted children.

    A container that paints its children somewhere other than their layout
    position -- a scroll viewport today, transforms and popups later -- opts in
    by exposing ``visual_offset() -> (dx, dy)``. Probed by name so this module
    stays independent of :mod:`nuiitivet.layout`; anything else contributes
    ``(0, 0)``.
    """
    probe = getattr(node, "visual_offset", None)
    if not callable(probe):
        return (0.0, 0.0)
    try:
        dx, dy = probe()
        return (float(dx), float(dy))
    except Exception:
        return (0.0, 0.0)


def _visual_clip_rect(node: Any) -> Optional[tuple[float, float, float, float]]:
    """Return ``node``'s content clip in root coordinates, or ``None`` if it clips nothing.

    The opt-in companion to ``visual_offset``: ``visual_clip_rect()`` reports the
    clip in the widget's *own* coordinates, which this translates to root space.
    """
    probe = getattr(node, "visual_clip_rect", None)
    if not callable(probe):
        return None
    try:
        cx, cy, cw, ch = probe()
    except Exception:
        return None
    origin = global_visual_rect(node)
    if origin is None:
        return None
    return (origin[0] + float(cx), origin[1] + float(cy), float(cw), float(ch))


def global_visual_rect(node: Any) -> Optional[tuple[float, float, float, float]]:
    """Return ``node``'s rect in root coordinates *as painted*, or ``None``.

    ``global_layout_rect`` accumulates ancestor layout offsets only -- it is
    content space, and inside a scrolled region it is off by the scroll offset
    (the two coincide only at offset zero). This adds each ancestor's
    :func:`_visual_offset`, giving the coordinates the app's own pointer
    dispatch works in, which is what an action must aim at.

    Paint state (``last_rect``) is deliberately not used: an action settles the
    tree by laying it out without painting, so ``last_rect`` is stale exactly
    when it would be needed.
    """
    rect = getattr(node, "global_layout_rect", None)
    if rect is None:
        return None
    x, y, w, h = rect
    dx = dy = 0.0
    for ancestor in ancestors(node):
        adx, ady = _visual_offset(ancestor)
        dx += adx
        dy += ady
    return (float(x) + dx, float(y) + dy, float(w), float(h))


def _contains(rect: tuple[float, float, float, float], x: float, y: float) -> bool:
    rx, ry, rw, rh = rect
    return rx <= x < rx + rw and ry <= y < ry + rh


def _on_path(node: Any, other: Any) -> bool:
    """Whether ``other`` is ``node`` itself, or one of the two is the other's ancestor.

    ``hit_test`` returns the deepest *hit-participating* widget, which for a
    non-interactive target (a ``Text`` inside a ``Button``) is an ancestor of it,
    and for a container target a descendant. Both mean the point genuinely
    reaches the target's chain; an unrelated subtree means something else is on
    top of it.
    """
    if other is node:
        return True
    return any(a is other for a in ancestors(node)) or any(a is node for a in ancestors(other))


def find_obstruction(root: Any, node: Any, x: float, y: float) -> Optional[str]:
    """Return why root-space ``(x, y)`` cannot reach ``node``, or ``None`` if it can.

    Two independent checks, because they catch different failures:

    * **Clipping** -- an ancestor that clips its content (a scroll viewport)
      whose clip rect excludes the point. This is the scrolled-out-of-view case:
      the widget is laid out, but painted nowhere.
    * **Occlusion** -- ``hit_test`` at the point lands in an unrelated subtree,
      i.e. something (a modal, an overlay) is on top. A point that hits nothing
      is *not* reported: a non-interactive target legitimately hit-tests to
      ``None``, and a click there is a harmless no-op.

    Best-effort by construction: a root without ``hit_test`` (a test fake) skips
    the occlusion check rather than failing it.
    """
    for ancestor in ancestors(node):
        clip = _visual_clip_rect(ancestor)
        if clip is not None and not _contains(clip, x, y):
            return (
                f"clipped out of {type(ancestor).__name__}'s visible area "
                f"{tuple(round(v) for v in clip)}"
            )

    hit_test = getattr(root, "hit_test", None)
    if not callable(hit_test):
        return None
    try:
        hit = hit_test(int(round(x)), int(round(y)))
    except Exception:
        return None
    if hit is None or _on_path(node, hit):
        return None
    return f"covered by {type(hit).__name__} at that point"


def _node_matches(
    node: Any,
    *,
    key: Optional[str],
    label: Optional[str],
    text: Optional[str],
) -> bool:
    """Return whether ``node`` satisfies every provided identity constraint.

    ``key`` / ``label`` match the same way :func:`find_target` does (``key``
    exactly, ``label`` against a visible identity). ``text`` matches when a
    visible identity *contains* it as a substring (case-sensitive). Constraints
    that are ``None`` are ignored, so all supplied ones must hold together.
    """
    if key is not None and _coerce_display(getattr(node, "key", None)) != key:
        return False
    identities = _identity_values(node)
    if label is not None and label not in identities:
        return False
    if text is not None and not any(text in value for value in identities):
        return False
    return True


def match_condition(
    root: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    text: Optional[str] = None,
    present: bool = True,
) -> bool:
    """Evaluate a ``wait_for`` condition against ``root``'s mounted tree.

    A condition names a target by identity (``key`` / ``label``) and/or by a
    ``text`` substring of a visible identity; a node must satisfy every supplied
    field (see :func:`_node_matches`). The condition is satisfied when such a
    node exists (``present=True``, the default) or when none does
    (``present=False`` -- e.g. waiting a spinner or loading overlay out).

    Must be called on the UI thread (it reads live observable/layout state).

    Raises:
        ValueError: If none of ``key`` / ``label`` / ``text`` is given.
    """
    if key is None and label is None and text is None:
        raise ValueError("a wait_for condition needs one of: key, label, text")
    found = any(
        _node_matches(node, key=key, label=label, text=text) for node in _iter_tree(root)
    )
    return found if present else not found


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


def _node_state(node: Any, *, include_animations: bool) -> dict[str, Any]:
    """Return the ``Observable`` state a single widget holds, keyed by name.

    Scans the widget's ``__dict__`` for observable-valued attributes -- both the
    descriptor storage of declared ``Observable`` fields and observables passed
    in and stored directly (the ``bool | ObservableProtocol`` binding pattern).
    Stateless widgets return ``{}``.

    ``Animatable`` attributes are skipped unless ``include_animations`` is set:
    an interactive widget carries several animation channels that change every
    frame and carry visual, not semantic, state, and they otherwise dominate the
    dump (#418).
    """
    namespace = getattr(node, "__dict__", None)
    if not namespace:
        return {}
    state: dict[str, Any] = {}
    for attr, value in namespace.items():
        if not isinstance(value, ObservableBase):
            continue
        if isinstance(value, Animatable) and not include_animations:
            continue
        entry = _read_observable(value)
        if entry is _UNREADABLE:
            continue
        name = _state_name(attr)
        # Two attributes mapping to the same reported name would collide; keep
        # the raw attribute name for the later one so nothing is silently lost.
        state[attr if name in state else name] = entry
    return state


def _describe_state_node(
    node: Any, *, seen: set[int], include_animations: bool
) -> Optional[dict[str, Any]]:
    """Build the state description for ``node``, or ``None`` if it carries none.

    Mirrors :func:`describe_tree`'s shape (``type`` + identity + ``children``) so
    the two views join structurally, but prunes every node that neither holds
    observable state nor has a descendant that does -- keeping the dump focused
    on the reactive state while retaining the ancestor path to each stateful node.

    Pruning runs on the *filtered* state, so a node whose only state was
    animation channels prunes away like any other stateless node rather than
    surviving as a hollow entry with its ancestor path.
    """
    seen.add(id(node))
    children: list[dict[str, Any]] = []
    for child in iter_child_widgets(node):
        if child is None or id(child) in seen:
            continue
        described = _describe_state_node(
            child, seen=seen, include_animations=include_animations
        )
        if described is not None:
            children.append(described)

    state = _node_state(node, include_animations=include_animations)
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


def describe_state(root: Any, *, include_animations: bool = False) -> dict[str, Any]:
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

    ``Animatable`` state is **omitted by default** (#418): an interactive widget
    carries several animation channels (``state_layer_anim``, ``bg_color_anim``,
    …) whose per-frame visual values buried the semantic state and dominated the
    payload. Pass ``include_animations=True`` when the animation itself is what
    is under investigation ("the button never returns to its rest state").

    Must be called on the UI thread (it reads live observable state).

    Args:
        root: The mounted root widget (``App.root``).
        include_animations: Report ``Animatable`` state too, instead of
            filtering it out.

    Returns:
        The pruned state tree, or ``{}`` if ``root`` is ``None`` or holds no
        reachable (reported) observable state.
    """
    if root is None:
        return {}
    described = _describe_state_node(
        root, seen=set(), include_animations=include_animations
    )
    return described if described is not None else {}
