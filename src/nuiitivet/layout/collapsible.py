"""Collapsible - animate a child's layout size as it opens and closes.

``Collapsible`` participates in the *layout* phase: it interpolates the
allocated width/height it reports to its parent so that a child growing or
collapsing does so smoothly instead of snapping.

This is the layout-aware counterpart of the paint-only ``visible()`` modifier.
Use ``visible()`` for opacity/scale fades that keep their layout space; use
``Collapsible`` when the layout footprint itself must animate (side sheets,
expandable panels, etc.).

Clipping is applied internally at all times; no ``clip()`` modifier is needed::

    Collapsible(panel, opened=vm.is_open)

Usage::

    # Simple vertical expand/collapse driven by an observable.
    Collapsible(my_panel, opened=vm.is_open)

    # Horizontal axis with distinct exit timing.
    Collapsible(
        my_panel,
        opened=vm.is_open,
        axis="horizontal",
        motion=EXPRESSIVE_DEFAULT_SPATIAL,
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
from nuiitivet.observable.protocols import ObservableBase
from nuiitivet.rendering.skia.geometry import clip_rect, make_rect
from nuiitivet.widgets.interaction import FocusTraversalBlocker
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from nuiitivet.observable.protocols import Disposable

logger = logging.getLogger(__name__)


Axis = Literal["both", "horizontal", "vertical"]

# Sub-pixel changes below this threshold do not trigger a retarget.
_EPSILON = 0.5

# Default size motion. Defined locally so this widget depends only on the
# animation layer (avoids a layout -> material cross dependency). Design
# layers may pass an explicit ``motion`` to apply M3 expressive curves.
_DEFAULT_MOTION: Motion = BezierMotion(0.38, 1.21, 0.22, 1.00, 0.50)


def _read_opened(opened: Union[bool, ObservableBase[bool]]) -> bool:
    if isinstance(opened, ObservableBase):
        try:
            return bool(opened.value)
        except Exception:
            exception_once(
                logger,
                "collapsible_opened_read_exc",
                "Failed to read Collapsible opened observable",
            )
            return True
    return bool(opened)


class Collapsible(FocusTraversalBlocker, Widget):
    """Single-child widget that animates its layout size open and closed.

    The child is always mounted and laid out at its own natural size; the
    *allocated* rectangle reported to the parent is interpolated per axis.
    The animated rectangle is clipped internally, so the child never overflows
    its allocated bounds.

    ``preferred_size`` only *reports* that interpolated rectangle: measuring is
    speculative and repeated, so it never retargets. ``layout`` owns the
    animation -- both the retarget and the first-layout snap to the initial
    state.
    """

    def __init__(
        self,
        child: Optional[Widget] = None,
        *,
        opened: Union[bool, ObservableBase[bool]] = True,
        motion: Motion = _DEFAULT_MOTION,
        motion_out: Optional[Motion] = None,
        axis: Axis = "both",
        alignment: Union[str, Tuple[str, str]] = "top-left",
        key: Optional[str] = None,
    ) -> None:
        """Initialize a Collapsible.

        Args:
            child: The ``Widget`` whose layout size is animated.
            opened: ``bool`` / ``Observable[bool]``. When ``False`` the child
                collapses to zero size along the animated axes; when ``True``
                it expands to the child's natural size.
            motion: Base motion used for both open (enter) and close (exit).
            motion_out: Optional motion that overrides only the close (exit)
                direction. When omitted, ``motion`` is used for both.
            axis: Which axis/axes to animate (``"both"``, ``"horizontal"``,
                ``"vertical"``). Axes that are not animated pass the child's
                natural size through unchanged.
            alignment: Alignment of the child within the animated rectangle.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(max_children=1, overflow_policy="replace_last", key=key)
        self._opened: Union[bool, ObservableBase[bool]] = opened
        self._motion_in = motion
        self._motion_out = motion_out if motion_out is not None else motion
        self._axis: Axis = axis
        self._align = normalize_alignment(alignment, default=("start", "start"))

        self._width_anim: Animatable[float] = Animatable(0.0, motion=self._motion_in)
        self._height_anim: Animatable[float] = Animatable(0.0, motion=self._motion_in)
        self._width_sub: Optional["Disposable"] = None
        self._height_sub: Optional["Disposable"] = None
        self._initialized = False
        # Constraints of the most recent measure pass. ``layout`` reuses them
        # so the child is measured identically on both paths and the animation
        # target cannot depend on which pass asked.
        self._measure_constraints: Tuple[Optional[int], Optional[int]] = (None, None)

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

    # --- Focus traversal ---------------------------------------------------
    @property
    def blocks_focus_traversal(self) -> bool:
        """Keep the child out of the Tab sequence while the collapsible is closed.

        The child stays mounted and laid out at its natural size while closed,
        so without this its focusable widgets would remain Tab stops behind the
        clip. Traversal follows the ``opened`` flag rather than the size
        animation: the content becomes reachable as soon as it starts expanding
        (it is on screen by then) and unreachable as soon as it starts
        collapsing.
        """
        return not _read_opened(self._opened)

    # --- Lifecycle ---------------------------------------------------------
    def on_mount(self) -> None:
        super().on_mount()
        # Only the animated axes drive relayout; the other Animatable is never
        # retargeted, so subscribing to it would keep a dead callback alive.
        if self._animates_width():
            self._width_sub = self._width_anim.subscribe(self._on_tick)
        if self._animates_height():
            self._height_sub = self._height_anim.subscribe(self._on_tick)
        if isinstance(self._opened, ObservableBase):
            self.observe(self._opened, self._on_opened_changed)

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
                "collapsible_stop_exc",
                "Collapsible failed to stop animatables on unmount",
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
                    "collapsible_unsubscribe_exc",
                    "Collapsible failed to dispose subscription",
                )

    def _on_tick(self, _: float) -> None:
        self.mark_needs_layout()
        self.invalidate()

    def _on_opened_changed(self, _: bool) -> None:
        # Re-measure and retarget on the next layout pass.
        self.mark_needs_layout()
        self.invalidate()

    # --- Target resolution -------------------------------------------------
    def _child_constraints(self) -> Tuple[Optional[int], Optional[int]]:
        """Constraints to measure the child under, on both passes.

        Taken from the latest measure pass, minus every axis this widget
        animates. A parent derives what it offers from the size we last
        reported, which on an animated axis is the interpolated one -- feeding
        that back in would let an axis that reached zero measure its child as
        zero and never reopen. Axes that merely pass through carry the parent's
        constraint as usual, so a child that reflows (wrapping text) is still
        measured against the width it will really get.
        """
        max_width, max_height = self._measure_constraints
        return (
            None if self._animates_width() else max_width,
            None if self._animates_height() else max_height,
        )

    def _natural_size(self, max_width: Optional[int], max_height: Optional[int]) -> Tuple[int, int]:
        child = self._child()
        if child is None:
            return (0, 0)
        try:
            return measure_preferred_size(child, max_width=max_width, max_height=max_height)
        except Exception:
            exception_once(
                logger,
                "collapsible_measure_exc",
                "Collapsible failed to measure child preferred size",
            )
            return (0, 0)

    def _retarget(self, anim: Animatable[float], target: float) -> None:
        if abs(anim.target - target) <= _EPSILON:
            return
        motion = self._motion_in if target >= anim.target else self._motion_out
        anim.set_motion(motion)
        anim.target = target

    def _sync_targets(self, natural_w: int, natural_h: int) -> None:
        """Sync animation targets to current natural size / opened state.

        Called from ``layout`` only: retargeting is a command, and measuring
        must not perform it.
        """
        open_ = _read_opened(self._opened)

        width_target = float(natural_w) if open_ else 0.0
        height_target = float(natural_h) if open_ else 0.0

        if not self._initialized:
            # Snap to the initial state without animating on the first layout.
            self._initialized = True
            if self._animates_width():
                self._width_anim.snap_to(width_target)
            if self._animates_height():
                self._height_anim.snap_to(height_target)
            return

        if self._animates_width():
            self._retarget(self._width_anim, width_target)
        if self._animates_height():
            self._retarget(self._height_anim, height_target)

    def _resolve_size(self, natural_w: int, natural_h: int) -> Tuple[int, int]:
        """Return the outer size implied by the current animation state.

        Read-only: animated axes report their interpolated value, other axes
        pass the natural size through. Before the first layout no target has
        been resolved yet, so report the size that layout is about to snap to.
        """
        if not self._initialized:
            open_ = _read_opened(self._opened)
            out_w = natural_w if open_ or not self._animates_width() else 0
            out_h = natural_h if open_ or not self._animates_height() else 0
            return (max(0, out_w), max(0, out_h))

        out_w = int(round(self._width_anim.value)) if self._animates_width() else natural_w
        out_h = int(round(self._height_anim.value)) if self._animates_height() else natural_h
        return (max(0, out_w), max(0, out_h))

    # --- Layout / measure --------------------------------------------------
    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Report the current (possibly interpolated) outer size.

        Measuring never touches the animation: the reported size follows
        whatever ``layout`` last resolved. The constraints are remembered so
        the following ``layout`` measures the child the same way.
        """
        self._measure_constraints = (max_width, max_height)
        natural_w, natural_h = self._natural_size(*self._child_constraints())
        return self._resolve_size(natural_w, natural_h)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        child = self._child()
        if child is None:
            return

        # Child is always laid out at its natural size; only the outer
        # allocation animates. The child is then aligned within `width`/
        # `height` and clipped to those bounds. The natural size is measured
        # under the constraints of the preceding measure pass so that the
        # target matches the size the parent was told about.
        natural_w, natural_h = self._natural_size(*self._child_constraints())
        self._sync_targets(natural_w, natural_h)

        child_w = natural_w if self._animates_width() else width
        child_h = natural_h if self._animates_height() else height
        try:
            child.layout(child_w, child_h)
        except Exception:
            exception_once(
                logger,
                "collapsible_child_layout_exc",
                "Collapsible child layout raised",
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

        # When the allocated rect has zero area the child is fully hidden.
        # Skip painting entirely; do not rely on the clip below because the
        # clip is only established when width > 0 and height > 0.
        if width <= 0 or height <= 0:
            return

        rect = child.layout_rect
        if rect is None:
            cx, cy, cw, ch = x, y, width, height
        else:
            rx, ry, rw, rh = rect
            cx, cy, cw, ch = x + rx, y + ry, rw, rh

        clip_saved = False
        if canvas is not None:
            clip_area = make_rect(x, y, width, height)
            try:
                canvas.save()
                if clip_area is not None and clip_rect(canvas, clip_area, True):
                    clip_saved = True
                else:
                    canvas.restore()
            except Exception:
                exception_once(
                    logger,
                    "collapsible_clip_save_exc",
                    "Collapsible clip save failed",
                )

        try:
            child.set_last_rect(cx, cy, cw, ch)
            child.paint(canvas, cx, cy, cw, ch)
        except Exception:
            exception_once(
                logger,
                "collapsible_child_paint_exc",
                "Collapsible child paint raised",
            )
        finally:
            if clip_saved:
                try:
                    canvas.restore()
                except Exception:
                    exception_once(
                        logger,
                        "collapsible_clip_restore_exc",
                        "Collapsible clip restore failed",
                    )


__all__ = ["Collapsible"]
