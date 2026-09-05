"""Material transition spec tokens and presets."""

from __future__ import annotations

from dataclasses import dataclass

from typing import Literal

from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import FadePattern, FractionalSlidePattern, ScalePattern, SlidePattern
from nuiitivet.material.motion import (
    EXPRESSIVE_DEFAULT_SPATIAL,
    EXPRESSIVE_FAST_EFFECTS,
    EXPRESSIVE_FAST_SPATIAL,
    EXPRESSIVE_SLOW_EFFECTS,
)

# Overlay preset policy: entrances run on expressive spatial tokens (slide and
# scale carry the meaning; the slight overshoot is the settle). Exits run on
# the fast tokens — effects for pure fade-outs, spatial for slide-outs — so an
# exit is always shorter than its entrance. A definition has one motion, so a
# composed fade shares the spatial curve and clamps at full opacity while it
# settles — an accepted approximation.


# MD3 Shared Axis (X): a subtle fixed slide (not full-width) — the fade carries
# the meaning, the slide only signals direction. The fade windows sequence the
# two pages ("fade through") so they are never both half-opaque at once.
_SHARED_AXIS_X_SLIDE = 30.0
_FADE_THROUGH_THRESHOLD = 0.35


def _fade_out_through() -> FadePattern:
    """Outgoing fade for the first 35% of the transition, then held transparent."""
    return FadePattern(start_alpha=1.0, end_alpha=0.0, start_progress=0.0, end_progress=_FADE_THROUGH_THRESHOLD)


def _fade_in_through() -> FadePattern:
    """Incoming fade over the last 65% of the transition, held transparent before."""
    return FadePattern(start_alpha=0.0, end_alpha=1.0, start_progress=_FADE_THROUGH_THRESHOLD, end_progress=1.0)


def _default_page_enter() -> TransitionDefinition:
    """Forward (push) incoming page: slide in from the right while fading in."""
    return TransitionDefinition(
        motion=EXPRESSIVE_SLOW_EFFECTS,
        pattern=_fade_in_through() | SlidePattern(start_x=_SHARED_AXIS_X_SLIDE, end_x=0.0),
    )


def _default_page_exit() -> TransitionDefinition:
    """Forward (push) outgoing page: slide out to the left while fading out."""
    return TransitionDefinition(
        motion=EXPRESSIVE_SLOW_EFFECTS,
        pattern=_fade_out_through() | SlidePattern(start_x=0.0, end_x=-_SHARED_AXIS_X_SLIDE),
    )


def _default_page_enter_back() -> TransitionDefinition:
    """Backward (pop) returning page: slide in from the left while fading in."""
    return TransitionDefinition(
        motion=EXPRESSIVE_SLOW_EFFECTS,
        pattern=_fade_in_through() | SlidePattern(start_x=-_SHARED_AXIS_X_SLIDE, end_x=0.0),
    )


def _default_page_exit_back() -> TransitionDefinition:
    """Backward (pop) leaving page: slide out to the right while fading out."""
    return TransitionDefinition(
        motion=EXPRESSIVE_SLOW_EFFECTS,
        pattern=_fade_out_through() | SlidePattern(start_x=0.0, end_x=_SHARED_AXIS_X_SLIDE),
    )


def _default_dialog_enter() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_SPATIAL,
        pattern=FadePattern(start_alpha=0.0, end_alpha=1.0)
        | ScalePattern(start_scale_x=0.8, start_scale_y=0.8, end_scale_x=1.0, end_scale_y=1.0),
    )


def _default_dialog_exit() -> TransitionDefinition:
    # Plain fade-out: in MD3's fade pattern the scale only plays on the way in.
    return TransitionDefinition(
        motion=EXPRESSIVE_FAST_EFFECTS,
        pattern=FadePattern(start_alpha=1.0, end_alpha=0.0),
    )


def _default_snackbar_enter() -> TransitionDefinition:
    # Fast rather than default spatial: the snackbar is a small component.
    return TransitionDefinition(
        motion=EXPRESSIVE_FAST_SPATIAL,
        pattern=FadePattern(start_alpha=0.0, end_alpha=1.0)
        | SlidePattern(start_x=0.0, start_y=20.0, end_x=0.0, end_y=0.0),
    )


def _default_snackbar_exit() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_FAST_EFFECTS,
        pattern=FadePattern(start_alpha=1.0, end_alpha=0.0),
    )


def _default_side_sheet_enter(side: Literal["right", "left"] = "right") -> TransitionDefinition:
    # Default: right-side sheet slides in from right edge (1.0 = full width).
    # `side="left"` slides in from the left edge instead.
    sign = 1.0 if side == "right" else -1.0
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_SPATIAL,
        pattern=FractionalSlidePattern(start_x=sign, end_x=0.0),
    )


def _default_side_sheet_exit(side: Literal["right", "left"] = "right") -> TransitionDefinition:
    sign = 1.0 if side == "right" else -1.0
    return TransitionDefinition(
        motion=EXPRESSIVE_FAST_SPATIAL,
        pattern=FractionalSlidePattern(start_x=0.0, end_x=sign),
    )


def _default_bottom_sheet_enter() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_DEFAULT_SPATIAL,
        pattern=FractionalSlidePattern(start_y=1.0, end_y=0.0),
    )


def _default_bottom_sheet_exit() -> TransitionDefinition:
    return TransitionDefinition(
        motion=EXPRESSIVE_FAST_SPATIAL,
        pattern=FractionalSlidePattern(start_y=0.0, end_y=1.0),
    )


@dataclass(frozen=True, slots=True)
class MaterialTransitionSpec:
    """Material transition token for overlay/page lifecycle.

    Carries `enter` / `exit_` `TransitionDefinition`s plus a `barrier_mode`
    that controls scrim opacity behavior:

    - ``"none"``  : no scrim (page, snackbar)
    - ``"fade"``  : scrim fades in/out following progress (dialog, sheets)

    ``enter_back`` / ``exit_back`` are the backward-direction (pop) variants.
    Directional transitions such as Shared Axis (Z) reverse their motion when
    navigating back, so a pop must not merely replay the forward ``enter`` /
    ``exit_``. When either is ``None`` the resolver falls back to the forward
    definition, which keeps symmetric transitions (dialog, sheets, snackbar)
    unchanged.
    """

    enter: TransitionDefinition
    exit_: TransitionDefinition
    barrier_mode: Literal["none", "fade"] = "none"
    enter_back: TransitionDefinition | None = None
    exit_back: TransitionDefinition | None = None


@dataclass(frozen=True, slots=True)
class _MaterialTransitionPresets:
    def page(
        self,
        enter: TransitionDefinition | None = None,
        exit_: TransitionDefinition | None = None,
        enter_back: TransitionDefinition | None = None,
        exit_back: TransitionDefinition | None = None,
    ) -> MaterialTransitionSpec:
        """Create a Material page transition token.

        Defaults to the MD3 Shared Axis (Z) pattern: push moves the incoming
        page toward the viewer, and pop reverses that motion via the
        ``enter_back`` / ``exit_back`` variants.

        Args:
            enter: Forward (push) incoming definition.
            exit_: Forward (push) outgoing definition.
            enter_back: Backward (pop) returning definition. Falls back to the
                forward ``enter`` default when omitted alongside a custom
                ``enter`` override.
            exit_back: Backward (pop) leaving definition. Falls back to the
                forward ``exit_`` default when omitted alongside a custom
                ``exit_`` override.
        """
        # An explicit back override wins. Otherwise a custom forward override is
        # mirrored (symmetric pop), and only the untouched default gets the
        # reversed Shared Axis (X) motion.
        if enter_back is not None:
            resolved_enter_back = enter_back
        else:
            resolved_enter_back = enter if enter is not None else _default_page_enter_back()
        if exit_back is not None:
            resolved_exit_back = exit_back
        else:
            resolved_exit_back = exit_ if exit_ is not None else _default_page_exit_back()
        return MaterialTransitionSpec(
            enter=enter if enter is not None else _default_page_enter(),
            exit_=exit_ if exit_ is not None else _default_page_exit(),
            barrier_mode="none",
            enter_back=resolved_enter_back,
            exit_back=resolved_exit_back,
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
