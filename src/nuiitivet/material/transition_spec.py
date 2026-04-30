"""Material transition spec tokens and presets."""

from __future__ import annotations

from dataclasses import dataclass

from typing import Literal

from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern, FractionalSlidePattern, ScalePattern, SlidePattern
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


def _default_side_sheet_enter(side: Literal["right", "left"] = "right") -> TransitionDefinition:
    # Default: right-side sheet slides in from right edge (1.0 = full width).
    # `side="left"` slides in from the left edge instead.
    sign = 1.0 if side == "right" else -1.0
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FractionalSlidePattern(start_x=sign, end_x=0.0),
    )


def _default_side_sheet_exit(side: Literal["right", "left"] = "right") -> TransitionDefinition:
    sign = 1.0 if side == "right" else -1.0
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FractionalSlidePattern(start_x=0.0, end_x=sign),
    )


def _default_bottom_sheet_enter() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FractionalSlidePattern(start_y=1.0, end_y=0.0),
    )


def _default_bottom_sheet_exit() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_EFFECTS,
        pattern=FractionalSlidePattern(start_y=0.0, end_y=1.0),
    )


@dataclass(frozen=True, slots=True)
class MaterialTransitionSpec:
    """Material transition token for overlay/page lifecycle.

    Carries `enter` / `exit_` `TransitionDefinition`s plus a `barrier_mode`
    that controls scrim opacity behavior:

    - ``"none"``  : no scrim (page, snackbar)
    - ``"fade"``  : scrim fades in/out following progress (dialog, sheets)
    """

    enter: TransitionDefinition
    exit_: TransitionDefinition
    barrier_mode: Literal["none", "fade"] = "none"


@dataclass(frozen=True, slots=True)
class _MaterialTransitionPresets:
    def page(
        self,
        enter: TransitionDefinition | None = None,
        exit_: TransitionDefinition | None = None,
    ) -> MaterialTransitionSpec:
        """Create a Material page transition token."""
        return MaterialTransitionSpec(
            enter=enter if enter is not None else _default_page_enter(),
            exit_=exit_ if exit_ is not None else _default_page_exit(),
            barrier_mode="none",
        )

    def dialog(
        self,
        enter: TransitionDefinition | None = None,
        exit_: TransitionDefinition | None = None,
    ) -> MaterialTransitionSpec:
        """Create a Material dialog transition token."""
        return MaterialTransitionSpec(
            enter=enter if enter is not None else _default_dialog_enter(),
            exit_=exit_ if exit_ is not None else _default_dialog_exit(),
            barrier_mode="fade",
        )

    def snackbar(
        self,
        enter: TransitionDefinition | None = None,
        exit_: TransitionDefinition | None = None,
    ) -> MaterialTransitionSpec:
        """Create a Material snackbar transition token."""
        return MaterialTransitionSpec(
            enter=enter if enter is not None else _default_snackbar_enter(),
            exit_=exit_ if exit_ is not None else _default_snackbar_exit(),
            barrier_mode="none",
        )

    def side_sheet(
        self,
        side: Literal["right", "left"] = "right",
        enter: TransitionDefinition | None = None,
        exit_: TransitionDefinition | None = None,
    ) -> MaterialTransitionSpec:
        """Create a Material side sheet transition token.

        Args:
            side: Which edge the sheet slides in from.
            enter: Custom enter transition definition.
            exit_: Custom exit transition definition.
        """
        return MaterialTransitionSpec(
            enter=enter if enter is not None else _default_side_sheet_enter(side),
            exit_=exit_ if exit_ is not None else _default_side_sheet_exit(side),
            barrier_mode="fade",
        )

    def bottom_sheet(
        self,
        enter: TransitionDefinition | None = None,
        exit_: TransitionDefinition | None = None,
    ) -> MaterialTransitionSpec:
        """Create a Material bottom sheet transition token.

        Args:
            enter: Custom enter transition definition.
            exit_: Custom exit transition definition.
        """
        return MaterialTransitionSpec(
            enter=enter if enter is not None else _default_bottom_sheet_enter(),
            exit_=exit_ if exit_ is not None else _default_bottom_sheet_exit(),
            barrier_mode="fade",
        )


MaterialTransitions = _MaterialTransitionPresets()


__all__ = [
    "MaterialTransitionSpec",
    "MaterialTransitions",
]
