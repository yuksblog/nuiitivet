"""The bridge's action verbs: :mod:`nuiitivet._interaction.action` plus the overlay.

The verbs themselves are driver-agnostic and live in the shared core, outside
this dev-session-gated package. What is dev-only is the on-screen marker each one
draws, so every verb here is the core verb with
:data:`~nuiitivet.dev.action_observer.OVERLAY_OBSERVER` bound: a bridge-driven
action is visible to the human watching, and every other driver gets silence.

Everything that needs no binding -- ``settle``, ``check_condition``, the errors --
is re-exported as-is, and only what the bridge and its tests reach for:
:func:`~nuiitivet._interaction.action.settle`'s strict mode is a harness concern,
so its ``LayoutNotConvergedError`` is imported from the core by whoever wants it.
"""

from __future__ import annotations

from typing import Any, Optional

from nuiitivet._interaction import action as _action
from nuiitivet._interaction.action import (
    TargetNotFoundError,
    TargetNotVisibleError,
    check_condition,
    resolve_modifiers,
    settle,
)

from .action_observer import OVERLAY_OBSERVER

__all__ = [
    "TargetNotFoundError",
    "TargetNotVisibleError",
    "check_condition",
    "click",
    "press_key",
    "resolve_modifiers",
    "scroll",
    "scroll_into_view",
    "settle",
    "type_text",
]


def click(
    app: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    button: Optional[int] = None,
) -> dict[str, Any]:
    """Synthesize a press+release at a resolved target, and mark it on screen.

    See :func:`nuiitivet._interaction.action.click`.
    """
    return _action.click(
        app, key=key, label=label, x=x, y=y, button=button, on_action=OVERLAY_OBSERVER
    )


def scroll(
    app: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None,
    dx: float = 0.0,
    dy: float = 0.0,
) -> dict[str, Any]:
    """Synthesize a wheel event over a scroll region, and mark it on screen.

    See :func:`nuiitivet._interaction.action.scroll`.
    """
    return _action.scroll(
        app, key=key, label=label, x=x, y=y, dx=dx, dy=dy, on_action=OVERLAY_OBSERVER
    )


def scroll_into_view(
    app: Any,
    *,
    key: Optional[str] = None,
    label: Optional[str] = None,
    align: str = "nearest",
) -> dict[str, Any]:
    """Scroll the target's region(s) until it is reachable, and mark it on screen.

    See :func:`nuiitivet._interaction.action.scroll_into_view`.
    """
    return _action.scroll_into_view(
        app, key=key, label=label, align=align, on_action=OVERLAY_OBSERVER
    )


def type_text(app: Any, text: str) -> dict[str, Any]:
    """Inject ``text`` into the focused widget, and mark it on screen.

    See :func:`nuiitivet._interaction.action.type_text`.
    """
    return _action.type_text(app, text, on_action=OVERLAY_OBSERVER)


def press_key(app: Any, key: str, modifiers: Any = 0) -> dict[str, Any]:
    """Synthesize a key press+release, and mark it on screen.

    See :func:`nuiitivet._interaction.action.press_key`.
    """
    return _action.press_key(app, key, modifiers, on_action=OVERLAY_OBSERVER)
