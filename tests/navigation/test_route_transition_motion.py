"""Regression tests for route transition motion resolution and per-frame repaint.

Two defects are pinned:

- Defect 1: ``pop`` fell back to the engine's 0.6 s default because the exit
  motion was resolved via ``getattr(spec, phase.value)`` — ``"exit"`` misses the
  ``exit_`` field, so ``_get_motion`` returned ``None``.
- Defect 2: the transition ``apply`` callback only mutated ``progress`` without
  requesting a frame, so the screen repainted only at the transition endpoints.
"""

from __future__ import annotations

from nuiitivet.material.transition_spec import MaterialTransitions
from nuiitivet.navigation import Navigator, Route
from nuiitivet.navigation.transition_spec import TransitionPhase
from nuiitivet.widgeting.widget import Widget


class _Screen(Widget):
    def build(self) -> Widget:
        return self


def _material_route() -> Route:
    return Route(builder=_Screen, transition_spec=MaterialTransitions.page())


def test_exit_motion_matches_enter_motion() -> None:
    """Defect 1: exit phase must resolve the Material motion, not fall back to None."""
    nav = Navigator.routes([Route(builder=_Screen)])
    route = _material_route()

    enter_motion = nav._get_motion(route, TransitionPhase.ENTER)  # type: ignore[attr-defined]
    exit_motion = nav._get_motion(route, TransitionPhase.EXIT)  # type: ignore[attr-defined]

    assert enter_motion is not None
    assert exit_motion is not None, "exit motion must resolve (regression: fell back to None → 0.6 s default)"
    assert exit_motion.duration == enter_motion.duration


def test_transition_progress_repaints_each_frame() -> None:
    """Defect 2: advancing progress must request a repaint every frame."""
    nav = Navigator.routes([Route(builder=_Screen)])

    invalidate_calls = 0
    original_invalidate = nav.invalidate

    def _counting_invalidate(immediate: bool = False) -> None:
        nonlocal invalidate_calls
        invalidate_calls += 1
        original_invalidate(immediate)

    nav.invalidate = _counting_invalidate  # type: ignore[method-assign]

    class _T:
        progress = 0.0

    transition = _T()
    nav._transition = transition  # type: ignore[attr-defined,assignment]

    samples = [0.8, 0.6, 0.4, 0.2, 0.0]
    for value in samples:
        nav._on_transition_progress(value)  # type: ignore[attr-defined]

    assert transition.progress == samples[-1]
    assert invalidate_calls == len(samples)


def test_transition_progress_noop_without_transition() -> None:
    """No active transition: the callback must not repaint or raise."""
    nav = Navigator.routes([Route(builder=_Screen)])
    nav._transition = None  # type: ignore[attr-defined]

    invalidate_calls = 0
    original_invalidate = nav.invalidate

    def _counting_invalidate(immediate: bool = False) -> None:
        nonlocal invalidate_calls
        invalidate_calls += 1
        original_invalidate(immediate)

    nav.invalidate = _counting_invalidate  # type: ignore[method-assign]

    nav._on_transition_progress(0.5)  # type: ignore[attr-defined]

    assert invalidate_calls == 0
