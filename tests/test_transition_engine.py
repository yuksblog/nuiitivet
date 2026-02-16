from __future__ import annotations

from nuiitivet.navigation.transition_engine import TransitionEngine, TransitionMotions


def test_transition_engine_immediate_completion_calls_apply_and_on_complete() -> None:
    engine = TransitionEngine()
    values: list[float] = []
    completed: list[bool] = []

    handle = engine.start(
        start=0.0,
        target=0.0,
        apply=lambda v: values.append(v),
        on_complete=lambda: completed.append(True),
    )

    assert handle.is_running is False
    assert values == [0.0]
    assert completed == [True]

    engine.dispose()


def test_transition_engine_stale_handle_cancel_does_not_break_latest_animation() -> None:
    engine = TransitionEngine()

    first = engine.start(start=0.0, target=1.0, apply=lambda _v: None)
    assert first.is_running is True

    second = engine.start(start=1.0, target=1.0, apply=lambda _v: None)
    assert second.is_running is False

    # Stale handle cancel should be ignored.
    first.cancel()

    engine.dispose()


def test_transition_motion_defaults_are_centralized() -> None:
    preset = TransitionMotions.navigation_default()
    assert preset.duration_sec == 0.6
