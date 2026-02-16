"""Material transition spec tokens and presets."""

from __future__ import annotations

from dataclasses import dataclass, field

from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern, ScalePattern, SlidePattern
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS


def _default_page_enter() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=0.0, end_alpha=1.0),
    )


def _default_page_exit() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=1.0, end_alpha=0.0),
    )


def _default_dialog_enter() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=0.0, end_alpha=1.0)
        | ScalePattern(start_scale_x=0.92, start_scale_y=0.92, end_scale_x=1.0, end_scale_y=1.0),
    )


def _default_dialog_exit() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=1.0, end_alpha=0.0)
        | ScalePattern(start_scale_x=1.0, start_scale_y=1.0, end_scale_x=0.96, end_scale_y=0.96),
    )


def _default_snackbar_enter() -> TransitionDefinition:
    # Emphasized easing for entrance
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=0.0, end_alpha=1.0)
        | SlidePattern(start_x=0.0, start_y=20.0, end_x=0.0, end_y=0.0),
    )


def _default_snackbar_exit() -> TransitionDefinition:
    # Emphasized easing for exit (faster)
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FadePattern(start_alpha=1.0, end_alpha=0.0),
    )


@dataclass(frozen=True, slots=True)
class MaterialPageTransitionSpec:
    """Material default transition token for page navigation."""

    enter: TransitionDefinition = field(default_factory=_default_page_enter)
    exit: TransitionDefinition = field(default_factory=_default_page_exit)


@dataclass(frozen=True, slots=True)
class MaterialDialogTransitionSpec:
    """Material default transition token for dialog overlays."""

    enter: TransitionDefinition = field(default_factory=_default_dialog_enter)
    exit: TransitionDefinition = field(default_factory=_default_dialog_exit)


@dataclass(frozen=True, slots=True)
class MaterialSnackbarTransitionSpec:
    """Material default transition token for snackbars."""

    enter: TransitionDefinition = field(default_factory=_default_snackbar_enter)
    exit: TransitionDefinition = field(default_factory=_default_snackbar_exit)


@dataclass(frozen=True, slots=True)
class _MaterialTransitionPresets:
    def page(
        self,
        enter: TransitionDefinition | None = None,
        exit: TransitionDefinition | None = None,
    ) -> MaterialPageTransitionSpec:
        """Create a Material page transition token."""
        return MaterialPageTransitionSpec(
            enter=enter or _default_page_enter(),
            exit=exit or _default_page_exit(),
        )

    def dialog(
        self,
        enter: TransitionDefinition | None = None,
        exit: TransitionDefinition | None = None,
    ) -> MaterialDialogTransitionSpec:
        """Create a Material dialog transition token."""
        return MaterialDialogTransitionSpec(
            enter=enter or _default_dialog_enter(),
            exit=exit or _default_dialog_exit(),
        )

    def snackbar(
        self,
        enter: TransitionDefinition | None = None,
        exit: TransitionDefinition | None = None,
    ) -> MaterialSnackbarTransitionSpec:
        """Create a Material snackbar transition token."""
        return MaterialSnackbarTransitionSpec(
            enter=enter or _default_snackbar_enter(),
            exit=exit or _default_snackbar_exit(),
        )


MaterialTransitions = _MaterialTransitionPresets()


__all__ = [
    "MaterialDialogTransitionSpec",
    "MaterialPageTransitionSpec",
    "MaterialSnackbarTransitionSpec",
    "MaterialTransitions",
]
