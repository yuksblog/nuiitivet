"""Transition kernel shared by Navigator and Overlay.

A presented element enters, stays and exits: the stack runtime tracks that
lifecycle, the engine drives the progress, and the spec says how it moves.
Navigator and Overlay are two applications of this kernel; neither depends on
the other.
"""

from nuiitivet.transition.engine import TransitionEngine, TransitionMotionPreset, TransitionMotions
from nuiitivet.transition.spec import (
    EmptyTransitionSpec,
    TransitionPhase,
    TransitionSpec,
    Transitions,
)
from nuiitivet.transition.stack import EntryLifecycle, StackEntry, StackRuntime
from nuiitivet.transition.state import TransitionLifecycle, TransitionState

__all__ = [
    "EmptyTransitionSpec",
    "EntryLifecycle",
    "StackEntry",
    "StackRuntime",
    "TransitionEngine",
    "TransitionLifecycle",
    "TransitionMotionPreset",
    "TransitionMotions",
    "TransitionPhase",
    "TransitionSpec",
    "TransitionState",
    "Transitions",
]
