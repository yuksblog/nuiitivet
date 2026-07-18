"""Action primitives for the dev bridge: drive a running app (dev-only).

Where :mod:`nuiitivet.dev.perception` lets an assistant *see* the running app,
this module lets it *act* on it -- the second half of the perception-action loop
(#375). Each verb synthesizes the same input the real backend delivers:

* :func:`click` resolves a stable target (``key`` / ``label``) to coordinates via
  ``global_layout_rect`` and fires a press/release through the app's own pointer
  dispatch (``runtime/app_events.py``). Targeting by identifier, not raw pixels,
  survives layout changes.
* :func:`type_text` injects text into the focused widget.
* :func:`press_key` injects a key press/release (with modifiers -> shortcuts).

Every verb runs on the UI thread (the :class:`~nuiitivet.dev.bridge.DevBridge`
marshals it there) and calls :func:`settle` afterwards so the tree is laid out
before the next ``describe_tree`` / ``screenshot`` observes it.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .perception import find_target
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
    return mask


def _target_center(node: Any) -> tuple[float, float]:
    """Return the center point of ``node``'s layout rect in root coordinates."""
    rect = getattr(node, "global_layout_rect", None)
    if rect is None:
        raise TargetNotFoundError(
            f"{type(node).__name__} has no layout rect yet (not laid out); cannot click it"
        )
    x, y, w, h = rect
    return (x + w / 2.0, y + h / 2.0)


def _describe_target(node: Any) -> dict[str, Any]:
    """A compact identity for a resolved target, echoed back to the caller."""
    info: dict[str, Any] = {"type": type(node).__name__}
    key = getattr(node, "key", None)
    if isinstance(key, str) and key:
        info["key"] = key
    return info


def settle(app: Any) -> None:
    """Flush pending reactive work and re-lay-out the tree after an action.

    An action mutates observables; the visible effect (and any layout change)
    lands on the *next* frame. To make the immediately-following ``describe_tree``
    / ``screenshot`` observe the settled state, flush binding invalidations and
    scope recompositions, then run a layout pass so ``global_layout_rect`` is
    current. Runs on the UI thread; never paints (perception needs geometry, not
    pixels).
    """
    from nuiitivet.widgeting.widget_binding import flush_binding_invalidations
    from nuiitivet.widgeting.widget_builder import flush_scope_recompositions

    try:
        flush_binding_invalidations()
    except Exception:
        logger.debug("settle: flush_binding_invalidations failed", exc_info=True)
    try:
        flush_scope_recompositions()
    except Exception:
        logger.debug("settle: flush_scope_recompositions failed", exc_info=True)

    root = getattr(app, "root", None)
    if root is None:
        return
    try:
        root.layout(int(app.width), int(app.height))
        root.clear_needs_layout()
    except Exception:
        logger.debug("settle: layout pass failed", exc_info=True)

    # Request a real repaint so the on-screen frame reflects the action too.
    try:
        app.invalidate()
    except Exception:
        logger.debug("settle: invalidate failed", exc_info=True)


def click(
    app: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    button: Optional[int] = None,
) -> dict[str, Any]:
    """Synthesize a primary press+release at a resolved target.

    Provide a stable identifier (``key`` or ``label``) -- resolved to the center
    of its layout rect -- or raw ``x`` / ``y`` root coordinates as a fallback.

    Raises:
        ValueError: If neither an identifier nor explicit coordinates are given.
        TargetNotFoundError: If the identifier matched nothing (or it has no rect).
    """
    if key is not None or label is not None:
        node = find_target(app.root, key=key, label=label)
        if node is None:
            raise TargetNotFoundError(_no_match_message(key, label))
        px, py = _target_center(node)
        target_info: dict[str, Any] = _describe_target(node)
    elif x is not None and y is not None:
        px, py = float(x), float(y)
        target_info = {}
    else:
        raise ValueError("click requires a 'key', a 'label', or explicit 'x' and 'y'")

    ix, iy = int(round(px)), int(round(py))
    app._dispatch_mouse_press(ix, iy, button=button)
    app._dispatch_mouse_release(ix, iy, button=button)
    settle(app)
    return {"clicked": target_info, "x": ix, "y": iy}


def type_text(app: Any, text: str) -> dict[str, Any]:
    """Inject ``text`` into the currently focused widget.

    A widget must be focused first (e.g. ``click`` a text field); with nothing
    focused the app has nowhere to route the text and ``handled`` is ``False``.
    """
    handled = bool(app._dispatch_text(str(text)))
    settle(app)
    return {"typed": str(text), "handled": handled}


def press_key(app: Any, key: str, modifiers: Any = 0) -> dict[str, Any]:
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
