"""Typed transition state holders for overlay routes."""

from __future__ import annotations

from nuiitivet.navigation.transition_state import TransitionState
from nuiitivet.navigation.transition_spec import TransitionPhase, TransitionSpec


class OverlayTransitionState(TransitionState):
    """Core transition state owned by an overlay route.

    This state is design-agnostic: it only tracks transition lifecycle
    (`phase`, `progress`) and the transition specification.
    """

    @classmethod
    def create(
        cls,
        transition_spec: TransitionSpec,
        *,
        initial_phase: TransitionPhase = TransitionPhase.ACTIVE,
        initial_progress: float = 1.0,
    ) -> "OverlayTransitionState":
        state = TransitionState.create(
            transition_spec,
            initial_phase=initial_phase,
            initial_progress=initial_progress,
        )
        return cls(
            transition_spec=state.transition_spec,
            phase_obs=state.phase_obs,
            progress_obs=state.progress_obs,
            lifecycle_obs=state.lifecycle_obs,
        )
