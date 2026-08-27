"""Action primitives: drive a running app.

Where :mod:`nuiitivet._interaction.perception` lets a driver *see* the running
app, this module lets it *act* on it -- the second half of the perception-action
loop. Each verb synthesizes the same input the real backend delivers:

* :func:`click` resolves a stable target (``key`` / ``label``) to the point it
  occupies *on screen* (``perception.global_visual_rect``) and fires a
  press/release through the app's own pointer dispatch
  (``runtime/app_events.py``). Targeting by identifier, not raw pixels, survives
  layout changes.
* :func:`scroll` synthesizes a wheel event over a scroll *region* -- named as
  itself, never via a row inside it -- reporting where it ended up.
* :func:`scroll_into_view` moves a target's region(s) until it is reachable --
  the answer to the :class:`TargetNotVisibleError` the others raise.
* :func:`type_text` injects text into the focused widget.
* :func:`press_key` injects a key press/release (with modifiers -> shortcuts).

Every pointer verb *verifies* its resolved point reaches the target before
dispatching. A target that is scrolled out of its region or covered by an
overlay is a :class:`TargetNotVisibleError`, never a silent event delivered to
whatever happened to be at those coordinates.

Every verb runs on the UI thread -- getting there is the driver's job -- and
calls :func:`settle` afterwards so the tree is laid out before the next
``describe_tree`` / ``screenshot`` observes it. A verb is otherwise silent: what
it did is reported to the caller's optional :class:`ActionObserver`, which is
how the dev bridge draws its on-screen markers without a test harness paying for
them.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Protocol

from .perception import ancestors, find_obstruction, find_target, global_visual_rect
from nuiitivet.input.codes import (
    MOD_ACCEL,
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
)

logger = logging.getLogger(__name__)

# Names accepted for ``press_key`` / the ``key`` CLI so callers need not know the
# raw bit masks. ``accel`` is the platform-correct Ctrl/Cmd (see ``input.codes``).
_MODIFIER_NAMES: dict[str, int] = {
    "shift": MOD_SHIFT,
    "ctrl": MOD_CTRL,
    "control": MOD_CTRL,
    "alt": MOD_ALT,
    "option": MOD_ALT,
    "meta": MOD_META,
    "cmd": MOD_META,
    "command": MOD_META,
    "super": MOD_META,
    "win": MOD_META,
    "accel": MOD_ACCEL,
}


class TargetNotFoundError(LookupError):
    """No widget matched the requested ``key`` / ``label``."""


class TargetNotVisibleError(TargetNotFoundError):
    """The target matched, but the point it resolves to cannot reach it.

    Scrolled out of its region, or covered by something on top. A subclass of
    :class:`TargetNotFoundError` so it rides the bridge's existing 404 branch:
    either way the assistant cannot act on the target as things stand, and the
    message says which it is.
    """


class LayoutNotConvergedError(RuntimeError):
    """A strict :func:`settle` ran out of passes with the tree still changing.

    A size callback that resizes what it measures never settles. Raising says so
    at the action that triggered it, rather than letting the caller assert
    against whichever half-laid-out frame the last pass happened to leave.
    """


class ActionObserver(Protocol):
    """What a driver implements to be told what each verb just did.

    One protocol for all five verbs, so a driver registers a single object: a
    point for the pointer verbs, wheel notches for the scroll ones, the keystroke
    for :func:`press_key`. ``target`` is the resolved widget's ``key``, or
    ``None`` when the verb was aimed at raw coordinates or an unkeyed widget.

    Called *after* the input is dispatched and before :func:`settle`, on the UI
    thread. A raising hook propagates -- containing that is the driver's business,
    since only it knows whether its side effect is worth failing an action over.
    """

    def on_click(self, app: Any, x: float, y: float, *, target: Optional[str]) -> None:
        """A press+release was dispatched at root-space ``(x, y)``."""
        ...

    def on_scroll(
        self,
        app: Any,
        x: float,
        y: float,
        *,
        dx: float,
        dy: float,
        target: Optional[str],
        verb: str,
    ) -> None:
        """A region at ``(x, y)`` was scrolled by ``dx`` / ``dy`` wheel notches.

        ``verb`` names which primitive moved it (``"scroll"`` or
        ``"scroll into view"``), since the two look identical on screen.
        """
        ...

    def on_type(self, app: Any) -> None:
        """Text was injected into the focused widget.

        The text itself is deliberately not passed: an observer that draws or
        logs it would leak field content into a screenshot or a journal.
        """
        ...

    def on_key(self, app: Any, key: str, modifiers: int) -> None:
        """A key press+release was dispatched with the given modifier mask."""
        ...


def resolve_modifiers(modifiers: Any) -> int:
    """Coerce a modifier spec to an int mask.

    Accepts an int (returned as-is), or an iterable of names
    (``["ctrl", "shift"]``) resolved via :data:`_MODIFIER_NAMES`.

    Raises:
        ValueError: If a name is not a recognized modifier.
    """
    if modifiers is None:
        return 0
    if isinstance(modifiers, int):
        return modifiers
    mask = 0
    for name in modifiers:
        try:
            mask |= _MODIFIER_NAMES[str(name).strip().lower()]
        except KeyError as exc:
            known = ", ".join(sorted(_MODIFIER_NAMES))
            raise ValueError(f"unknown modifier {name!r}; expected one of: {known}") from exc
    # Synthesized input stands in for a backend, and backends never emit the
    # logical ``MOD_ACCEL`` bit — resolve it to the platform's physical mask so
    # ``"accel"`` actually matches ``Shortcut`` bindings.
    from nuiitivet.input.codes import resolve_modifiers as _resolve_accel

    return _resolve_accel(mask)


def _target_point(app: Any, node: Any, *, verb: str) -> tuple[float, float]:
    """Return the on-screen point to dispatch ``verb`` at for ``node``.

    The centre of the node's rect *as painted* (:func:`global_visual_rect`, not
    ``global_layout_rect`` -- inside a scrolled region the two differ by the
    scroll offset), verified to actually reach it before anything is
    synthesized. Without that check a resolution defect returns a cheerful
    ``{"clicked": …}`` for an event that landed somewhere else entirely.

    Raises:
        TargetNotFoundError: If the node has no rect yet (never laid out).
        TargetNotVisibleError: If the point cannot reach it (scrolled out of
            view, or covered).
    """
    rect = global_visual_rect(node)
    if rect is None:
        raise TargetNotFoundError(
            f"{type(node).__name__} has no layout rect yet (not laid out); cannot {verb} it"
        )
    x, y, w, h = rect
    px, py = x + w / 2.0, y + h / 2.0

    obstruction = find_obstruction(getattr(app, "root", None), node, px, py)
    if obstruction is not None:
        raise TargetNotVisibleError(
            f"{type(node).__name__} resolves to ({px:.0f}, {py:.0f}) but is {obstruction}; "
            "'scroll_into_view' it first, or check for an overlay"
        )
    return (px, py)


def _resolve_point(
    app: Any,
    *,
    key: Optional[str],
    label: Optional[str],
    x: Optional[float],
    y: Optional[float],
    verb: str,
    require: Optional[Callable[[Any], None]] = None,
) -> tuple[float, float, dict[str, Any]]:
    """Resolve a target spec to a dispatch point plus the identity to echo back.

    Shared by every pointer verb: a stable identifier (``key`` / ``label``) is
    resolved and verified, raw ``x`` / ``y`` root coordinates are taken as given
    (the caller asked for a pixel, and there is no target to verify against).

    ``require`` is an optional check a verb imposes on the *kind* of widget it
    accepts -- ``scroll`` only acts on a scroll region -- run before the
    geometric checks, since "you named the wrong sort of thing" explains a
    mistake that "it is off screen" would only describe.

    Raises:
        ValueError: If neither an identifier nor explicit coordinates are given.
        TargetNotFoundError: If the identifier matched nothing.
    """
    if key is not None or label is not None:
        node = find_target(app.root, key=key, label=label)
        if node is None:
            raise TargetNotFoundError(_no_match_message(key, label))
        if require is not None:
            require(node)
        px, py = _target_point(app, node, verb=verb)
        return (px, py, _describe_target(node))
    if x is not None and y is not None:
        return (float(x), float(y), {})
    raise ValueError(f"{verb} requires a 'key', a 'label', or explicit 'x' and 'y'")


def _is_scroll_region(node: Any) -> bool:
    """Whether ``node`` is a widget a wheel event can actually move.

    Probed by the ``scroll_metrics`` hook a scroll region exposes, so this stays
    independent of :mod:`nuiitivet.layout`.
    """
    return callable(getattr(node, "scroll_metrics", None))


def _enclosing_scroll_region(node: Any) -> Optional[Any]:
    """Return the scroll region ``node`` sits in, or ``None``.

    A region is layered -- an app-authored ``VerticalScrollable`` wrapping the
    ``ScrollViewport`` that does the clipping -- so this returns the *outermost*
    of the contiguous run nearest to ``node``: the one the app actually
    constructed, and therefore the one a ``keyed()`` can be attached to.
    """
    region: Optional[Any] = None
    for ancestor in ancestors(node):
        if _is_scroll_region(ancestor):
            region = ancestor
        elif region is not None:
            break
    return region


def _require_scroll_region(node: Any) -> None:
    """Reject a ``scroll`` target that is not itself a scroll region.

    Naming a *row* rather than the list is the tempting mistake, because a row
    is what carries an identity in ``describe_tree`` while the region often
    carries none. It is also self-defeating: the wheel would move the row off
    screen, invalidating the very target that aimed it, so the next call in a
    scroll loop fails. Refusing it -- and naming the region plus the coordinates
    that reach it -- turns that dead end into one legible error.

    Raises:
        ValueError: If ``node`` cannot be scrolled.
    """
    if _is_scroll_region(node):
        return

    what = f"{type(node).__name__} is not a scrollable region"
    region = _enclosing_scroll_region(node)
    if region is None:
        raise ValueError(f"{what}, and it is not inside one -- there is nothing here to scroll")

    where = ""
    rect = global_visual_rect(region)
    if rect is not None:
        cx, cy = rect[0] + rect[2] / 2.0, rect[1] + rect[3] / 2.0
        where = f" at {tuple(round(v) for v in rect)}"
    raise ValueError(
        f"{what}. It sits inside a {type(region).__name__}{where}: target that region "
        "instead -- give it a stable key with keyed(), or pass "
        + (f"x={cx:.0f} y={cy:.0f}" if rect is not None else "explicit 'x' and 'y'")
        + ". To bring this widget on screen instead, use 'scroll_into_view'."
    )


def _describe_target(node: Any) -> dict[str, Any]:
    """A compact identity for a resolved target, echoed back to the caller."""
    info: dict[str, Any] = {"type": type(node).__name__}
    key = getattr(node, "key", None)
    if isinstance(key, str) and key:
        info["key"] = key
    return info


def settle(
    app: Any,
    *,
    strict: bool = False,
    max_passes: int = 3,
    before_pass: Optional[Callable[[], object]] = None,
) -> None:
    """Flush pending reactive work and re-lay-out the tree after an action.

    An action mutates observables; the visible effect (and any layout change)
    lands on the *next* frame. To make the immediately-following ``describe_tree``
    / ``screenshot`` observe the settled state, flush binding invalidations and
    scope recompositions, then run a layout pass so ``global_layout_rect`` is
    current. Runs on the UI thread; never paints (perception needs geometry, not
    pixels).

    Args:
        app: The running app.
        strict: Let a failing flush or layout reach the caller, run passes until
            the tree stops changing rather than a fixed two, and skip
            ``app.invalidate()``. Default off, because a long-lived session must
            survive a bad frame and re-settles on the next call; a test must fail
            on one, or it asserts against a stale tree and passes.
        max_passes: Cap on the strict pass count, so a size callback that resizes
            what it measures raises instead of looping forever. Ignored when
            ``strict`` is off.
        before_pass: Called at the top of every pass, before the flushes. The
            hook a driver needs to advance whatever *it* owns between passes --
            the test harness pumps its clock's zero-delay queue here, so a
            cross-thread marshal produced by one pass is applied in the
            next. Not a policy this module has: the bridge runs against a real
            clock that drains itself, and passes nothing. A raising hook
            propagates, in both modes -- it is the caller's own code.

    Raises:
        LayoutNotConvergedError: If ``strict`` and the tree is still changing
            after ``max_passes``.
    """
    if strict:
        _settle_strict(app, max_passes=max_passes, before_pass=before_pass)
        return

    from nuiitivet.widgeting.widget_binding import flush_binding_invalidations
    from nuiitivet.widgeting.widget_builder import flush_scope_recompositions
    from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks

    def _flush_reactive() -> None:
        if before_pass is not None:
            before_pass()
        try:
            flush_binding_invalidations()
        except Exception:
            logger.debug("settle: flush_binding_invalidations failed", exc_info=True)
        try:
            flush_scope_recompositions()
        except Exception:
            logger.debug("settle: flush_scope_recompositions failed", exc_info=True)

    def _layout(root: Any) -> None:
        try:
            root.layout(int(app.width), int(app.height))
            root.clear_needs_layout()
        except Exception:
            logger.debug("settle: layout pass failed", exc_info=True)

    _flush_reactive()

    root = getattr(app, "root", None)
    if root is None:
        return
    _layout(root)

    # A size callback fires only after layout has measured its widget, so the
    # state it drives is one pass behind. Run that pass here too, otherwise the
    # following describe_tree observes the pre-callback tree.
    try:
        flush_size_change_callbacks()
    except Exception:
        logger.debug("settle: flush_size_change_callbacks failed", exc_info=True)
    _flush_reactive()
    root = getattr(app, "root", None)
    if root is not None:
        _layout(root)

    # Request a real repaint so the on-screen frame reflects the action too.
    try:
        app.invalidate()
    except Exception:
        logger.debug("settle: invalidate failed", exc_info=True)


def _settle_strict(
    app: Any, *, max_passes: int, before_pass: Optional[Callable[[], object]] = None
) -> None:
    """Settle with nothing swallowed, looping until the tree stops changing.

    Mirrors :meth:`nuiitivet.runtime.app.App._settle_pending_size_changes`, the
    framework's settle for a one-shot render, which is the caller of the same
    kind: it must be *correct* rather than merely survive. No ``invalidate`` --
    there is no frame to request, and a caller counting repaints must not count
    settle's own.
    """
    from nuiitivet.widgeting.widget_binding import flush_binding_invalidations
    from nuiitivet.widgeting.widget_builder import flush_scope_recompositions
    from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks

    def run_pass(root: Any) -> None:
        # Before the flushes, not after: a hook that mutates observables (the
        # harness pumping a cross-thread marshal) needs the same pass to
        # turn that into an updated tree, or the value lands one pass late and
        # the final pass never lands it at all.
        if before_pass is not None:
            before_pass()
        flush_binding_invalidations()
        flush_scope_recompositions()
        root.layout(int(app.width), int(app.height))
        root.clear_needs_layout()

    root = getattr(app, "root", None)
    if root is None:
        return
    run_pass(root)
    for _ in range(max_passes):
        if not flush_size_change_callbacks():
            return
        run_pass(root)
    raise LayoutNotConvergedError(
        f"tree still changing after {max_passes} settle passes: a size callback keeps "
        "resizing what it measures"
    )


def check_condition(
    app: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    text: Optional[str] = None,
    present: bool = True,
) -> bool:
    """Settle the app, then evaluate a ``wait_for`` condition once (one poll).

    This is a *single* poll meant to run on the UI thread. Settling first flushes
    the synchronous reactive work an in-flight async update may have just
    produced, so the condition sees the freshest tree; the caller (the bridge's
    ``/wait_for`` loop) re-invokes this across the worker thread, sleeping between
    polls so the UI thread is free to advance asynchronous work between them.

    Raises:
        ValueError: If none of ``key`` / ``label`` / ``text`` is given.
    """
    from .perception import match_condition

    settle(app)
    return match_condition(app.root, key=key, label=label, text=text, present=present)


def click(
    app: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    button: Optional[int] = None,
    on_action: Optional[ActionObserver] = None,
) -> dict[str, Any]:
    """Synthesize a primary press+release at a resolved target.

    Provide a stable identifier (``key`` or ``label``) -- resolved to the center
    of its layout rect -- or raw ``x`` / ``y`` root coordinates as a fallback.

    Raises:
        ValueError: If neither an identifier nor explicit coordinates are given.
        TargetNotFoundError: If the identifier matched nothing (or it has no rect).
        TargetNotVisibleError: If the target is scrolled out of view or covered.
    """
    px, py, target_info = _resolve_point(app, key=key, label=label, x=x, y=y, verb="click")

    ix, iy = int(round(px)), int(round(py))
    app._dispatch_mouse_press(ix, iy, button=button)
    app._dispatch_mouse_release(ix, iy, button=button)
    if on_action is not None:
        on_action.on_click(app, px, py, target=target_info.get("key"))
    settle(app)
    return {"clicked": target_info, "x": ix, "y": iy}


def scroll(
    app: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    dx: float = 0.0,
    dy: float = 0.0,
    on_action: Optional[ActionObserver] = None,
) -> dict[str, Any]:
    """Synthesize a mouse wheel event over a scroll region.

    ``key`` / ``label`` mean the same thing they mean everywhere -- *this*
    widget -- so the one named here must be the scroll region itself, not
    something inside it. A row is refused (see :func:`_require_scroll_region`):
    it would work once and then be scrolled out of reach by its own wheel event.
    ``x`` / ``y`` remain available for a region that carries no identity.

    ``dx`` / ``dy`` are **wheel
    notches**, not pixels: the region multiplies them by its
    ``scroll_multiplier``, 20 px per notch by default -- so ``dy=5`` moves a
    default region 100 px. Positive is toward the content's end (down / right),
    the framework's internal convention that the backend normalizes real wheel
    input into, so a synthesized event and a real one behave identically. A
    delta the region rounds away (``abs < 0.01``) is discarded by the handler.
    Scrolling is linear with no inertia, so one ``dy=10`` equals ten ``dy=1``;
    prefer the single call.

    The result reports what actually happened -- ``handled`` plus the region's
    resulting ``offset`` / ``max_extent`` / ``at_start`` / ``at_end`` -- because
    unlike a click, "already at the end" and "nothing consumed it" are otherwise
    indistinguishable from success, leaving the caller no stop condition.

    Raises:
        ValueError: If both deltas are zero, no target is given, or the named
            target is not a scroll region.
        TargetNotFoundError: If the identifier matched nothing.
        TargetNotVisibleError: If the region is scrolled out of view or covered.
    """
    ddx, ddy = float(dx), float(dy)
    if ddx == 0.0 and ddy == 0.0:
        raise ValueError("scroll needs a non-zero 'dx' or 'dy' (in wheel notches)")

    px, py, target_info = _resolve_point(
        app, key=key, label=label, x=x, y=y, verb="scroll", require=_require_scroll_region
    )
    ix, iy = int(round(px)), int(round(py))

    handler = app._dispatch_mouse_scroll(ix, iy, ddx, ddy)
    result: dict[str, Any] = {
        "scrolled": target_info,
        "x": ix,
        "y": iy,
        "dx": ddx,
        "dy": ddy,
        "handled": handler is not None,
    }
    if handler is not None:
        result["handled_by"] = _describe_target(handler)
        result.update(_scroll_metrics(handler))

    if on_action is not None:
        on_action.on_scroll(
            app, px, py, dx=ddx, dy=ddy, target=target_info.get("key"), verb="scroll"
        )
    settle(app)
    return result


def scroll_into_view(
    app: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    align: str = "nearest",
    on_action: Optional[ActionObserver] = None,
) -> dict[str, Any]:
    """Scroll the target's region(s) until the target is reachable.

    What :func:`scroll` cannot express: it is wheel-shaped ("send N notches
    here"), so "make this widget clickable" becomes a poll loop in 20 px steps.
    This computes the offset directly and applies it in one shot, guaranteeing
    the postcondition -- the answer to the :class:`TargetNotVisibleError` a
    ``click`` on an off-screen target now raises.

    Deliberately not routed through the wheel path: :func:`scroll` earns its
    keep by being real input that exercises the app's own handlers, while this
    one is exact and single-shot. Nested regions are resolved outermost-inward.

    Args:
        app: The running app.
        key: Target the widget whose ``key`` matches.
        label: Target the widget whose visible label/text/title matches.
        align: Where to land the target: ``"nearest"`` (default, move as little
            as possible), ``"start"``, ``"center"`` or ``"end"``.

    Raises:
        ValueError: If no identifier is given, ``align`` is unknown, or the
            target sits in no scrollable region at all (nothing to scroll --
            reported rather than passed off as success).
        TargetNotFoundError: If the identifier matched nothing.
    """
    if key is None and label is None:
        raise ValueError("scroll_into_view requires a 'key' or a 'label'")
    node = find_target(app.root, key=key, label=label)
    if node is None:
        raise TargetNotFoundError(_no_match_message(key, label))

    regions = _scrollable_ancestors(node)
    if not regions:
        raise ValueError(
            f"{type(node).__name__} is not inside a scrollable region; nothing to scroll "
            "(it is already wherever the layout put it)"
        )

    # Outermost first, each revealing the next region inward -- so an inner
    # region is itself on screen before it is asked to reveal the target.
    moved = 0.0
    innermost_delta = 0.0
    for index, region in enumerate(regions):
        reveal = regions[index + 1] if index + 1 < len(regions) else node
        local = _local_rect(reveal, region)
        if local is None:
            continue
        innermost_delta = region.scroll_rect_into_view(local, align=align)
        moved += abs(innermost_delta)

    settle(app)

    metrics = _scroll_metrics(regions[-1])
    result: dict[str, Any] = {
        "scrolled_into_view": _describe_target(node),
        "already_visible": moved == 0.0,
    }
    result.update(metrics)

    rect = global_visual_rect(node)
    if on_action is not None and rect is not None and moved:
        # A positive offset delta moves the content toward its end, i.e. the
        # same direction a positive wheel delta would have sent it.
        step = 1.0 if innermost_delta > 0 else -1.0
        horizontal = metrics.get("axis") == "horizontal"
        on_action.on_scroll(
            app,
            rect[0] + rect[2] / 2.0,
            rect[1] + rect[3] / 2.0,
            dx=step if horizontal else 0.0,
            dy=0.0 if horizontal else step,
            target=result["scrolled_into_view"].get("key"),
            verb="scroll into view",
        )
    return result


def _scrollable_ancestors(node: Any) -> list[Any]:
    """Return the scrollable regions containing ``node``, outermost first.

    A region is anything exposing ``scroll_rect_into_view`` (``ScrollViewport``
    today), probed by name so this module needs no import from
    :mod:`nuiitivet.layout`.
    """
    regions = [a for a in ancestors(node) if callable(getattr(a, "scroll_rect_into_view", None))]
    regions.reverse()
    return regions


def _local_rect(node: Any, container: Any) -> Optional[tuple[float, float, float, float]]:
    """Return ``node``'s rect in ``container``'s local (content) coordinates.

    Both rects come from ``global_layout_rect``, which accumulates layout
    offsets only -- so their difference is scroll-independent, which is exactly
    the space a viewport's own scroll math works in.
    """
    inner = getattr(node, "global_layout_rect", None)
    outer = getattr(container, "global_layout_rect", None)
    if inner is None or outer is None:
        return None
    return (float(inner[0] - outer[0]), float(inner[1] - outer[1]), float(inner[2]), float(inner[3]))


def _scroll_metrics(widget: Any) -> dict[str, Any]:
    """Read a scrollable widget's reported position, or ``{}`` if it reports none."""
    probe = getattr(widget, "scroll_metrics", None)
    if not callable(probe):
        return {}
    try:
        metrics = probe()
    except Exception:
        logger.debug("scroll: reading scroll metrics failed", exc_info=True)
        return {}
    return dict(metrics) if isinstance(metrics, dict) else {}


def type_text(
    app: Any, text: str, *, on_action: Optional[ActionObserver] = None
) -> dict[str, Any]:
    """Inject ``text`` into the currently focused widget.

    A widget must be focused first (e.g. ``click`` a text field); with nothing
    focused the app has nowhere to route the text and ``handled`` is ``False``.
    """
    handled = bool(app._dispatch_text(str(text)))
    if on_action is not None:
        on_action.on_type(app)
    settle(app)
    return {"typed": str(text), "handled": handled}


def press_key(
    app: Any, key: str, modifiers: Any = 0, *, on_action: Optional[ActionObserver] = None
) -> dict[str, Any]:
    """Synthesize a key press+release (e.g. ``enter``, ``tab``, ``a``).

    ``modifiers`` is an int mask or an iterable of names (``["accel", "shift"]``);
    it drives shortcut and focus-traversal behavior just like a real key event.
    """
    mask = resolve_modifiers(modifiers)
    name = str(key)
    handled = bool(app._dispatch_key_press(name, mask))
    try:
        app._dispatch_key_release(name, mask)
    except Exception:
        logger.debug("press_key: key release dispatch failed", exc_info=True)
    if on_action is not None:
        on_action.on_key(app, name, mask)
    settle(app)
    return {"key": name, "modifiers": mask, "handled": handled}


def _no_match_message(key: Optional[str], label: Optional[str]) -> str:
    if key is not None and label is not None:
        what = f"key={key!r} / label={label!r}"
    elif key is not None:
        what = f"key={key!r}"
    else:
        what = f"label={label!r}"
    return f"no widget matched {what}; run 'describe-tree' to see available targets"
