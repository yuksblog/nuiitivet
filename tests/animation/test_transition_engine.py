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


def test_transition_engine_does_not_complete_on_overshoot_crossing() -> None:
    """An overshooting motion crosses the target mid-flight and settles back.

    Completion must require the exact target value (emitted when the motion
    reports done), not epsilon proximity — a crossing sample landing inside a
    proximity band would end the transition before the settle plays out.
    """
    engine = TransitionEngine()
    completed: list[bool] = []

    engine.start(start=0.0, target=1.0, apply=lambda _v: None, on_complete=lambda: completed.append(True))

    engine._on_value(0.99995)  # within the old epsilon band, mid-flight
    assert completed == []
    engine._on_value(1.0139)  # overshoot peak
    assert completed == []
    engine._on_value(1.0)  # exact arrival emitted on motion done
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
