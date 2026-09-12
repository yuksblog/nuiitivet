"""Mechanics shared by the dev input layers.

Select mode, layout mode and the source jump all sit on the backend's real
input handlers and read the same things off them: whether the runner's
``Ctrl+Shift`` prefix is down, whether a press travelled far enough to be a
drag, which widget the pointer is over, and how to step a chosen widget up to
its parent and back. Each layer keeps its own meaning for those answers; the
answers themselves live here so the three agree by construction.
"""

from __future__ import annotations

import logging
import weakref
from typing import Any, Callable, Optional

from nuiitivet._interaction.perception import ancestors, pick_at
from nuiitivet.input.codes import MOD_CTRL, MOD_META, MOD_SHIFT, resolve_modifiers

logger = logging.getLogger(__name__)

#: Pointer travel, in logical pixels, below which a press/release pair is a
#: click rather than a drag. Discriminating on *release* is what lets one
#: gesture serve both: the press handler never has to commit to a reading it
#: cannot yet make.
DRAG_THRESHOLD = 4.0


def travelled(press: tuple[float, float], x: float, y: float) -> bool:
    """Whether the pointer moved from ``press`` by more than :data:`DRAG_THRESHOLD`."""
    return abs(float(x) - press[0]) > DRAG_THRESHOLD or abs(float(y) - press[1]) > DRAG_THRESHOLD


def accel_held(modifier_keys: int) -> bool:
    """Whether the platform accelerator is down: Ctrl, or Cmd on macOS."""
    return bool(resolve_modifiers(int(modifier_keys)) & (MOD_CTRL | MOD_META))


def chord_held(modifier_keys: int) -> bool:
    """Whether the dev runner's prefix, ``Ctrl+Shift`` (``Cmd+Shift``), is down."""
    physical = resolve_modifiers(int(modifier_keys))
    return bool(physical & (MOD_CTRL | MOD_META)) and bool(physical & MOD_SHIFT)


def pick(app: Any, x: float, y: float) -> Optional[Any]:
    """The widget a human pointing at ``(x, y)`` in ``app``'s window means, or ``None``."""
    root = getattr(app, "root", None)
    if root is None:
        return None
    try:
        return pick_at(root, float(x), float(y))
    except Exception:
        logger.debug("dev input: pick_at failed", exc_info=True)
        return None


def parent_of(node: Any) -> Optional[Any]:
    """``node``'s parent, or ``None`` at the root."""
    chain = ancestors(node)
    return chain[0] if chain else None


def child_toward(current: Any, anchor: Any) -> Optional[Any]:
    """The child of ``current`` on the path down to ``anchor``, or ``None``.

    ``down`` is only meaningful as the inverse of ``up``: a node has many
    children and no way to guess which the human meant, but exactly one lies
    on the path back to where the walk started.
    """
    if current is None or anchor is None or anchor is current:
        return None
    previous = anchor
    for node in ancestors(anchor):
        if node is current:
            return previous
        previous = node
    return None


def invalidate(app: Any) -> None:
    """Ask for a frame, so an overlay reflects the change that just happened."""
    try:
        app.invalidate()
    except Exception:
        logger.debug("dev input: invalidate failed", exc_info=True)


def weak(obj: Any) -> Optional[Callable[[], Any]]:
    """A weak reference to ``obj``, or ``None`` for ``None`` and the unreferenceable."""
    if obj is None:
        return None
    try:
        return weakref.ref(obj)
    except TypeError:
        return None


__all__ = [
    "DRAG_THRESHOLD",
    "accel_held",
    "child_toward",
    "chord_held",
    "invalidate",
    "parent_of",
    "pick",
    "travelled",
    "weak",
]
