"""visible() modifier - conditional widget presence with optional animation.

Toggles a widget's *presence* in the layout tree based on a bool or
``Observable[bool]``. When hidden, the widget contributes zero layout size and
no input events ("gone" semantics). When shown again, the widget is freshly
mounted (lazy mount).

An optional ``transition`` parameter accepts a ``TransitionDefinition`` (a
``Motion`` + ``TransitionPattern``) and animates enter/exit using the existing
animation infrastructure. During the exit animation, the widget continues to be
laid out and painted with the animation's interpolated visuals applied, but
input is blocked from the moment the condition flips to ``False``.

Usage::

    widget.modifier(visible(self.vm.is_open))

    widget.modifier(
        visible(
            self.vm.is_open,
            transition=TransitionDefinition(
                motion=LinearMotion(0.2),
                pattern=FadePattern(start_alpha=0.0, end_alpha=1.0),
            ),
        )
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Tuple, Union

from nuiitivet.animation.animatable import Animatable
from nuiitivet.animation.transition_definition import TransitionDefinition
from nuiitivet.animation.transition_pattern import TransitionVisuals
from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import ReadOnlyObservableProtocol
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.observable.protocols import Disposable


logger = logging.getLogger(__name__)


VisibleConditionLike = Union[bool, ReadOnlyObservableProtocol[bool]]


_HIDDEN_SIZING = Sizing.fixed(0)


class VisibleBox(Widget):
    """Wrapper widget that toggles the presence of a child based on a condition.

    The child is *lazy-mounted*: when the initial condition is ``False`` the
    child is not added to the tree at all. It is mounted on the first
    transition to ``True`` and unmounted again after exit (or immediately when
    no transition is provided).
    """

    def __init__(
        self,
        child: Widget,
        condition: VisibleConditionLike,
        *,
        transition: Optional[TransitionDefinition] = None,
    ) -> None:
        # Inherit sizing from the child so layout matches when visible.
        super().__init__(
            width=child.width_sizing,
            height=child.height_sizing,
            max_children=1,
            overflow_policy="replace_last",
        )
        self._child_widget: Widget = child
        self._condition: VisibleConditionLike = condition
        self._transition: Optional[TransitionDefinition] = transition

        # User-facing logical visibility (drives input).
        self._logical_visible: bool = self._read_initial_condition(condition)
        # Whether the child is currently mounted in the tree.
        self._physical_present: bool = False
        # Saved sizing to restore when becoming visible.
        self._user_width_sizing: Sizing = self.width_sizing
        self._user_height_sizing: Sizing = self.height_sizing

        # Animation state (only used when transition is provided).
        self._animatable: Optional[Animatable[float]] = None
        self._animatable_subscription: Optional["Disposable"] = None
        self._progress: float = 1.0 if self._logical_visible else 0.0

        if self._logical_visible:
            self._mount_child()
            self._progress = 1.0
        else:
            self._apply_hidden_sizing()

    # ------------------------------------------------------------------
    # Sizing helpers
    # ------------------------------------------------------------------

    def _apply_hidden_sizing(self) -> None:
        self.width_sizing = _HIDDEN_SIZING
        self.height_sizing = _HIDDEN_SIZING

    def _apply_visible_sizing(self) -> None:
        self.width_sizing = self._user_width_sizing
        self.height_sizing = self._user_height_sizing

    # ------------------------------------------------------------------
    # Initial condition / observation
    # ------------------------------------------------------------------

    @staticmethod
    def _read_initial_condition(condition: VisibleConditionLike) -> bool:
        if isinstance(condition, ReadOnlyObservableProtocol):
            try:
                return bool(condition.value)
            except Exception:
                exception_once(
                    logger,
                    "visible_box_initial_condition_exc",
                    "Failed to read initial condition observable",
                )
                return False
        return bool(condition)

    def on_mount(self) -> None:
        super().on_mount()
        # Re-apply sizing to match current state once we have an app reference.
        if self._physical_present:
            self._apply_visible_sizing()
        else:
            self._apply_hidden_sizing()

        if isinstance(self._condition, ReadOnlyObservableProtocol):
            self.observe(self._condition, self._on_condition_changed)

    def on_unmount(self) -> None:
        self._stop_animation_subscription()
        super().on_unmount()

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _on_condition_changed(self, value: bool) -> None:
        next_visible = bool(value)
        if next_visible == self._logical_visible:
            return
        self._logical_visible = next_visible
        if next_visible:
            self._handle_show()
        else:
            self._handle_hide()

    def _handle_show(self) -> None:
        # Always lazy-mount before animating.
        if not self._physical_present:
            self._mount_child()

        if self._transition is None:
            self._progress = 1.0
            self._stop_animation_subscription()
            self.invalidate()
            return

        animatable = self._ensure_animatable()
        animatable.target = 1.0
        self.invalidate()

    def _handle_hide(self) -> None:
        if not self._physical_present:
            # Already hidden; nothing to do.
            return

        if self._transition is None:
            self._unmount_child()
            self._progress = 0.0
            self.invalidate()
            return

        animatable = self._ensure_animatable()
        animatable.target = 0.0
        self.invalidate()

    # ------------------------------------------------------------------
    # Child mount / unmount
    # ------------------------------------------------------------------

    def _mount_child(self) -> None:
        if self._physical_present:
            return
        self._apply_visible_sizing()
        self.add_child(self._child_widget)
        self._physical_present = True
        self.mark_needs_layout()
        self.invalidate()

    def _unmount_child(self) -> None:
        if not self._physical_present:
            return
        try:
            self.remove_child(self._child_widget)
        except Exception:
            exception_once(
                logger,
                "visible_box_remove_child_exc",
                "VisibleBox failed to remove child during hide",
            )
        self._physical_present = False
        self._apply_hidden_sizing()
        self.mark_needs_layout()
        self.invalidate()

    # ------------------------------------------------------------------
    # Animation driver
    # ------------------------------------------------------------------

    def _ensure_animatable(self) -> Animatable[float]:
        if self._animatable is not None:
            return self._animatable

        assert self._transition is not None
        initial = self._progress
        animatable: Animatable[float] = Animatable(initial, motion=self._transition.motion)
        self._animatable = animatable

        def _on_progress(value: float) -> None:
            self._progress = float(value)
            self.invalidate()
            # Detect exit completion: hidden requested and animation reached 0.
            if not self._logical_visible and self._progress <= 0.0 and self._physical_present:
                self._unmount_child()

        sub = animatable.subscribe(_on_progress)
        self._animatable_subscription = sub
        return animatable

    def _stop_animation_subscription(self) -> None:
        sub = self._animatable_subscription
        if sub is None:
            return
        try:
            dispose = getattr(sub, "dispose", None)
            if callable(dispose):
                dispose()
        except Exception:
            exception_once(
                logger,
                "visible_box_animation_unsubscribe_exc",
                "VisibleBox failed to dispose animation subscription",
            )
        self._animatable_subscription = None

    # ------------------------------------------------------------------
    # Visuals from transition pattern
    # ------------------------------------------------------------------

    def _resolve_transition_visuals(self) -> Optional[TransitionVisuals]:
        if self._transition is None:
            return None
        try:
            return self._transition.pattern.resolve(self._progress)
        except Exception:
            exception_once(
                logger,
                "visible_box_resolve_visuals_exc",
                "TransitionPattern.resolve raised in VisibleBox",
            )
            return None

    # ------------------------------------------------------------------
    # Widget overrides
    # ------------------------------------------------------------------

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        if not self._physical_present:
            return (0, 0)
        try:
            return self._child_widget.preferred_size(max_width=max_width, max_height=max_height)
        except Exception:
            exception_once(
                logger,
                "visible_box_preferred_size_exc",
                "Child preferred_size raised in VisibleBox",
            )
            return (0, 0)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        if not self._physical_present:
            return
        try:
            self._child_widget.layout(width, height)
            self._child_widget.set_layout_rect(0, 0, width, height)
        except Exception:
            exception_once(
                logger,
                "visible_box_layout_exc",
                "Child layout raised in VisibleBox",
            )

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        if not self._physical_present:
            return

        visuals = self._resolve_transition_visuals()
        if visuals is None or canvas is None or not _has_visual_effect(visuals):
            try:
                self._child_widget.set_last_rect(x, y, width, height)
                self._child_widget.paint(canvas, x, y, width, height)
            except Exception:
                exception_once(
                    logger,
                    "visible_box_paint_no_visuals_exc",
                    "Child paint raised in VisibleBox",
                )
            return

        # Apply transition visuals (opacity + transforms) around child paint.
        opacity = _clamp_unit(visuals.opacity) if visuals.opacity is not None else 1.0
        scale_x = visuals.scale_x if visuals.scale_x is not None else 1.0
        scale_y = visuals.scale_y if visuals.scale_y is not None else 1.0
        translate_x = visuals.translate_x if visuals.translate_x is not None else 0.0
        translate_y = visuals.translate_y if visuals.translate_y is not None else 0.0
        if visuals.translate_x_fraction is not None:
            translate_x += visuals.translate_x_fraction * float(width)
        if visuals.translate_y_fraction is not None:
            translate_y += visuals.translate_y_fraction * float(height)

        needs_opacity = opacity < 1.0
        try:
            canvas.save()
            if needs_opacity:
                try:
                    from nuiitivet.rendering.skia.color import make_opacity_paint

                    layer_paint = make_opacity_paint(opacity)
                    if layer_paint is not None:
                        canvas.saveLayer(None, layer_paint)
                except Exception:
                    exception_once(
                        logger,
                        "visible_box_opacity_layer_exc",
                        "VisibleBox failed to apply opacity layer",
                    )

            if translate_x != 0.0 or translate_y != 0.0:
                canvas.translate(translate_x, translate_y)
            if scale_x != 1.0 or scale_y != 1.0:
                cx = float(x) + float(width) / 2.0
                cy = float(y) + float(height) / 2.0
                canvas.translate(cx, cy)
                canvas.scale(scale_x, scale_y)
                canvas.translate(-cx, -cy)

            self._child_widget.set_last_rect(x, y, width, height)
            self._child_widget.paint(canvas, x, y, width, height)
        except Exception:
            exception_once(
                logger,
                "visible_box_paint_exc",
                "VisibleBox paint raised",
            )
        finally:
            try:
                if needs_opacity:
                    canvas.restore()  # opacity layer
                canvas.restore()  # geometric transforms
            except Exception:
                exception_once(
                    logger,
                    "visible_box_restore_exc",
                    "VisibleBox canvas.restore failed",
                )

    def hit_test(self, x: int, y: int):
        # Block all input the moment the condition flips to False, even while
        # an exit animation is still playing.
        if not self._logical_visible or not self._physical_present:
            return None
        try:
            hit = self._child_widget.hit_test(x, y)
            if hit is not None:
                return hit
        except Exception:
            exception_once(
                logger,
                "visible_box_hit_test_exc",
                "Child hit_test raised in VisibleBox",
            )
        return super().hit_test(x, y)


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _has_visual_effect(visuals: TransitionVisuals) -> bool:
    return any(
        v is not None
        for v in (
            visuals.opacity,
            visuals.scale_x,
            visuals.scale_y,
            visuals.translate_x,
            visuals.translate_y,
            visuals.translate_x_fraction,
            visuals.translate_y_fraction,
        )
    )


@dataclass(slots=True)
class VisibleModifier(ModifierElement):
    """Modifier that conditionally shows/hides a widget with optional animation."""

    condition: VisibleConditionLike
    transition: Optional[TransitionDefinition] = None

    def apply(self, widget: Widget) -> Widget:
        return VisibleBox(widget, self.condition, transition=self.transition)


def visible(
    condition: VisibleConditionLike,
    *,
    transition: Optional[TransitionDefinition] = None,
) -> VisibleModifier:
    """Toggle a widget's presence in the layout tree.

    When *condition* is ``False`` the widget is removed from layout (zero
    width/height) and no longer receives input events. When ``True`` the
    widget is mounted and laid out normally.

    Args:
        condition: Static ``bool`` or an ``Observable[bool]`` driving visibility.
        transition: Optional :class:`TransitionDefinition` that animates enter
            and exit. When omitted, mount/unmount happens immediately.

    Returns:
        A :class:`VisibleModifier` to apply via ``widget.modifier(...)``.

    Note:
        Visibility uses *lazy mount*: when *condition* starts ``False`` the
        child is not built until the first transition to ``True``. Subsequent
        hides will fully unmount the child, so widget-local state is not
        preserved across hide/show cycles. For "invisible but interactive"
        behavior, use :func:`opacity` ``(0.0)`` instead.
    """
    return VisibleModifier(condition=condition, transition=transition)


__all__ = [
    "VisibleBox",
    "VisibleModifier",
    "visible",
]
