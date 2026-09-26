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


def resolve_phase_motion(spec: TransitionSpec, phase: TransitionPhase, *, back: bool = False) -> object | None:
    """Duck-typed lookup of the ``motion`` a spec declares for one phase.

    The exit definition is stored under ``exit_`` (``exit`` is a builtin), so a
    bare ``getattr(spec, phase.value)`` would miss it and silently fall back to
    the engine's default motion. With ``back=True`` the backward-direction
    variant (``enter_back`` / ``exit_back``) is preferred, falling back to the
    forward definition — mirroring how the visual resolver picks patterns.
    """
    attr = _TRANSITION_PHASE_ATTR.get(phase)
    if attr is None:
        return None
    try:
        definition = None
        if back:
            definition = getattr(spec, _TRANSITION_PHASE_BACK_ATTR[phase], None)
        if definition is None:
            definition = getattr(spec, attr, None)
        if definition is None:
            return None
        return getattr(definition, "motion", None)
    except Exception:
        return None


_TRANSITION_PHASE_ATTR: dict[TransitionPhase, str] = {
    TransitionPhase.ENTER: "enter",
    TransitionPhase.EXIT: "exit_",
}

_TRANSITION_PHASE_BACK_ATTR: dict[TransitionPhase, str] = {
    TransitionPhase.ENTER: "enter_back",
    TransitionPhase.EXIT: "exit_back",
}


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
    "resolve_phase_motion",
]
