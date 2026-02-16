"""Design-agnostic transition state primitive for navigation/overlay."""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.observable import Observable, ReadOnlyObservableProtocol, combine

from .transition_spec import TransitionPhase, TransitionSpec


@dataclass(slots=True)
class TransitionLifecycle:
    """Lifecycle facts for one transition tick.

    This model is design-agnostic and contains no visual policy.
    """

    phase: TransitionPhase
    progress: float


@dataclass(slots=True)
class TransitionState:
    """Core transition state.

    This state tracks transition lifecycle (`phase`, `progress`) and exposes
        a lifecycle-only observable.
    """

    transition_spec: TransitionSpec
    phase_obs: Observable[TransitionPhase]
    progress_obs: Observable[float]
    lifecycle_obs: ReadOnlyObservableProtocol[TransitionLifecycle]

    @classmethod
    def create(
        cls,
        transition_spec: TransitionSpec,
        *,
        initial_phase: TransitionPhase = TransitionPhase.ACTIVE,
        initial_progress: float = 1.0,
    ) -> "TransitionState":
        phase_obs: Observable[TransitionPhase] = Observable(initial_phase)
        progress_obs: Observable[float] = Observable(float(initial_progress))
        lifecycle_obs = combine(phase_obs, progress_obs).compute(
            lambda phase, progress: TransitionLifecycle(phase=phase, progress=float(progress))
        )
        return cls(
            transition_spec=transition_spec,
            phase_obs=phase_obs,
            progress_obs=progress_obs,
            lifecycle_obs=lifecycle_obs,
        )


__all__ = ["TransitionLifecycle", "TransitionState"]
