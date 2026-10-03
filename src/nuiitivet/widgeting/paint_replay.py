"""Declaring that a widget's paint may be replayed from a recording."""

from __future__ import annotations

from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable[..., object])

#: The methods that draw a widget. A widget is replayed only when the function
#: each of these names resolves to on its class is declared with ``replay_safe``.
REPLAY_HOOKS = (
    "paint",
    "draw_background",
    "draw_children",
    "draw_border",
    "draw_state_layer",
    "draw_focus_indicator",
)


def replay_safe(method: F) -> F:
    """Declare that skipping this method on a frame where nothing changed is safe.

    Two things must hold. The method keeps nothing that later code reads: a
    position stored for pointer handling would stay where the last recording
    left it. And every change to what it draws calls ``invalidate()`` on the
    widget or on something below it.

    The declaration belongs to the function, so a subclass that overrides the
    method is undeclared until it declares its own.
    """
    setattr(method, "_replay_safe", True)
    return method


__all__ = ["REPLAY_HOOKS", "replay_safe"]
