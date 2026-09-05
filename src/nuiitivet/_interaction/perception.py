"""Structural perception of a running app: a token-cheap JSON tree dump.

``describe_tree`` walks the mounted widget tree and emits, per node, its type,
any human-meaningful identity (``key`` / ``label`` / ``text``), the interactive
state it publishes (``disabled`` / ``focused`` / ``selected`` / ``value``) and
its ``global_layout_rect`` in root coordinates. This is the semantic, low-token
view an assistant reasons over -- "a disabled ``Button`` labeled 'increment' at
(x, y, w, h)" -- and is what makes targeting for
:mod:`nuiitivet._interaction.action` possible.

Alongside the dump it owns the *geometry* half of targeting -- resolving a node
to the point on screen the app's own pointer dispatch would deliver to
(:func:`global_visual_rect`) and deciding whether that point can reach it at all
(:func:`find_obstruction`) -- which is what keeps the action verbs honest.
"""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet.animation.animatable import Animatable
from nuiitivet.observable.protocols import MutableObservableBase, ObservableBase

from .tree import iter_child_widgets

# Attributes probed, in order, for a node's display identity. The first that
# resolves to a non-empty string is reported.
_IDENTITY_ATTRS = ("key", "label", "text", "title")

# Cap on a single identity string so one giant text node cannot bloat the dump.
_MAX_IDENTITY_LEN = 120

# Caps for value serialization: a single string/repr is truncated to this
# length, and a container reports at most this many items so one large
# collection cannot bloat the dump.
_MAX_VALUE_LEN = 200
_MAX_VALUE_ITEMS = 20
# How deep to recurse into nested containers before summarizing, so a
# self-referential or deeply nested value cannot recurse without bound.
_MAX_VALUE_DEPTH = 4

# Boolean semantic state reported per node, in order. Each is probed as a public
# property first and as a field of the widget's ``InteractionState`` second: a
# widget publishes a flag one way or the other, and both kinds exist (a chip
# carries ``selected`` only as a property, a navigation rail item only in its
# state). ``focused`` lives solely in the state -- the input backend drives it.
_STATE_FLAGS = ("disabled", "focused", "selected")

# Sentinel: an observable whose value could not be read is dropped rather than
# reported, so one misbehaving getter never aborts the whole state dump.
_UNREADABLE = object()

# Sentinel: an attribute a node does not publish, kept distinct from ``None`` so
# a tri-state checkbox's indeterminate ``value`` still reports as ``null``.
_MISSING = object()


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


def _truncate(text: str) -> str:
    """Return ``text`` capped at :data:`_MAX_VALUE_LEN` with an ellipsis marker."""
    if len(text) > _MAX_VALUE_LEN:
        return text[: _MAX_VALUE_LEN - 1] + "…"
    return text


def _coerce_value(value: Any, *, depth: int = 0) -> Any:
    """Return a JSON-safe, bounded representation of a reported value.

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


def _probe(node: Any, name: str) -> Any:
    """Return ``node``'s ``name`` attribute, or :data:`_MISSING`.

    A widget publishes its semantic state as an ordinary property, so reading one
    runs app code; a getter that raises degrades to "not published" rather than
    aborting the whole dump.
    """
    try:
        return getattr(node, name, _MISSING)
    except Exception:
        return _MISSING


def _node_semantics(node: Any) -> dict[str, Any]:
    """Return the interactive/semantic state ``node`` publishes.

    The half of a widget's state that :func:`describe_state` structurally cannot
    reach. ``disabled`` and ``focused`` are plain fields of an
    ``InteractionState``, never observables; ``selected`` and ``value`` are
    observable-backed but only under whatever private attribute the widget bound
    them to (``_state_internal``, ``checked_external_tri``), so the raw state
    dump names them differently for every widget. Here they are one vocabulary.

    The flags are reported only when set, so an ordinary node costs no bytes.
    ``value`` is reported whenever the widget has one: a toggle's ``False`` and a
    field's ``""`` are the answer as much as their opposites. A checkbox reports
    its checked state as ``value`` like every other toggle -- there is no
    separate ``checked``, which could not carry the indeterminate third state.
    """
    state = _probe(node, "state")
    if _probe(state, "focused") is _MISSING:
        # Something else named ``state``; only an InteractionState is a source.
        state = _MISSING

    semantics: dict[str, Any] = {}
    for name in _STATE_FLAGS:
        flag = _probe(node, name)
        if not isinstance(flag, bool):
            flag = _probe(state, name)
        if flag is True:
            semantics[name] = True

    value = _probe(node, "value")
    if value is not _MISSING:
        semantics["value"] = _coerce_value(value)
    return semantics


def _describe_node(node: Any, *, seen: set[int]) -> dict[str, Any]:
    """Build the JSON description for ``node`` and, recursively, its children."""
    info: dict[str, Any] = {"type": type(node).__name__}

    for attr in _IDENTITY_ATTRS:
        display = _coerce_display(getattr(node, attr, None))
        if display is not None:
            info[attr] = display

    semantics = _node_semantics(node)
    if semantics:
        info["state"] = semantics

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


def _target_matches(node: Any, *, key: Optional[str], label: Optional[str]) -> bool:
    """Whether ``node`` answers to either identifier.

    ``key`` matches a widget's ``key`` exactly (the testID set at construction);
    ``label`` matches any of a node's human-visible identities (``label`` /
    ``text`` / ``title``). Either alone is enough -- a target spec names one
    widget two ways, unlike a ``wait_for`` condition (:func:`_node_matches`),
    where every supplied field must hold.
    """
    if key is not None and _coerce_display(getattr(node, "key", None)) == key:
        return True
    return label is not None and label in _identity_values(node)


def find_targets(root: Any, *, key: Optional[str] = None, label: Optional[str] = None) -> list[Any]:
    """Return every widget matching ``key`` or ``label``, outermost first.

    Targets are stable identifiers, not pixels (see :func:`_target_matches`). The
    tree is searched depth-first, then a match nested inside another match is
    dropped: a composite that surfaces the identity it also composes into a child
    would otherwise report both, and a caller asking for "the Save button" means
    the button, not the ``Text`` inside it.

    Must be called on the UI thread (it reads live layout/observable state).
    """
    if root is None or (key is None and label is None):
        return []
    matches = [node for node in _iter_tree(root) if _target_matches(node, key=key, label=label)]
    matched = {id(node) for node in matches}
    return [node for node in matches if not any(id(a) in matched for a in ancestors(node))]


def find_target(root: Any, *, key: Optional[str] = None, label: Optional[str] = None) -> Optional[Any]:
    """Return the first widget matching ``key`` or ``label``, or ``None``.

    The first of :func:`find_targets`, which pre-order traversal makes the
    topmost, outermost match: a matching ancestor always precedes its descendant,
    so the head of the list is never the one the nesting rule drops.

    Must be called on the UI thread (it reads live layout/observable state).
    """
    targets = find_targets(root, key=key, label=label)
    return targets[0] if targets else None


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
    A widget that has the hook but is not clipping right now says so by
    returning ``None`` -- ``Box`` does exactly that unless ``clip_content`` is
    set, which is the common case.
    """
    probe = getattr(node, "visual_clip_rect", None)
    if not callable(probe):
        return None
    try:
        clip = probe()
    except Exception:
        return None
    if clip is None:
        return None
    cx, cy, cw, ch = clip
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

    The definition lives on ``WidgetKernel.global_visual_rect`` so that the
    app's own pointer path and this module agree by construction; this is the
    duck-typed front door for anything tree-shaped.
    """
    if hasattr(node, "global_visual_rect"):
        return node.global_visual_rect
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


def visible_rect(node: Any) -> Optional[tuple[float, float, float, float]]:
    """Return the part of ``node`` that is actually on screen, in root coordinates.

    :func:`global_visual_rect` answers "where is this node", which is the right
    question for aiming a pointer at it but the wrong one for *reporting* it: a
    child laid out larger than the ancestor that clips it keeps its full rect
    there, so the answer can name an area where nothing of the node is painted.
    A decorative shape oversized on purpose and trimmed to a corner is the
    common case, and a rect spanning a neighbouring pane is actively misleading
    to anyone -- human or assistant -- reading it as "this is what I pointed at".

    So this intersects the node's rect with every ancestor clip, and returns
    ``None`` when nothing survives (the node is laid out somewhere it is painted
    nowhere).
    """
    rect = global_visual_rect(node)
    if rect is None:
        return None
    x, y, w, h = rect
    for ancestor in ancestors(node):
        clip = _visual_clip_rect(ancestor)
        if clip is None:
            continue
        cx, cy, cw, ch = clip
        left, top = max(x, cx), max(y, cy)
        right, bottom = min(x + w, cx + cw), min(y + h, cy + ch)
        if right <= left or bottom <= top:
            return None
        x, y, w, h = left, top, right - left, bottom - top
    return (x, y, w, h)


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


def _visible_children(node: Any) -> list[Any]:
    """Return the children a *pick* may descend into, in traversal order.

    A container that keeps content mounted while it is off screen -- a ``Deck``
    showing one page, a ``Navigator`` whose top route covers the rest -- narrows
    ``focus_traversal_children()`` to what the user can currently act on, on the
    grounds (see
    :meth:`nuiitivet.widgeting.widget_children.WidgetChildren.focus_traversal_children`)
    that "``paint`` and ``hit_test`` already narrow the same way ... so Tab stops
    where the eye does". A picker has to stop where the eye does too, so it asks
    the same question rather than inventing a second notion of visibility.

    Occlusion filtering cannot substitute for this. :func:`find_obstruction`
    deliberately does not report a ``None`` hit as an obstruction -- that is what
    keeps a non-interactive target reachable -- so an entirely non-interactive
    hidden subtree (two ``Text`` pages in a ``Deck``) is invisible to the
    occlusion check and would otherwise be picked in preference to the page on
    screen.

    ``FocusTraversalBlocker`` is deliberately *not* honoured: it hides a subtree
    from Tab, but a disabled ``Clickable`` is plainly visible and must stay
    pickable. It is a separate mechanism (a ``blocks_focus_traversal`` property),
    so descending through ``focus_traversal_children()`` alone skips it.

    Falls back to ``children`` for anything without the hook, and always appends
    ``built_child`` -- the default ``focus_traversal_children()`` reports only the
    laid-out children, so a :class:`ComposableWidget`'s subtree would be lost.
    """
    probe = getattr(node, "focus_traversal_children", None)
    kids: list[Any] = []
    if callable(probe):
        try:
            kids = [child for child in probe() if child is not None]
        except Exception:
            kids = []
    else:
        kids = [child for child in (getattr(node, "children", ()) or ()) if child is not None]
    built = getattr(node, "built_child", None)
    if built is not None and built is not node and not any(child is built for child in kids):
        kids.append(built)
    return kids


def _is_visually_empty(node: Any) -> bool:
    """Whether ``node`` is currently drawing nothing at all.

    The opt-in companion to ``visual_offset`` / ``visual_clip_rect``, probed by
    name for the same reason: a container that stays mounted at full size while
    showing nothing -- an ``Overlay`` with no open entries -- reports
    ``is_visually_empty() -> True`` and drops out of picking along with its whole
    subtree.

    Geometry cannot detect this and neither can occlusion. Such a container keeps
    a full-window rect, so it contains every point; and ``find_obstruction``
    clears it, because ``hit_test`` there returns ``None`` and a ``None`` hit is
    deliberately not an obstruction (that rule is what keeps a non-interactive
    target reachable). Painted on top of everything, it would otherwise shadow
    the entire app -- and precisely for the non-interactive widgets ``pick_at``
    exists to reach.
    """
    probe = getattr(node, "is_visually_empty", None)
    if not callable(probe):
        return False
    try:
        return bool(probe())
    except Exception:
        return False


def _pick(root: Any, node: Any, x: float, y: float, seen: set[int]) -> Optional[Any]:
    """Depth-first, top-most-first search for the deepest reachable node at ``(x, y)``."""
    if node is None or id(node) in seen:
        return None
    seen.add(id(node))
    if _is_visually_empty(node):
        return None

    # Reversed, so a later sibling -- painted on top -- is tried first. This is
    # the convention ``_hit_test_children`` already works in.
    for child in reversed(_visible_children(node)):
        picked = _pick(root, child, x, y, seen)
        if picked is not None:
            return picked

    rect = global_visual_rect(node)
    if rect is None or rect[2] <= 0 or rect[3] <= 0:
        return None
    if not _contains(rect, x, y):
        return None
    if find_obstruction(root, node, x, y) is not None:
        return None
    return node


def pick_at(root: Any, x: float, y: float) -> Optional[Any]:
    """Return the widget a human pointing at root-space ``(x, y)`` means, or ``None``.

    The devtools-picker counterpart to ``hit_test``, and deliberately not built on
    it: ``hit_test`` returns the deepest *hit-participating* widget, but the node
    a human wants to point at is frequently one that participates in no hit
    testing at all -- a plain ``Text``, a spacing ``Container``. This is purely
    geometric, so those are reachable.

    The deepest node whose :func:`global_visual_rect` contains the point wins,
    with three qualifications:

    * **Descent is narrowed to what is on screen** (:func:`_visible_children`), so
      a ``Deck``'s hidden page or a ``Navigator``'s covered route is never a
      candidate in the first place, and a container that reports itself
      :func:`visually empty <_is_visually_empty>` -- an ``Overlay`` with nothing
      open -- drops out with its whole subtree.
    * **Siblings are visited in reverse**, matching the top-most-first order
      ``_hit_test_children`` uses, so the node painted on top wins an overlap.
    * **Zero-size nodes are skipped, and unreachable ones rejected**
      (:func:`find_obstruction`: clipped out of a scrolled region, or covered by
      something in an unrelated subtree). A rejected candidate falls back to the
      next one out, so a click over a clipped row lands on whatever is genuinely
      painted there.

    A layout-only wrapper stacking several rects under one pixel is skipped in
    favour of its deepest child; walking back out to it is the caller's job (the
    ancestor walk in inspect mode), not this function's.

    Must be called on the UI thread (it reads live layout state).

    Args:
        root: The mounted root widget (``App.root``).
        x: Root-space x coordinate.
        y: Root-space y coordinate.

    Returns:
        The picked widget, or ``None`` if the point reaches nothing.
    """
    if root is None:
        return None
    return _pick(root, root, float(x), float(y), set())


def _rect_intersects(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def _rect_encloses(outer: tuple[float, ...], inner: tuple[float, ...]) -> bool:
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return ox <= ix and oy <= iy and ox + ow >= ix + iw and oy + oh >= iy + ih


def _visible_rect(node: Any) -> Optional[tuple[float, float, float, float]]:
    """A node's painted rect, or ``None`` when it has none or is degenerate."""
    rect = visible_rect(node)
    if rect is None or rect[2] <= 0 or rect[3] <= 0:
        return None
    return rect


def _iter_visible(node: Any, seen: set[int]) -> Any:
    """Yield ``node`` and every descendant the eye can currently reach."""
    if node is None or id(node) in seen or _is_visually_empty(node):
        return
    seen.add(id(node))
    yield node
    for child in _visible_children(node):
        yield from _iter_visible(child, seen)


def enclosing_container(root: Any, rect: tuple[float, float, float, float]) -> Optional[Any]:
    """Return the innermost visible node whose rect wholly encloses ``rect``.

    The anchor for a designated *region*. When the human draws a box over
    empty space there is no widget to name, and this is the entire answer: it
    names the widget that *should* have painted something there.

    Descends through the same narrowing :func:`pick_at` uses, so a ``Deck``'s
    hidden page or an idle ``Overlay`` never answers for a region drawn over the
    content in front of it.

    Must be called on the UI thread (it reads live layout state).
    """
    if root is None:
        return None
    found: Optional[Any] = None
    for node in _iter_visible(root, set()):
        node_rect = _visible_rect(node)
        if node_rect is not None and _rect_encloses(node_rect, rect):
            # Pre-order, so a later match is always deeper than an earlier one.
            found = node
    return found


def _relation(node_rect: tuple[float, ...], rect: tuple[float, ...]) -> Optional[str]:
    """How ``node_rect`` stands to a designated region, or ``None`` if it misses it."""
    if not _rect_intersects(node_rect, rect):
        return None
    return "contained" if _rect_encloses(rect, node_rect) else "clipped"


def _intersection_node(
    node: Any, rect: tuple[float, float, float, float], seen: set[int]
) -> Optional[tuple[Any, Optional[str], list[Any]]]:
    """Build the pruned intersection subtree rooted at ``node``, or ``None``."""
    if node is None or id(node) in seen or _is_visually_empty(node):
        return None
    seen.add(id(node))
    children = [
        described
        for described in (_intersection_node(child, rect, seen) for child in _visible_children(node))
        if described is not None
    ]
    node_rect = _visible_rect(node)
    relation = _relation(node_rect, rect) if node_rect is not None else None
    if relation is None and not children:
        return None
    return (node, relation, children)


def intersecting_subtree(
    container: Any, rect: tuple[float, float, float, float]
) -> list[tuple[Any, Optional[str], list[Any]]]:
    """Return what a designated region covers, as a pruned ``(node, relation, children)`` tree.

    Scoped to ``container``'s subtree, which is what makes an *intersection* rule
    workable at all: humans drag rough boxes, but a bare intersection test
    against the whole tree would also match every ancestor, each of which
    trivially overlaps. ``container`` encloses the region by definition, so its
    subtree is exactly the right scope and the ancestor chain drops out without a
    special case.

    ``relation`` is ``"contained"`` when the node lies wholly inside the region,
    ``"clipped"`` when it only overlaps, and ``None`` for a node kept solely
    because a descendant matched -- the same pruning shape
    :func:`describe_state` uses, so the result reads like the other dumps.

    **Nothing is collapsed.** An earlier flat form applied :func:`find_targets`'
    rule -- drop a match nested inside another match -- and that is wrong here.
    It answers "which widget did you name?", where the outermost match is the one
    meant; a region asks "what is under this box?", where the same rectangle may
    equally mean the gap between things or the things it crosses. Geometry cannot
    tell those apart, so collapsing to one reading destroyed the other: a band
    drawn across a column reported only the column. The structure is reported
    instead, and the caller -- which knows what the human said -- decides.

    May legitimately be empty: a region over blank space covers nothing, which is
    the signal rather than a failure. :func:`enclosing_container` still answers.

    Must be called on the UI thread (it reads live layout state).
    """
    if container is None:
        return []
    described = _intersection_node(container, rect, set())
    # The container itself always intersects; its subtree is the answer.
    return described[2] if described is not None else []


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

    Must be called on the UI thread (it reads live layout and interaction state).
    Each node maps to ``{"type", optional "key"/"label"/"text"/"title", optional
    "state", optional "rect", optional "children"}`` where ``rect`` is
    ``[x, y, w, h]`` in root coordinates.

    ``state`` is the interactive state the widget publishes (see
    :func:`_node_semantics`), in the widget's own vocabulary: ``disabled`` /
    ``focused`` / ``selected`` / ``value``. It is not :func:`describe_state`'s
    ``state``, which is the raw ``Observable`` attributes underneath, named as
    the widget bound them.

    Args:
        root: The mounted root widget (``App.root``).

    Returns:
        The root node's description, or ``{}`` if ``root`` is ``None``.
    """
    if root is None:
        return {}
    return _describe_node(root, seen=set())


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
    dump.
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

    These are the *raw* observables, named as the widget bound them
    (``_state_internal``, ``checked_external_tri``); :func:`describe_tree`'s own
    ``state`` reports the same widget in its published vocabulary instead. Reach
    for this one when that vocabulary is not the level the bug is at.

    ``Animatable`` state is **omitted by default**: an interactive widget
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
