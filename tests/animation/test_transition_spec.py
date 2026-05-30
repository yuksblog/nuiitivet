from __future__ import annotations

from nuiitivet.navigation.transition_spec import (
    EmptyTransitionSpec,
    TransitionPhase,
    Transitions,
)


def test_transition_phase_values_are_stable() -> None:
    assert TransitionPhase.ENTER.value == "enter"
    assert TransitionPhase.ACTIVE.value == "active"
    assert TransitionPhase.EXIT.value == "exit"


def test_transition_presets_return_core_lifecycle_tokens() -> None:
    empty_spec = Transitions.empty()
    assert isinstance(empty_spec, EmptyTransitionSpec)


def test_transition_presets_create_distinct_instances() -> None:
    assert Transitions.empty() is not Transitions.empty()
