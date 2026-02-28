"""Material Design 3 Slider widgets."""

from __future__ import annotations

import logging
import math
import re
from enum import Enum
from typing import Callable, Optional, Sequence, Tuple, cast

from nuiitivet.common.logging_once import exception_once
from nuiitivet.input.codes import MOD_SHIFT
from nuiitivet.input.pointer import PointerEvent
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS
from nuiitivet.material.styles.slider_style import SliderStyle
from nuiitivet.observable import ObservableProtocol
from nuiitivet.rendering.sizing import Sizing, SizingLike
from nuiitivet.widgets.interaction import DraggableNode, PointerInputNode
from nuiitivet.animation import Animatable


_logger = logging.getLogger(__name__)


class Orientation(Enum):
    """Slider orientation."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


def _resolve_length_sizing(length: SizingLike) -> SizingLike:
    if isinstance(length, str):
        m = re.fullmatch(r"\s*([0-9]*\.?[0-9]+)\s*fr\s*", length, flags=re.IGNORECASE)
        if m is not None:
            weight = float(m.group(1))
            if weight <= 0.0:
                return Sizing.auto()
            return Sizing.flex(weight)
    return length


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


class _SliderBase(InteractiveWidget):
    """Shared behavior for slider widgets."""

    def __init__(
        self,
        *,
        min_value: float,
        max_value: float,
        stops: Optional[int],
        show_value_indicator: bool,
        disabled: bool | ObservableProtocol[bool],
        orientation: Orientation,
        length: SizingLike,
        padding,
        style,
    ) -> None:
        self._min_value = float(min_value)
        self._max_value = float(max_value)
        self._stops = int(stops) if stops is not None else None
        self._show_value_indicator = bool(show_value_indicator)
        self._orientation = orientation
        self._style = style
        style_for_layout = style or SliderStyle.xs()

        self._dragging = False
        self._active_handle_index = 0
        self._space_accel_armed = False

        self._track_x = 0.0
        self._track_y = 0.0
        self._track_w = 0.0
        self._track_h = 0.0
        self._track_start = 0.0
        self._track_end = 0.0

        self._state_layer_anim: Animatable[float] = Animatable(0.0, motion=EXPRESSIVE_DEFAULT_EFFECTS)

        default_padding = 0 if padding is None else padding
        if orientation is Orientation.HORIZONTAL:
            resolved_width = _resolve_length_sizing(length)
            resolved_height = Sizing.fixed(int(math.ceil(self._cross_axis_size(style_for_layout))))
        else:
            resolved_width = Sizing.fixed(int(math.ceil(self._cross_axis_size(style_for_layout))))
            resolved_height = _resolve_length_sizing(length)

        super().__init__(
            width=resolved_width,
            height=resolved_height,
            padding=default_padding,
            disabled=disabled,
            focusable=True,
        )

        self.bind(self._state_layer_anim.subscribe(lambda _v: self.invalidate()))

        self._drag_node = DraggableNode(
            on_drag_start=self._on_drag_start,
            on_drag_update=self._on_drag_update,
            on_drag_end=self._on_drag_end,
            hit_test=self._hit_test_handle,
        )
        self.add_node(self._drag_node)

        self._track_node = PointerInputNode(hit_test=self._hit_test_track)
        self._track_node.enable_click(on_press=self._on_track_press)
        self.add_node(self._track_node)

    @property
    def style(self):
        if self._style is not None:
            return self._style
        try:
            from nuiitivet.material.theme.theme_data import MaterialThemeData
            from nuiitivet.theme.manager import manager

            theme = manager.current.extension(MaterialThemeData)
            if theme is not None:
                return theme.slider_style
        except Exception:
            pass
        return SliderStyle.xs()

    def _cross_axis_size(self, style) -> float:
        return max(style.active_handle_height, style.state_layer_size, 48.0)

    def _value_to_ratio(self, value: float) -> float:
        span = self._max_value - self._min_value
        if span <= 0.0:
            return 0.0
        return _clamp((value - self._min_value) / span, 0.0, 1.0)

    def _ratio_to_value(self, ratio: float) -> float:
        ratio = _clamp(ratio, 0.0, 1.0)
        if self._stops is not None and self._stops >= 2:
            steps = max(2, int(self._stops))
            idx = int(round(ratio * (steps - 1)))
            ratio = float(idx) / float(steps - 1)
        span = self._max_value - self._min_value
        return self._min_value + (span * ratio)

    def _track_ratio_from_pointer(self, event: PointerEvent) -> float:
        axis_value = event.x if self._orientation is Orientation.HORIZONTAL else event.y
        if self._track_end <= self._track_start:
            return 0.0
        return _clamp((axis_value - self._track_start) / (self._track_end - self._track_start), 0.0, 1.0)

    def _get_state_layer_target_opacity(self) -> float:
        if self.state.dragging:
            return float(self._DRAG_OPACITY)
        if self.state.pressed:
            return float(self._PRESS_OPACITY)
        if self.state.hovered:
            return float(self._HOVER_OPACITY)
        return 0.0

    def _get_active_state_layer_opacity(self) -> float:
        target = self._get_state_layer_target_opacity()
        if abs(self._state_layer_anim.target - target) > 1e-6:
            self._state_layer_anim.target = target
        return float(self._state_layer_anim.value)

    def _on_drag_start(self, event: PointerEvent) -> None:
        self._dragging = True
        self._active_handle_index = self._pick_handle_index(event)
        self._update_value_from_ratio(self._track_ratio_from_pointer(event), from_track=False)

    def _on_drag_update(self, event: PointerEvent, _dx: float, _dy: float) -> None:
        self._update_value_from_ratio(self._track_ratio_from_pointer(event), from_track=False)

    def _on_drag_end(self, _event: PointerEvent) -> None:
        self._dragging = False

    def _on_track_press(self, event: PointerEvent) -> None:
        self._active_handle_index = self._pick_handle_index(event)
        self._update_value_from_ratio(self._track_ratio_from_pointer(event), from_track=True)

    def _hit_test_track(self, x: float, y: float) -> bool:
        gx, gy, gw, gh = self.global_layout_rect or (0, 0, 0, 0)
        self._compute_geometry(float(gx), float(gy), float(gw), float(gh))
        if self._track_w <= 0.0 or self._track_h <= 0.0:
            return False
        return (
            self._track_x <= x <= self._track_x + self._track_w and self._track_y <= y <= self._track_y + self._track_h
        )

    def _hit_test_handle(self, x: float, y: float) -> bool:
        gx, gy, gw, gh = self.global_layout_rect or (0, 0, 0, 0)
        self._compute_geometry(float(gx), float(gy), float(gw), float(gh))
        centers = self._handle_centers()
        handle_w = self._current_handle_width()
        handle_h = float(self.style.active_handle_height)
        if self._orientation is Orientation.VERTICAL:
            handle_w, handle_h = handle_h, handle_w

        for idx, (cx, cy) in enumerate(centers):
            half_w = handle_w / 2.0 + 6.0
            half_h = handle_h / 2.0 + 6.0
            if (cx - half_w) <= x <= (cx + half_w) and (cy - half_h) <= y <= (cy + half_h):
                self._active_handle_index = idx
                return True
        return False

    def _current_handle_width(self) -> float:
        if self.state.focused or self.state.pressed or self.state.dragging:
            return float(self.style.handle_width_focused)
        return float(self.style.handle_width)

    def on_key_event(self, key: str, modifiers: int = 0) -> bool:
        if self.disabled:
            return False

        key_name = (key or "").lower()
        if key_name == "space":
            self._space_accel_armed = True
            return True

        inc = key_name in ("right", "up")
        dec = key_name in ("left", "down")
        if not inc and not dec:
            self._space_accel_armed = False
            return super().on_key_event(key, modifiers)

        step = self._keyboard_step(modifiers, large=self._space_accel_armed)
        delta = step if inc else -step
        self._step_active_handle(delta)
        self._space_accel_armed = False
        return True

    def _keyboard_step(self, modifiers: int, *, large: bool = False) -> float:
        span = max(1e-6, self._max_value - self._min_value)
        if self._stops is not None and self._stops >= 2:
            unit = span / float(max(1, self._stops - 1))
        else:
            unit = span * 0.01

        if large:
            unit *= 10.0

        if modifiers & MOD_SHIFT:
            unit *= 10.0
        return unit

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        w_dim = self.width_sizing
        h_dim = self.height_sizing
        default_cross = int(math.ceil(self._cross_axis_size(self.style)))

        width = (
            int(w_dim.value) if w_dim.kind == "fixed" else (int(max_width) if max_width is not None else default_cross)
        )
        height = (
            int(h_dim.value)
            if h_dim.kind == "fixed"
            else (int(max_height) if max_height is not None else default_cross)
        )

        l, t, r, b = self.padding
        return (int(width) + l + r, int(height) + t + b)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        try:
            from nuiitivet.material.theme.color_role import ColorRole
            from nuiitivet.material.theme.theme_data import MaterialThemeData
            from nuiitivet.rendering.skia import draw_oval, draw_round_rect, make_paint, make_rect, skcolor
            from nuiitivet.theme import manager as theme_manager

            self.set_last_rect(x, y, width, height)
            self._compute_geometry(float(x), float(y), float(width), float(height))

            style = self.style
            theme = theme_manager.current.extension(MaterialThemeData)
            roles = theme.roles if theme is not None else {}

            active_track_hex = roles.get(ColorRole.PRIMARY, "#000000")
            inactive_track_hex = roles.get(ColorRole.SECONDARY_CONTAINER, "#9E9E9E")
            handle_hex = roles.get(ColorRole.PRIMARY, "#000000")
            active_stop_hex = roles.get(ColorRole.ON_PRIMARY, "#FFFFFF")
            inactive_stop_hex = roles.get(ColorRole.ON_SECONDARY_CONTAINER, "#000000")

            if self.disabled:
                active_track_hex = roles.get(ColorRole.ON_SURFACE, "#000000")
                inactive_track_hex = roles.get(ColorRole.ON_SURFACE, "#000000")
                handle_hex = roles.get(ColorRole.ON_SURFACE, "#000000")

            track_radius = min(self._track_h, self._track_w) / 2.0
            track_rect = make_rect(self._track_x, self._track_y, self._track_w, self._track_h)
            if track_rect is not None:
                inactive_alpha = style.disabled_inactive_track_alpha if self.disabled else 1.0
                inactive_paint = make_paint(color=skcolor(inactive_track_hex, inactive_alpha), style="fill", aa=True)
                if inactive_paint is not None:
                    draw_round_rect(canvas, track_rect, track_radius, inactive_paint)

            active_start, active_end = self._active_range_ratio()
            if active_end < active_start:
                active_start, active_end = active_end, active_start
            if active_end > active_start:
                active_rect = self._active_track_rect(active_start, active_end)
                if active_rect is not None:
                    active_alpha = style.disabled_active_track_alpha if self.disabled else 1.0
                    active_paint = make_paint(color=skcolor(active_track_hex, active_alpha), style="fill", aa=True)
                    if active_paint is not None:
                        draw_round_rect(canvas, active_rect, track_radius, active_paint)

            if self._stops is not None and self._stops >= 2:
                steps = max(2, int(self._stops))
                centers = self._handle_centers()
                gap = float(style.stop_indicator_trailing_space)
                stop_r = float(style.stop_indicator_size) / 2.0
                for idx in range(steps):
                    ratio = float(idx) / float(steps - 1)
                    sx, sy = self._point_on_track(ratio)
                    near_handle = any(abs(sx - hx) < gap and abs(sy - hy) < gap for hx, hy in centers)
                    if near_handle:
                        continue
                    stop_rect = make_rect(sx - stop_r, sy - stop_r, stop_r * 2.0, stop_r * 2.0)
                    if stop_rect is None:
                        continue
                    color = active_stop_hex if active_start <= ratio <= active_end else inactive_stop_hex
                    stop_paint = make_paint(color=skcolor(color, 1.0), style="fill", aa=True)
                    if stop_paint is not None:
                        draw_oval(canvas, stop_rect, stop_paint)

            layer_alpha = self._get_active_state_layer_opacity()
            centers = self._handle_centers()
            if centers:
                active_index = max(0, min(self._active_handle_index, len(centers) - 1))
                cx, cy = centers[active_index]

                if layer_alpha > 0.0:
                    layer_size = float(style.state_layer_size)
                    layer_rect = make_rect(cx - layer_size / 2.0, cy - layer_size / 2.0, layer_size, layer_size)
                    if layer_rect is not None:
                        layer_color = roles.get(ColorRole.PRIMARY, "#000000")
                        layer_paint = make_paint(color=skcolor(layer_color, layer_alpha), style="fill", aa=True)
                        if layer_paint is not None:
                            draw_oval(canvas, layer_rect, layer_paint)

                handle_w = self._current_handle_width()
                handle_h = float(style.active_handle_height)
                if self._orientation is Orientation.VERTICAL:
                    handle_w, handle_h = handle_h, handle_w

                for hx, hy in centers:
                    handle_rect = make_rect(hx - handle_w / 2.0, hy - handle_h / 2.0, handle_w, handle_h)
                    if handle_rect is None:
                        continue
                    handle_alpha = style.disabled_handle_alpha if self.disabled else 1.0
                    handle_paint = make_paint(color=skcolor(handle_hex, handle_alpha), style="fill", aa=True)
                    if handle_paint is not None:
                        draw_round_rect(canvas, handle_rect, min(handle_w, handle_h) / 2.0, handle_paint)

                if self.should_show_focus_ring:
                    focus_stroke = max(1.0, float(style.focus_stroke_ratio) * 48.0)
                    focus_offset = float(style.focus_offset_ratio) * 48.0
                    focus_size = float(style.state_layer_size) + (focus_offset * 2.0)
                    focus_rect = make_rect(cx - focus_size / 2.0, cy - focus_size / 2.0, focus_size, focus_size)
                    if focus_rect is not None:
                        focus_color = roles.get(ColorRole.PRIMARY, "#000000")
                        focus_paint = make_paint(
                            color=skcolor(focus_color, style.focus_alpha),
                            style="stroke",
                            stroke_width=focus_stroke,
                            aa=True,
                        )
                        if focus_paint is not None:
                            draw_oval(canvas, focus_rect, focus_paint)

                if self._show_value_indicator and self.state.dragging:
                    active_value = self._active_value_for_indicator()
                    self._draw_value_indicator(canvas, cx, cy, active_value)
        except Exception:
            exception_once(_logger, "slider_paint_exc", "Slider paint raised")

    def _draw_value_indicator(self, canvas, cx: float, cy: float, value: float) -> None:
        from nuiitivet.material.theme.color_role import ColorRole
        from nuiitivet.material.theme.theme_data import MaterialThemeData
        from nuiitivet.rendering.skia import (
            draw_round_rect,
            get_typeface,
            make_font,
            make_paint,
            make_rect,
            make_text_blob,
            measure_text_ink_bounds,
            skcolor,
        )
        from nuiitivet.theme import manager as theme_manager

        style = self.style
        theme = theme_manager.current.extension(MaterialThemeData)
        roles = theme.roles if theme is not None else {}

        bg_hex = roles.get(ColorRole.SURFACE, "#1F1F1F")
        text_hex = roles.get(ColorRole.ON_SURFACE, "#FFFFFF")

        bubble_w = float(style.value_indicator_width)
        bubble_h = float(style.value_indicator_height)
        bubble_r = bubble_h / 2.0
        bottom_gap = float(style.value_indicator_bottom_space)

        bx = cx - (bubble_w / 2.0)
        by = cy - (bubble_h + bottom_gap)

        bubble_rect = make_rect(bx, by, bubble_w, bubble_h)
        if bubble_rect is None:
            return

        bubble_paint = make_paint(color=skcolor(bg_hex, 1.0), style="fill", aa=True)
        if bubble_paint is None:
            return

        draw_round_rect(canvas, bubble_rect, bubble_r, bubble_paint)

        label = self._format_value_label(value)
        tf = get_typeface(fallback_to_default=True)
        if tf is None:
            return

        font_size = max(12, int(round(bubble_h * 0.38)))
        font = make_font(tf, font_size)
        if font is None:
            return

        blob = make_text_blob(label, font)
        if blob is None:
            return

        ink_left, ink_top, ink_right, ink_bottom = measure_text_ink_bounds(tf, font_size, label)
        ink_w = max(0.0, float(ink_right) - float(ink_left))
        ink_h = max(0.0, float(ink_bottom) - float(ink_top))

        tx = bx + (bubble_w - ink_w) / 2.0 - float(ink_left)
        ty = by + (bubble_h - ink_h) / 2.0 - float(ink_top)

        text_paint = make_paint(color=skcolor(text_hex, 1.0), style="fill", aa=True)
        if text_paint is None:
            return

        canvas.drawTextBlob(blob, tx, ty, text_paint)

    def _compute_geometry(self, x: float, y: float, width: float, height: float) -> None:
        cx, cy, cw, ch = self.content_rect(int(x), int(y), int(width), int(height))
        style = self.style
        track_thickness = min(
            float(style.active_track_height),
            float(ch) if self._orientation is Orientation.HORIZONTAL else float(cw),
        )

        if self._orientation is Orientation.HORIZONTAL:
            self._track_w = max(1.0, float(cw))
            self._track_h = max(1.0, track_thickness)
            self._track_x = float(cx)
            self._track_y = float(cy) + (float(ch) - self._track_h) / 2.0
            self._track_start = self._track_x
            self._track_end = self._track_x + self._track_w
        else:
            self._track_w = max(1.0, track_thickness)
            self._track_h = max(1.0, float(ch))
            self._track_x = float(cx) + (float(cw) - self._track_w) / 2.0
            self._track_y = float(cy)
            self._track_start = self._track_y
            self._track_end = self._track_y + self._track_h

    def _point_on_track(self, ratio: float) -> Tuple[float, float]:
        ratio = _clamp(ratio, 0.0, 1.0)
        if self._orientation is Orientation.HORIZONTAL:
            return (
                self._track_start + ((self._track_end - self._track_start) * ratio),
                self._track_y + self._track_h / 2.0,
            )
        return (
            self._track_x + self._track_w / 2.0,
            self._track_start + ((self._track_end - self._track_start) * ratio),
        )

    def _active_track_rect(self, start_ratio: float, end_ratio: float):
        from nuiitivet.rendering.skia import make_rect

        sx, sy = self._point_on_track(start_ratio)
        ex, ey = self._point_on_track(end_ratio)
        if self._orientation is Orientation.HORIZONTAL:
            return make_rect(min(sx, ex), self._track_y, abs(ex - sx), self._track_h)
        return make_rect(self._track_x, min(sy, ey), self._track_w, abs(ey - sy))

    def _pick_handle_index(self, event: PointerEvent) -> int:
        centers = self._handle_centers()
        if len(centers) <= 1:
            return 0
        axis_value = event.x if self._orientation is Orientation.HORIZONTAL else event.y
        distances = [
            abs((cx if self._orientation is Orientation.HORIZONTAL else cy) - axis_value) for cx, cy in centers
        ]
        return 0 if distances[0] <= distances[1] else 1

    def _format_value_label(self, value: float) -> str:
        if abs(value - round(value)) < 1e-6:
            return str(int(round(value)))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _update_value_from_ratio(self, ratio: float, *, from_track: bool) -> None:
        raise NotImplementedError

    def _step_active_handle(self, delta: float) -> None:
        raise NotImplementedError

    def _handle_centers(self) -> Sequence[Tuple[float, float]]:
        raise NotImplementedError

    def _active_range_ratio(self) -> Tuple[float, float]:
        raise NotImplementedError

    def _active_value_for_indicator(self) -> float:
        raise NotImplementedError


class Slider(_SliderBase):
    """Material Design 3 Slider widget."""

    def __init__(
        self,
        value: float | ObservableProtocol[float] = 0.0,
        *,
        on_change: Optional[Callable[[float], None]] = None,
        min_value: float = 0.0,
        max_value: float = 1.0,
        stops: Optional[int] = None,
        show_value_indicator: bool = False,
        disabled: bool | ObservableProtocol[bool] = False,
        orientation: Orientation = Orientation.HORIZONTAL,
        length: SizingLike = "1fr",
        padding: Optional[Tuple[int, int] | Tuple[int, int, int, int] | int] = None,
        style=None,
    ) -> None:
        """Initialize Slider.

        Args:
            value: Current slider value or observable value.
            on_change: Callback invoked when value changes.
            min_value: Minimum value.
            max_value: Maximum value.
            stops: Discrete stop count. ``None`` means continuous.
            show_value_indicator: Whether to show value indicator during drag.
            disabled: Disabled state.
            orientation: Slider orientation.
            length: Axis length sizing.
            padding: Slider padding.
            style: Optional SliderStyle override.
        """
        self._on_change = on_change
        self._value_external: ObservableProtocol[float] | None = None

        if hasattr(value, "subscribe") and hasattr(value, "value"):
            self._value_external = cast("ObservableProtocol[float]", value)
            initial = float(self._value_external.value)
        else:
            initial = float(value)

        self._value = _clamp(initial, float(min_value), float(max_value))

        super().__init__(
            min_value=min_value,
            max_value=max_value,
            stops=stops,
            show_value_indicator=show_value_indicator,
            disabled=disabled,
            orientation=orientation,
            length=length,
            padding=padding,
            style=style,
        )

    def on_mount(self) -> None:
        super().on_mount()
        if self._value_external is not None:
            self.observe(self._value_external, lambda _v: self._sync_from_external())
            self._sync_from_external()

    def _sync_from_external(self) -> None:
        if self._value_external is None:
            return
        next_value = _clamp(float(self._value_external.value), self._min_value, self._max_value)
        if abs(next_value - self._value) <= 1e-9:
            return
        self._value = next_value
        self.invalidate()

    @property
    def value(self) -> float:
        return float(self._value_external.value) if self._value_external is not None else float(self._value)

    @value.setter
    def value(self, new_value: float) -> None:
        next_value = _clamp(float(new_value), self._min_value, self._max_value)
        if self._stops is not None and self._stops >= 2:
            next_value = self._ratio_to_value(self._value_to_ratio(next_value))
        if self._value_external is not None:
            self._value_external.value = next_value
        self._value = next_value
        self.invalidate()

    def _update_value_from_ratio(self, ratio: float, *, from_track: bool) -> None:
        del from_track
        next_value = self._ratio_to_value(ratio)
        if abs(next_value - self.value) <= 1e-9:
            return
        self.value = next_value
        if self._on_change is not None:
            self._on_change(next_value)

    def _step_active_handle(self, delta: float) -> None:
        self.value = self.value + delta
        if self._on_change is not None:
            self._on_change(self.value)

    def _handle_centers(self) -> Sequence[Tuple[float, float]]:
        return [self._point_on_track(self._value_to_ratio(self.value))]

    def _active_range_ratio(self) -> Tuple[float, float]:
        return (0.0, self._value_to_ratio(self.value))

    def _active_value_for_indicator(self) -> float:
        return self.value


class CenteredSlider(Slider):
    """Material Design 3 Centered Slider widget."""

    def __init__(
        self,
        value: float | ObservableProtocol[float] = 0.0,
        *,
        on_change: Optional[Callable[[float], None]] = None,
        min_value: float = -1.0,
        max_value: float = 1.0,
        stops: Optional[int] = None,
        show_value_indicator: bool = False,
        disabled: bool | ObservableProtocol[bool] = False,
        orientation: Orientation = Orientation.HORIZONTAL,
        length: SizingLike = "1fr",
        padding: Optional[Tuple[int, int] | Tuple[int, int, int, int] | int] = None,
        style=None,
    ) -> None:
        super().__init__(
            value=value,
            on_change=on_change,
            min_value=min_value,
            max_value=max_value,
            stops=stops,
            show_value_indicator=show_value_indicator,
            disabled=disabled,
            orientation=orientation,
            length=length,
            padding=padding,
            style=style,
        )

    def _active_range_ratio(self) -> Tuple[float, float]:
        center = self._value_to_ratio(0.0)
        current = self._value_to_ratio(self.value)
        return (center, current)


class RangeSlider(_SliderBase):
    """Material Design 3 Range Slider widget."""

    def __init__(
        self,
        value_start: float | ObservableProtocol[float] = 0.0,
        value_end: float | ObservableProtocol[float] = 1.0,
        *,
        on_change: Optional[Callable[[Tuple[float, float]], None]] = None,
        min_value: float = 0.0,
        max_value: float = 1.0,
        stops: Optional[int] = None,
        show_value_indicator: bool = False,
        disabled: bool | ObservableProtocol[bool] = False,
        orientation: Orientation = Orientation.HORIZONTAL,
        length: SizingLike = "1fr",
        padding: Optional[Tuple[int, int] | Tuple[int, int, int, int] | int] = None,
        style=None,
    ) -> None:
        """Initialize RangeSlider.

        Args:
            value_start: Start value or observable value.
            value_end: End value or observable value.
            on_change: Callback invoked when range changes.
            min_value: Minimum value.
            max_value: Maximum value.
            stops: Discrete stop count. ``None`` means continuous.
            show_value_indicator: Whether to show value indicator during drag.
            disabled: Disabled state.
            orientation: Slider orientation.
            length: Axis length sizing.
            padding: Slider padding.
            style: Optional SliderStyle override.
        """
        self._on_change = on_change

        self._value_start_external: ObservableProtocol[float] | None = None
        self._value_end_external: ObservableProtocol[float] | None = None

        if hasattr(value_start, "subscribe") and hasattr(value_start, "value"):
            self._value_start_external = cast("ObservableProtocol[float]", value_start)
            start_initial = float(self._value_start_external.value)
        else:
            start_initial = float(value_start)

        if hasattr(value_end, "subscribe") and hasattr(value_end, "value"):
            self._value_end_external = cast("ObservableProtocol[float]", value_end)
            end_initial = float(self._value_end_external.value)
        else:
            end_initial = float(value_end)

        s0 = _clamp(start_initial, float(min_value), float(max_value))
        e0 = _clamp(end_initial, float(min_value), float(max_value))
        self._value_start = min(s0, e0)
        self._value_end = max(s0, e0)

        super().__init__(
            min_value=min_value,
            max_value=max_value,
            stops=stops,
            show_value_indicator=show_value_indicator,
            disabled=disabled,
            orientation=orientation,
            length=length,
            padding=padding,
            style=style,
        )

    def on_mount(self) -> None:
        super().on_mount()
        if self._value_start_external is not None:
            self.observe(self._value_start_external, lambda _v: self._sync_from_external())
        if self._value_end_external is not None:
            self.observe(self._value_end_external, lambda _v: self._sync_from_external())
        self._sync_from_external()

    def _sync_from_external(self) -> None:
        s = self._value_start
        e = self._value_end

        if self._value_start_external is not None:
            s = _clamp(float(self._value_start_external.value), self._min_value, self._max_value)
        if self._value_end_external is not None:
            e = _clamp(float(self._value_end_external.value), self._min_value, self._max_value)

        s, e = min(s, e), max(s, e)
        if abs(s - self._value_start) <= 1e-9 and abs(e - self._value_end) <= 1e-9:
            return

        self._value_start = s
        self._value_end = e
        self.invalidate()

    @property
    def value_start(self) -> float:
        if self._value_start_external is not None:
            return float(self._value_start_external.value)
        return float(self._value_start)

    @value_start.setter
    def value_start(self, new_value: float) -> None:
        s = _clamp(float(new_value), self._min_value, self._max_value)
        if self._stops is not None and self._stops >= 2:
            s = self._ratio_to_value(self._value_to_ratio(s))
        e = self.value_end
        s = min(s, e)
        self._value_start = s
        if self._value_start_external is not None:
            self._value_start_external.value = s
        self.invalidate()

    @property
    def value_end(self) -> float:
        if self._value_end_external is not None:
            return float(self._value_end_external.value)
        return float(self._value_end)

    @value_end.setter
    def value_end(self, new_value: float) -> None:
        e = _clamp(float(new_value), self._min_value, self._max_value)
        if self._stops is not None and self._stops >= 2:
            e = self._ratio_to_value(self._value_to_ratio(e))
        s = self.value_start
        e = max(s, e)
        self._value_end = e
        if self._value_end_external is not None:
            self._value_end_external.value = e
        self.invalidate()

    def _update_value_from_ratio(self, ratio: float, *, from_track: bool) -> None:
        del from_track
        next_value = self._ratio_to_value(ratio)
        if self._active_handle_index == 0:
            prev = self.value_start
            self.value_start = min(next_value, self.value_end)
            changed = abs(self.value_start - prev) > 1e-9
        else:
            prev = self.value_end
            self.value_end = max(next_value, self.value_start)
            changed = abs(self.value_end - prev) > 1e-9

        if changed and self._on_change is not None:
            self._on_change((self.value_start, self.value_end))

    def _step_active_handle(self, delta: float) -> None:
        if self._active_handle_index == 0:
            self.value_start = self.value_start + delta
        else:
            self.value_end = self.value_end + delta
        if self._on_change is not None:
            self._on_change((self.value_start, self.value_end))

    def _handle_centers(self) -> Sequence[Tuple[float, float]]:
        return [
            self._point_on_track(self._value_to_ratio(self.value_start)),
            self._point_on_track(self._value_to_ratio(self.value_end)),
        ]

    def _active_range_ratio(self) -> Tuple[float, float]:
        return (self._value_to_ratio(self.value_start), self._value_to_ratio(self.value_end))

    def _active_value_for_indicator(self) -> float:
        if self._active_handle_index == 0:
            return self.value_start
        return self.value_end


__all__ = ["Orientation", "Slider", "CenteredSlider", "RangeSlider"]
