from __future__ import annotations

from nuiitivet.navigation.transition_state import TransitionState
from nuiitivet.navigation.transition_spec import TransitionPhase, Transitions


def test_transition_state_create_builds_lifecycle_observable() -> None:
    spec = Transitions.empty()
    state = TransitionState.create(spec, initial_phase=TransitionPhase.ENTER, initial_progress=0.25)

    assert state.transition_spec is spec
    assert state.phase_obs.value is TransitionPhase.ENTER
    assert abs(state.progress_obs.value - 0.25) < 1e-9
    assert state.lifecycle_obs.value.phase is TransitionPhase.ENTER
    assert abs(state.lifecycle_obs.value.progress - 0.25) < 1e-9


def test_transition_state_lifecycle_updates_with_phase_and_progress() -> None:
    spec = Transitions.empty()
    state = TransitionState.create(spec)

    state.phase_obs.value = TransitionPhase.EXIT
    state.progress_obs.value = 1.0

    lifecycle = state.lifecycle_obs.value
    assert lifecycle.phase is TransitionPhase.EXIT
    assert lifecycle.progress == 1.0
