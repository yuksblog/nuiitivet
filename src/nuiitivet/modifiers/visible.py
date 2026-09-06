"""visible() modifier - conditional widget visibility with optional animation.

``visible()`` is a *thin composition* over three paint-time / input primitives:

* :func:`opacity` — drives the visual fade between hidden (``0.0``) and shown
  (``1.0``).
* :func:`passthrough_pointer` — lets clicks pass through while the widget is
  logically hidden so that invisible widgets do not consume input.
* :func:`block_focus_traversal` — takes the hidden subtree out of the Tab
  sequence so that keyboard focus cannot land on what nobody can see.

The wrapped widget continues to occupy its normal layout space while hidden;
``visible()`` no longer collapses layout to zero size. Use a layout-aware
Widget for animated layout-size changes.

When *condition* is a static ``bool`` or an ``Observable[bool]`` and no
*transition* is provided, ``visible()`` collapses to ``opacity(...) |
block_focus_traversal(...) | passthrough_pointer(...)`` exactly. With a *transition*
provided, an internal
animation driver wires the ``opacity`` (and any pattern-driven ``scale`` /
``translate``) to an :class:`Animatable` retargeted on each condition change.

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
from nuiitivet.observable import ObservableBase
from nuiitivet.observable.computed import ComputedObservable
from nuiitivet.rendering.visual_bounds import transformed_outsets
from nuiitivet.widgeting.modifier import Modifier, ModifierElement
from nuiitivet.widgeting.widget import Widget

from .block_focus_traversal import BlockFocusTraversalBox, block_focus_traversal
from .passthrough_pointer import PassthroughPointerBox, passthrough_pointer
from .transform import opacity

if TYPE_CHECKING:
    from nuiitivet.observable.protocols import Disposable


logger = logging.getLogger(__name__)


VisibleConditionLike = Union[bool, ObservableBase[bool]]


def _read_initial_condition(condition: VisibleConditionLike) -> bool:
    if isinstance(condition, ObservableBase):
        try:
            return bool(condition.value)
        except Exception:
            exception_once(
                logger,
                "visible_initial_condition_exc",
                "Failed to read visible() initial condition observable",
            )
            return False
    return bool(condition)


class _AnimatedVisibleBox(Widget):
    """Single-child paint wrapper that animates pattern visuals on visibility change.

    The child is always mounted and occupies its natural layout space. Visuals
    (opacity / scale / translate, and translate-as-fraction-of-size) are
    derived from the supplied :class:`TransitionDefinition` and applied at
    paint time. Hit-test blocking while hidden is the responsibility of an
    outer ``passthrough_pointer`` wrapper applied by :class:`_AnimatedVisibleModifier`.
    """

    def __init__(
        self,
        child: Widget,
        condition: VisibleConditionLike,
        transition: TransitionDefinition,
        transition_out: Optional[TransitionDefinition] = None,
    ) -> None:
        super().__init__(
            width=child.width_sizing,
            height=child.height_sizing,
            max_children=1,
            overflow_policy="replace_last",
        )
        self._condition: VisibleConditionLike = condition
        self._transition_in: TransitionDefinition = transition
        self._transition_out: TransitionDefinition = transition_out if transition_out is not None else transition
        self._logical_visible: bool = _read_initial_condition(condition)
        self._active_transition: TransitionDefinition = (
            self._transition_in if self._logical_visible else self._transition_out
        )
        self._progress: float = 1.0 if self._logical_visible else 0.0
        self._animatable: Optional[Animatable[float]] = None
        self._animatable_subscription: Optional["Disposable"] = None
        self.add_child(child)

    def on_mount(self) -> None:
        super().on_mount()
        if isinstance(self._condition, ObservableBase):
            self.observe(self._condition, self._on_condition_changed)

    def on_unmount(self) -> None:
        self._stop_animation_subscription()
        super().on_unmount()

    def _on_condition_changed(self, value: bool) -> None:
        next_visible = bool(value)
        if next_visible == self._logical_visible:
            return
        self._logical_visible = next_visible
        self._active_transition = self._transition_in if next_visible else self._transition_out
        animatable = self._ensure_animatable()
        animatable.set_motion(self._active_transition.motion)
        animatable.target = 1.0 if next_visible else 0.0
        self.invalidate()

    def _ensure_animatable(self) -> Animatable[float]:
        if self._animatable is not None:
            return self._animatable
        animatable: Animatable[float] = Animatable(self._progress, motion=self._active_transition.motion)
        self._animatable = animatable

        def _on_progress(value: float) -> None:
            self._progress = float(value)
            self.invalidate()

        self._animatable_subscription = animatable.subscribe(_on_progress)
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
                "visible_animation_unsubscribe_exc",
                "_AnimatedVisibleBox failed to dispose animation subscription",
            )
        self._animatable_subscription = None

    def _child(self) -> Optional[Widget]:
        if not self.children:
            return None
        child = self.children[0]
        if isinstance(child, Widget):
            return child
        return None

    def _resolve_visuals(self) -> Optional[TransitionVisuals]:
        try:
            return self._active_transition.pattern.resolve(self._progress)
        except Exception:
            exception_once(
                logger,
                "visible_resolve_visuals_exc",
                "TransitionPattern.resolve raised in _AnimatedVisibleBox",
            )
            return None

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        child = self._child()
        if child is None:
            return super().preferred_size(max_width=max_width, max_height=max_height)
        try:
            return child.preferred_size(max_width=max_width, max_height=max_height)
        except Exception:
            exception_once(
                logger,
                "visible_preferred_size_exc",
                "Child preferred_size raised in _AnimatedVisibleBox",
            )
            return super().preferred_size(max_width=max_width, max_height=max_height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        child = self._child()
        if child is None:
            return
        try:
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)
        except Exception:
            exception_once(
                logger,
                "visible_layout_exc",
                "Child layout raised in _AnimatedVisibleBox",
            )

    def paint_outsets(self) -> Tuple[int, int, int, int]:
        # A slide or scale moves the child's pixels; a container deciding
        # whether this widget can be seen at all has to know where they end up.
        visuals = self._resolve_visuals()
        if visuals is None or not _has_visual_effect(visuals):
            return super().paint_outsets()
        rect = self.layout_rect
        width, height = (rect[2], rect[3]) if rect is not None else (0, 0)
        return transformed_outsets(
            width,
            height,
            translate=_translation(visuals, width, height),
            scale=(
                visuals.scale_x if visuals.scale_x is not None else 1.0,
                visuals.scale_y if visuals.scale_y is not None else 1.0,
            ),
        )

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        child = self._child()
        if child is None:
            return

        visuals = self._resolve_visuals()
        if visuals is None or canvas is None or not _has_visual_effect(visuals):
            try:
                child.set_last_rect(x, y, width, height)
                child.paint(canvas, x, y, width, height)
            except Exception:
                exception_once(
                    logger,
                    "visible_paint_no_visuals_exc",
                    "Child paint raised in _AnimatedVisibleBox",
                )
            return

        op = _clamp_unit(visuals.opacity) if visuals.opacity is not None else 1.0
        sx = visuals.scale_x if visuals.scale_x is not None else 1.0
        sy = visuals.scale_y if visuals.scale_y is not None else 1.0
        tx, ty = _translation(visuals, width, height)

        needs_opacity = op < 1.0
        try:
            canvas.save()
            if needs_opacity:
                try:
                    from nuiitivet.rendering.skia.color import make_opacity_paint

                    layer_paint = make_opacity_paint(op)
                    if layer_paint is not None:
                        canvas.saveLayer(None, layer_paint)
                except Exception:
                    exception_once(
                        logger,
                        "visible_opacity_layer_exc",
                        "_AnimatedVisibleBox failed to apply opacity layer",
                    )

            if tx != 0.0 or ty != 0.0:
                canvas.translate(tx, ty)
            if sx != 1.0 or sy != 1.0:
                cx = float(x) + float(width) / 2.0
                cy = float(y) + float(height) / 2.0
                canvas.translate(cx, cy)
                canvas.scale(sx, sy)
                canvas.translate(-cx, -cy)

            child.set_last_rect(x, y, width, height)
            child.paint(canvas, x, y, width, height)
        except Exception:
            exception_once(
                logger,
                "visible_paint_exc",
                "_AnimatedVisibleBox paint raised",
            )
        finally:
            try:
                if needs_opacity:
                    canvas.restore()
                canvas.restore()
            except Exception:
                exception_once(
                    logger,
                    "visible_restore_exc",
                    "_AnimatedVisibleBox canvas.restore failed",
                )


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _translation(visuals: TransitionVisuals, width: float, height: float) -> Tuple[float, float]:
    """Total ``(dx, dy)`` of a transition step: absolute plus size-relative."""
    tx = visuals.translate_x if visuals.translate_x is not None else 0.0
    ty = visuals.translate_y if visuals.translate_y is not None else 0.0
    if visuals.translate_x_fraction is not None:
        tx += visuals.translate_x_fraction * float(width)
    if visuals.translate_y_fraction is not None:
        ty += visuals.translate_y_fraction * float(height)
    return (tx, ty)


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


def _hidden_observable(
    condition: VisibleConditionLike,
) -> Union[bool, ObservableBase[bool]]:
    if isinstance(condition, ObservableBase):
        source = condition
        return ComputedObservable(lambda: not bool(source.value))
    return not bool(condition)


def _opacity_observable(
    condition: VisibleConditionLike,
) -> Union[float, ObservableBase[float]]:
    if isinstance(condition, ObservableBase):
        source = condition
        return ComputedObservable(lambda: 1.0 if bool(source.value) else 0.0)
    return 1.0 if bool(condition) else 0.0


@dataclass(slots=True)
class _AnimatedVisibleModifier(ModifierElement):
    """Animated branch of :func:`visible`. Wraps with a paint box and passthrough_pointer."""

    condition: VisibleConditionLike
    transition: TransitionDefinition
    transition_out: Optional[TransitionDefinition] = None

    def apply(self, widget: Widget) -> Widget:
        paint_box = _AnimatedVisibleBox(widget, self.condition, self.transition, self.transition_out)
        hidden = _hidden_observable(self.condition)
        return PassthroughPointerBox(BlockFocusTraversalBox(paint_box, hidden), hidden)


def visible(
    condition: VisibleConditionLike,
    *,
    transition: Optional[TransitionDefinition] = None,
    transition_out: Optional[TransitionDefinition] = None,
) -> ModifierElement:
    """Toggle a widget's visibility as a thin composition of paint / input primitives.

    When *condition* is ``False`` the widget is rendered fully transparent,
    ignores pointer / hit events, and is skipped by Tab traversal; when ``True``
    it is fully opaque and interactive. The widget continues to occupy its
    normal layout space in both states (use a layout-aware Widget if you need
    the layout to collapse).

    Args:
        condition: Static ``bool`` or an ``Observable[bool]`` driving visibility.
        transition: Optional :class:`TransitionDefinition` whose pattern drives
            the ``opacity`` (and optional ``scale`` / ``translate``) animation
            on enter / exit. When omitted, visibility flips instantly.
        transition_out: Optional :class:`TransitionDefinition` applied only on
            exit (becoming hidden). When omitted, *transition* is used for both
            directions. Has no effect unless *transition* is also provided.

    Returns:
        A :class:`ModifierElement` to apply via ``widget.modifier(...)``. With
        no *transition* this is literally ``opacity(...) |
        block_focus_traversal(...) | passthrough_pointer(...)``.

    Note:
        ``visible()`` is a paint-time / input-time convenience and does *not*
        manage layout. The child is always eagerly mounted and keeps its
        layout space while hidden. Widget-local state is therefore preserved
        across hide / show cycles.
    """
    if transition is None:
        composed: Modifier = Modifier()
        composed = composed.then(opacity(_opacity_observable(condition)))
        composed = composed.then(block_focus_traversal(_hidden_observable(condition)))
        composed = composed.then(passthrough_pointer(_hidden_observable(condition)))
        return composed
    return _AnimatedVisibleModifier(
        condition=condition,
        transition=transition,
        transition_out=transition_out,
    )


__all__ = [
    "visible",
]
