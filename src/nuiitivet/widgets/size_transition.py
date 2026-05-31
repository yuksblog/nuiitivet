"""SizeTransition - animate a child's layout size as it changes.

``SizeTransition`` participates in the *layout* phase: it interpolates the
allocated width/height it reports to its parent so that a child growing or
shrinking (or being collapsed via ``condition``) does so smoothly instead of
snapping.

This is the layout-aware counterpart of the paint-only ``visible()`` modifier.
Use ``visible()`` for opacity/scale fades that keep their layout space; use
``SizeTransition`` when the layout footprint itself must animate (side sheets,
expandable panels, etc.).

Following the framework's overflow philosophy (see ``docs/design/LAYOUT.md``),
``SizeTransition`` does **not** clip its child: clipping is the responsibility
of the ``clip()`` modifier. While the animated rectangle is smaller than the
child's natural size the child overflows by default; wrap the widget in
``clip()`` when the overflow must be hidden::

    SizeTransition(panel, condition=vm.is_open).modifier(clip())

Usage::

    # Follow the child's natural size changes.
    SizeTransition(my_panel)

    # Open / close along the horizontal axis with distinct exit timing.
    SizeTransition(
        my_panel,
        condition=vm.is_open,
        axis="horizontal",
        motion=EXPRESSIVE_DEFAULT_SPATIAL,   # design-layer curve (optional)
        motion_out=EXPRESSIVE_FAST_SPATIAL,
    )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, Optional, Tuple, Union

from nuiitivet.animation.animatable import Animatable
from nuiitivet.animation.motion import BezierMotion, Motion
from nuiitivet.common.logging_once import exception_once
from nuiitivet.layout.alignment import normalize_alignment
from nuiitivet.layout.measure import preferred_size as measure_preferred_size
from nuiitivet.observable.protocols import ReadOnlyObservableProtocol
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.observable.protocols import Disposable

logger = logging.getLogger(__name__)


Axis = Literal["both", "horizontal", "vertical"]
ConditionLike = Union[bool, ReadOnlyObservableProtocol[bool]]

# Sub-pixel changes below this threshold do not trigger a retarget.
_EPSILON = 0.5

# Default size motion. Defined locally so this widget depends only on the
# animation layer (avoids a widgets -> material cross dependency). Design
# layers may pass an explicit ``motion`` to apply M3 expressive curves.
_DEFAULT_MOTION: Motion = BezierMotion(0.38, 1.21, 0.22, 1.00, 0.50)


def _read_condition(condition: ConditionLike) -> bool:
    if isinstance(condition, ReadOnlyObservableProtocol):
        try:
            return bool(condition.value)
        except Exception:
            exception_once(
                logger,
                "size_transition_condition_read_exc",
                "Failed to read SizeTransition condition observable",
            )
            return True
    return bool(condition)


class SizeTransition(Widget):
    """Single-child widget that animates its layout size.

    The child is always mounted and laid out at its own natural size; the
    *allocated* rectangle reported to the parent is interpolated per axis. While
    the size is smaller than the child's natural size, the child overflows the
    allocated rectangle (positioned by ``alignment``) and is not clipped. Wrap
    the widget in the ``clip()`` modifier to hide the overflow.
    """

    def __init__(
        self,
        child: Optional[Widget] = None,
        *,
        condition: Optional[ConditionLike] = None,
        motion: Motion = _DEFAULT_MOTION,
        motion_out: Optional[Motion] = None,
        axis: Axis = "both",
        alignment: Union[str, Tuple[str, str]] = "top_left",
    ) -> None:
        """Initialize a SizeTransition.

        Args:
            child: The ``Widget`` whose layout size is animated.
            condition: Optional ``bool`` / ``Observable[bool]``. When ``False``
                the child collapses to zero size along the animated axes; when
                ``True`` it expands to the child's natural size. When omitted,
                the widget simply follows the child's natural size changes.
            motion: Base motion used for both grow (enter) and shrink (exit).
            motion_out: Optional motion that overrides only the shrink (exit)
                direction. When omitted, ``motion`` is used for both.
            axis: Which axis/axes to animate (``"both"``, ``"horizontal"``,
                ``"vertical"``). Axes that are not animated pass the child's
                natural size through unchanged.
            alignment: Alignment of the child within the animated rectangle.
        """
        super().__init__(max_children=1, overflow_policy="replace_last")
        self._condition = condition
        self._motion_in = motion
        self._motion_out = motion_out if motion_out is not None else motion
        self._axis: Axis = axis
        self._align = normalize_alignment(alignment, default=("start", "start"))

        self._width_anim: Animatable[float] = Animatable(0.0, motion=self._motion_in)
        self._height_anim: Animatable[float] = Animatable(0.0, motion=self._motion_in)
        self._width_sub: Optional["Disposable"] = None
        self._height_sub: Optional["Disposable"] = None
        self._initialized = False

        if child is not None:
            self.add_child(child)

    # --- Child access ------------------------------------------------------
    def _child(self) -> Optional[Widget]:
        if not self.children:
            return None
        child = self.children[0]
        return child if isinstance(child, Widget) else None

    def _animates_width(self) -> bool:
        return self._axis in ("both", "horizontal")

    def _animates_height(self) -> bool:
        return self._axis in ("both", "vertical")

    # --- Lifecycle ---------------------------------------------------------
    def on_mount(self) -> None:
        super().on_mount()
        self._width_sub = self._width_anim.subscribe(self._on_tick)
        self._height_sub = self._height_anim.subscribe(self._on_tick)
        if isinstance(self._condition, ReadOnlyObservableProtocol):
            self.observe(self._condition, self._on_condition_changed)

    def on_unmount(self) -> None:
        self._dispose_subscription(self._width_sub)
        self._dispose_subscription(self._height_sub)
        self._width_sub = None
        self._height_sub = None
        try:
            self._width_anim.stop()
            self._height_anim.stop()
        except Exception:
            exception_once(
                logger,
                "size_transition_stop_exc",
                "SizeTransition failed to stop animatables on unmount",
            )
        super().on_unmount()

    def _dispose_subscription(self, sub: Optional["Disposable"]) -> None:
        if sub is None:
            return
        dispose = getattr(sub, "dispose", None)
        if callable(dispose):
            try:
                dispose()
            except Exception:
                exception_once(
                    logger,
                    "size_transition_unsubscribe_exc",
                    "SizeTransition failed to dispose subscription",
                )

    def _on_tick(self, _: float) -> None:
        self.mark_needs_layout()
        self.invalidate()

    def _on_condition_changed(self, _: bool) -> None:
        # Re-measure and retarget on the next layout pass.
        self.mark_needs_layout()
        self.invalidate()

    # --- Target resolution -------------------------------------------------
    def _natural_size(self, max_width: Optional[int], max_height: Optional[int]) -> Tuple[int, int]:
        child = self._child()
        if child is None:
            return (0, 0)
        try:
            return measure_preferred_size(child, max_width=max_width, max_height=max_height)
        except Exception:
            exception_once(
                logger,
                "size_transition_measure_exc",
                "SizeTransition failed to measure child preferred size",
            )
            return (0, 0)

    def _retarget(self, anim: Animatable[float], target: float) -> None:
        if abs(anim.target - target) <= _EPSILON:
            return
        motion = self._motion_in if target >= anim.target else self._motion_out
        anim.set_motion(motion)
        anim.target = target

    def _sync_targets(self, natural_w: int, natural_h: int) -> Tuple[int, int]:
        """Sync animation targets to current natural size / condition.

        Returns the resolved (possibly animating) outer size.
        """
        open_ = True if self._condition is None else _read_condition(self._condition)

        width_target = float(natural_w) if open_ else 0.0
        height_target = float(natural_h) if open_ else 0.0

        if not self._initialized:
            # Snap to initial state without animating on first measure.
            self._initialized = True
            self._width_anim.snap_to(width_target if self._animates_width() else float(natural_w))
            self._height_anim.snap_to(height_target if self._animates_height() else float(natural_h))

        if self._animates_width():
            self._retarget(self._width_anim, width_target)
            out_w = int(round(self._width_anim.value))
        else:
            out_w = natural_w

        if self._animates_height():
            self._retarget(self._height_anim, height_target)
            out_h = int(round(self._height_anim.value))
        else:
            out_h = natural_h

        return (max(0, out_w), max(0, out_h))

    # --- Layout / measure --------------------------------------------------
    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        natural_w, natural_h = self._natural_size(max_width, max_height)
        return self._sync_targets(natural_w, natural_h)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        child = self._child()
        if child is None:
            return

        # Child is always laid out at its natural size; only the outer
        # allocation animates. The child is then aligned within `width`/
        # `height` (and overflows when the allocation is smaller).
        natural_w, natural_h = self._natural_size(None, None)
        self._sync_targets(natural_w, natural_h)

        child_w = natural_w if self._animates_width() else width
        child_h = natural_h if self._animates_height() else height
        try:
            child.layout(child_w, child_h)
        except Exception:
            exception_once(
                logger,
                "size_transition_child_layout_exc",
                "SizeTransition child layout raised",
            )
            return

        fx = {"start": 0.0, "center": 0.5, "end": 1.0}.get(self._align[0], 0.0)
        fy = {"start": 0.0, "center": 0.5, "end": 1.0}.get(self._align[1], 0.0)
        cx = int(round((width - child_w) * fx))
        cy = int(round((height - child_h) * fy))
        child.set_layout_rect(cx, cy, child_w, child_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)
        child = self._child()
        if child is None:
            return

        rect = child.layout_rect
        if rect is None:
            cx, cy, cw, ch = x, y, width, height
        else:
            rx, ry, rw, rh = rect
            cx, cy, cw, ch = x + rx, y + ry, rw, rh

        try:
            child.set_last_rect(cx, cy, cw, ch)
            child.paint(canvas, cx, cy, cw, ch)
        except Exception:
            exception_once(
                logger,
                "size_transition_child_paint_exc",
                "SizeTransition child paint raised",
            )


__all__ = ["SizeTransition"]
