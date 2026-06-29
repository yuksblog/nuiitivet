"""ScrollController: multi-axis scroll state manager.

Inspired by Jetpack Compose's ScrollState, this centralizes scroll state for
multiple axes, not just a single axis.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, Mapping, Tuple

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import Observable

from .types import ScrollDirection, ScrollPhysics


_logger = logging.getLogger(__name__)


class ScrollAxisState:
    """Holds scroll metrics for a single axis.

    This uses `Observable` descriptors for per-instance observable fields
    instead of constructing runtime `Value(...)` objects. Instances still
    expose `_ObservableValue` objects when accessed (via the descriptor), so
    calling code can use `.value` and `.subscribe(...)` as before.
    """

    offset = Observable(0.0)
    max_extent = Observable(0.0)
    viewport_size = Observable(0)
    content_size = Observable(0)

    def __init__(self, axis: ScrollDirection, initial: float = 0.0) -> None:
        self.axis = axis
        try:
            setattr(self, "offset", float(initial))
        except Exception:
            try:
                setattr(self, "offset", float(initial))
            except Exception:
                exception_once(
                    _logger,
                    "scroll_axis_state_init_offset_exc",
                    "ScrollAxisState offset initialization failed",
                )


class ScrollController:
    """Manages scroll state and provides scroll operations.

    ScrollController is used together with VerticalScrollable /
    HorizontalScrollable. When one is not supplied, those widgets create one
    internally. Scroll behavior (``physics``) and wheel sensitivity
    (``scroll_multiplier``) are held by the controller.

    Examples:
        Basic usage (auto-created):
            VerticalScrollable(child=Column([...]))

        Controlled externally:
            controller = ScrollController()
            VerticalScrollable(child=..., controller=controller)
            controller.scroll_to_end()

        Observing the scroll position:
            controller = ScrollController()
            axis = controller.axis_state(controller.primary_axis)
            axis.offset.subscribe(lambda pos: print(f"At {pos}"))
            VerticalScrollable(child=..., controller=controller)
    """

    def __init__(
        self,
        *,
        axes: Iterable[ScrollDirection] | None = None,
        primary_axis: ScrollDirection | None = None,
        initial_offsets: Mapping[ScrollDirection, float] | None = None,
        physics: ScrollPhysics | str = ScrollPhysics.CLAMP,
        scroll_multiplier: float = 20.0,
    ):
        """Initialize the ScrollController.

        Args:
            axes: The set of managed axes (defaults to vertical only).
            primary_axis: The axis referenced by helpers like get_offset()/is_at_start.
            initial_offsets: Per-axis initial offset overrides.
            physics: Scroll behavior (clamp / disabled). See :class:`ScrollPhysics`.
            scroll_multiplier: Scroll amount in pixels per mouse-wheel step.
        """
        axis_list: Tuple[ScrollDirection, ...]
        if axes is None:
            axis_list = (ScrollDirection.VERTICAL,)
        else:
            deduped = []
            for axis in axes:
                axis = axis if isinstance(axis, ScrollDirection) else ScrollDirection(axis)
                if axis not in deduped:
                    deduped.append(axis)
            if not deduped:
                raise ValueError("ScrollController requires at least one axis")
            axis_list = tuple(deduped)

        if primary_axis is None:
            primary_axis = axis_list[0]
        elif primary_axis not in axis_list:
            raise ValueError("primary_axis must be part of axes")

        self._axes: Tuple[ScrollDirection, ...] = axis_list
        self._primary_axis: ScrollDirection = primary_axis
        self._physics: ScrollPhysics = physics if isinstance(physics, ScrollPhysics) else ScrollPhysics(physics)
        self._scroll_multiplier: float = float(scroll_multiplier)

        offsets: Dict[ScrollDirection, float] = {}
        if initial_offsets:
            offsets = {ScrollDirection(k): float(v) for k, v in initial_offsets.items()}

        self._axis_states: Dict[ScrollDirection, ScrollAxisState] = {}
        for axis in self._axes:
            axis_initial = offsets.get(axis, 0.0)
            self._axis_states[axis] = ScrollAxisState(axis, initial=float(axis_initial))

    @property
    def axes(self) -> Tuple[ScrollDirection, ...]:
        return self._axes

    @property
    def primary_axis(self) -> ScrollDirection:
        return self._primary_axis

    @property
    def physics(self) -> ScrollPhysics:
        """Scroll behavior (clamp / disabled)."""
        return self._physics

    @property
    def scroll_multiplier(self) -> float:
        """Scroll amount in pixels per mouse-wheel step."""
        return self._scroll_multiplier

    def has_axis(self, axis: ScrollDirection) -> bool:
        return axis in self._axis_states

    def axis_state(self, axis: ScrollDirection) -> ScrollAxisState:
        try:
            return self._axis_states[axis]
        except KeyError as exc:  # pragma: no cover
            raise ValueError(f"ScrollController does not manage axis {axis}") from exc

    def _resolve_axis(self, axis: ScrollDirection | None) -> ScrollAxisState:
        if axis is None:
            axis = self._primary_axis
        return self.axis_state(axis)

    def _primary_axis_state(self) -> ScrollAxisState:
        return self.axis_state(self._primary_axis)

    @property
    def max_extent(self) -> float:
        """Maximum scrollable distance in pixels.

        Computed as content_size - viewport_size. Updated automatically by the
        scrollable widget.
        """
        return self._primary_axis_state().max_extent.value

    def axis_max_extent(self, axis: ScrollDirection) -> float:
        return self.axis_state(axis).max_extent.value

    @property
    def viewport_size(self) -> int:
        """Viewport size in pixels."""
        return self._primary_axis_state().viewport_size.value

    def axis_viewport_size(self, axis: ScrollDirection) -> int:
        return self.axis_state(axis).viewport_size.value

    @property
    def content_size(self) -> int:
        """Total content size in pixels."""
        return self._primary_axis_state().content_size.value

    def axis_content_size(self, axis: ScrollDirection) -> int:
        return self.axis_state(axis).content_size.value

    @property
    def is_at_start(self) -> bool:
        return self.get_offset() <= 0

    @property
    def is_at_end(self) -> bool:
        return self.get_offset() >= self.max_extent

    def get_offset(self, axis: ScrollDirection | None = None) -> float:
        return self._resolve_axis(axis).offset.value

    def scroll_to(self, offset: float, *, axis: ScrollDirection | None = None) -> None:
        """Scroll to the given offset.

        The offset is clamped to the range 0 .. max_extent.

        Args:
            offset: Target scroll position in pixels.
        """
        axis_state = self._resolve_axis(axis)
        max_extent = getattr(axis_state.max_extent, "value", 0.0)
        clamped = max(0.0, min(float(offset), max_extent))
        try:
            axis_state.offset.value = clamped
        except Exception:
            try:
                axis_state.offset.value = clamped
            except Exception:
                exception_once(
                    _logger,
                    "scroll_controller_scroll_to_set_offset_exc",
                    "ScrollController scroll_to failed to set offset",
                )

    def scroll_by(self, delta: float, *, axis: ScrollDirection | None = None) -> None:
        """Scroll relative to the current position."""
        axis_state = self._resolve_axis(axis)
        self.scroll_to(axis_state.offset.value + delta, axis=axis_state.axis)

    def scroll_to_start(self, *, axis: ScrollDirection | None = None) -> None:
        axis_state = self._resolve_axis(axis)
        try:
            axis_state.offset.value = 0.0
        except Exception:
            try:
                axis_state.offset.value = 0.0
            except Exception:
                exception_once(
                    _logger,
                    "scroll_controller_scroll_to_start_set_offset_exc",
                    "ScrollController scroll_to_start failed to set offset",
                )

    def scroll_to_end(self, *, axis: ScrollDirection | None = None) -> None:
        axis_state = self._resolve_axis(axis)
        try:
            max_val = getattr(axis_state.max_extent, "value", None)
            if max_val is None and hasattr(axis_state.max_extent, "value"):
                max_val = axis_state.max_extent.value
            axis_state.offset.value = max_val
        except Exception:
            try:
                axis_state.offset.value = getattr(axis_state.max_extent, "value", 0.0)
            except Exception:
                exception_once(
                    _logger,
                    "scroll_controller_scroll_to_end_set_offset_exc",
                    "ScrollController scroll_to_end failed to set offset",
                )

    def _update_metrics(
        self,
        max_extent: float,
        viewport_size: int,
        content_size: int,
        *,
        axis: ScrollDirection | None = None,
    ) -> None:
        """Update scroll metrics (for the scrollable widget only)."""
        state = self._resolve_axis(axis)
        try:
            state.max_extent.value = float(max_extent)
        except Exception:
            try:
                state.max_extent.value = float(max_extent)
            except Exception:
                exception_once(
                    _logger,
                    "scroll_controller_update_metrics_set_max_extent_exc",
                    "ScrollController failed to set max_extent",
                )
        try:
            state.viewport_size.value = int(viewport_size)
        except Exception:
            try:
                state.viewport_size.value = int(viewport_size)
            except Exception:
                exception_once(
                    _logger,
                    "scroll_controller_update_metrics_set_viewport_size_exc",
                    "ScrollController failed to set viewport_size",
                )
        try:
            state.content_size.value = int(content_size)
        except Exception:
            try:
                state.content_size.value = int(content_size)
            except Exception:
                exception_once(
                    _logger,
                    "scroll_controller_update_metrics_set_content_size_exc",
                    "ScrollController failed to set content_size",
                )


__all__ = ["ScrollAxisState", "ScrollController"]
