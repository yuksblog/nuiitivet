from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class TransitionPhase(str, Enum):
    """Lifecycle phase for route transition rendering."""

    ENTER = "enter"
    ACTIVE = "active"
    EXIT = "exit"


class TransitionSpec(Protocol):
    """Declarative transition contract.

    Core transition specs intentionally carry no visual policy.
    Visual parameter resolution belongs to design implementations.
    """

    # Marker protocol. Concrete specs are opaque lifecycle tokens.


@dataclass(frozen=True, slots=True)
class EmptyTransitionSpec:
    """Empty lifecycle transition token.

    Core owns no visual transition policy. Design layers may map this token
    to "no transition" or any design-specific baseline behavior.
    """


@dataclass(frozen=True, slots=True)
class _TransitionPresets:
    def empty(self) -> TransitionSpec:
        """Create an empty core transition token."""
        return EmptyTransitionSpec()


Transitions = _TransitionPresets()


__all__ = [
    "EmptyTransitionSpec",
    "TransitionPhase",
    "TransitionSpec",
    "Transitions",
]
