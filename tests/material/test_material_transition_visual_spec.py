from __future__ import annotations

from nuiitivet.material.transition_spec import MaterialTransitions
from nuiitivet.material.transition_visual_spec import resolve_material_transition_visual_spec
from nuiitivet.navigation.transition_spec import TransitionPhase, Transitions


def test_page_fade_enter_active_exit_visuals() -> None:
    spec = MaterialTransitions.page()

    enter_start = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ENTER, progress=0.0)
    enter_end = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ENTER, progress=1.0)
    active = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ACTIVE, progress=0.3)
    exit_start = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.EXIT, progress=0.0)
    exit_end = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.EXIT, progress=1.0)

    assert enter_start.content_opacity == 0.0
    assert enter_end.content_opacity == 1.0
    assert active.content_opacity == 1.0
    assert exit_start.content_opacity == 1.0
    assert exit_end.content_opacity == 0.0

    assert active.content_scale == (1.0, 1.0)
    assert active.content_translation == (0.0, 0.0)
    assert active.barrier_opacity is None


def test_page_fade_progress_is_clamped() -> None:
    spec = MaterialTransitions.page()

    below = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ENTER, progress=-1.0)
    above = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.EXIT, progress=2.0)

    assert below.content_opacity == 0.0
    assert above.content_opacity == 0.0


def test_dialog_fade_scale_visuals() -> None:
    spec = MaterialTransitions.dialog()

    enter_start = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ENTER, progress=0.0)
    enter_end = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ENTER, progress=1.0)
    active = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ACTIVE, progress=0.5)
    exit_start = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.EXIT, progress=0.0)
    exit_end = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.EXIT, progress=1.0)

    assert enter_start.content_opacity == 0.0
    assert enter_start.content_scale == (0.8, 0.8)
    assert enter_start.barrier_opacity == 0.0

    assert enter_end.content_opacity == 1.0
    assert enter_end.content_scale == (1.0, 1.0)
    assert enter_end.barrier_opacity == 1.0

    assert active.content_opacity == 1.0
    assert active.content_scale == (1.0, 1.0)
    assert active.barrier_opacity == 1.0

    assert exit_start.content_opacity == 1.0
    assert exit_start.content_scale == (1.0, 1.0)
    assert exit_start.barrier_opacity == 1.0

    # Exit is a plain fade-out; the scale only plays on the way in.
    assert exit_end.content_opacity == 0.0
    assert exit_end.content_scale == (1.0, 1.0)
    assert exit_end.barrier_opacity == 0.0


def test_overshoot_passes_through_to_spatial_patterns() -> None:
    """Progress above 1.0 (spatial settle) extrapolates scale/slide, while the
    fade and the scrim clamp."""
    spec = MaterialTransitions.dialog()

    below = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ENTER, progress=-10.0)
    settle = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ENTER, progress=1.05)

    assert below.content_opacity == 0.0
    assert below.content_scale == (0.8, 0.8)
    assert below.barrier_opacity == 0.0

    assert settle.content_opacity == 1.0
    assert settle.content_scale[0] > 1.0
    assert settle.barrier_opacity == 1.0

    sheet = MaterialTransitions.bottom_sheet()
    sheet_settle = resolve_material_transition_visual_spec(sheet, phase=TransitionPhase.ENTER, progress=1.05)
    assert sheet_settle.content_translation_fraction[1] < 0.0


def test_none_transition_is_noop_for_all_phases() -> None:
    spec = Transitions.empty()

    enter = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ENTER, progress=0.2)
    active = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.ACTIVE, progress=0.7)
    exit_visual = resolve_material_transition_visual_spec(spec, phase=TransitionPhase.EXIT, progress=0.9)

    for visual in (enter, active, exit_visual):
        assert visual.content_opacity == 1.0
        assert visual.content_scale == (1.0, 1.0)
        assert visual.content_translation == (0.0, 0.0)
        assert visual.barrier_opacity is None
