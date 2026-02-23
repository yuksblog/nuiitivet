"""Material Design 3 Selection Controls.

This module contains the implementation of Material Design 3 selection controls:
- Checkbox
- RadioButton / RadioGroup
- Switch
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional, Tuple, Union, cast

from nuiitivet.animation import Animatable, LinearMotion
from nuiitivet.common.logging_once import exception_once
from nuiitivet.layout.container import Container
from nuiitivet.observable import Observable, ObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgets.toggleable import Toggleable
from nuiitivet.material.interactive_widget import InteractiveWidget

if TYPE_CHECKING:
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle
    from nuiitivet.material.styles.radio_button_style import RadioButtonStyle
    from nuiitivet.material.styles.switch_style import SwitchStyle


_logger = logging.getLogger(__name__)

_STATE_LAYER_MOTION = LinearMotion(0.1)
_SELECTION_MOTION = LinearMotion(0.12)


class Checkbox(Toggleable, InteractiveWidget):
    """A minimal Material-like Checkbox widget (M3).

    Parameters:
    - checked: Checked state source (bool / Observable[bool] / Observable[Optional[bool]])
    - on_toggle: Callback when toggled
    - size: Touch target size (default 48dp, M3 recommendation)
    - padding: Space around the checkbox (M3: "space between UI elements")
    - indeterminate: Indeterminate flag (bool / Observable[bool])
    - disabled: Disable interaction (bool / Observable[bool])
    - style: CheckboxStyle for visual customization (defaults to theme style)
    """

    def __init__(
        self,
        checked: bool | ObservableProtocol[bool] | ObservableProtocol[Optional[bool]] = False,
        *,
        on_toggle: Optional[Callable[[Optional[bool]], None]] = None,
        indeterminate: bool | ObservableProtocol[bool] = False,
        disabled: bool | ObservableProtocol[bool] = False,
        size: SizingLike = 48,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["CheckboxStyle"] = None,
    ):
        self._checked_external_tri: ObservableProtocol[Optional[bool]] | None = None
        self._checked_external_bool: ObservableProtocol[bool] | None = None
        self._indeterminate_external: ObservableProtocol[bool] | None = None

        checked_is_obs = hasattr(checked, "subscribe") and hasattr(checked, "value")
        indeterminate_is_obs = hasattr(indeterminate, "subscribe") and hasattr(indeterminate, "value")

        if checked_is_obs and not (indeterminate_is_obs or bool(indeterminate)):
            self._checked_external_tri = cast("ObservableProtocol[Optional[bool]]", checked)
        elif checked_is_obs:
            self._checked_external_bool = cast("ObservableProtocol[bool]", checked)

        if indeterminate_is_obs:
            self._indeterminate_external = cast("ObservableProtocol[bool]", indeterminate)

        # Determine initial value for Toggleable (internal state is the render source-of-truth)
        value: Optional[bool]
        if self._checked_external_tri is not None:
            value = self._checked_external_tri.value
        else:
            if self._checked_external_bool is not None:
                base_checked = bool(self._checked_external_bool.value)
            else:
                base_checked = bool(checked)

            if self._indeterminate_external is not None:
                is_indeterminate = bool(self._indeterminate_external.value)
            else:
                is_indeterminate = bool(indeterminate)

            value = None if is_indeterminate else base_checked

        # Store style (use provided or get from theme lazily)
        self._style = style

        # Resolve padding
        final_padding = padding
        if final_padding is None:
            if style is not None:
                final_padding = style.padding
            else:
                final_padding = 0

        # Initialize Toggleable
        super().__init__(
            value=value,
            on_change=on_toggle,
            tristate=False,  # Checkbox does not cycle to indeterminate
            disabled=disabled,
            width=size,
            height=size,
            padding=final_padding,
        )

        # If padding was None and style was None, we might need to update padding from theme later.
        # We can do this in on_mount or similar if we want full theme support for padding.
        self._user_padding = padding

        # Parse size for M3 touch target
        try:
            from nuiitivet.rendering.sizing import parse_sizing

            parsed = parse_sizing(size, default=None)
            if parsed.kind == "fixed":
                self._touch_target_size = int(parsed.value)
            elif parsed.kind in ("flex", "auto"):
                # Checkbox cannot resolve flex/auto without parent context
                self._touch_target_size = 48
            else:
                # Last resort: try numeric coercion
                self._touch_target_size = int(cast(int, size))
        except Exception:
            exception_once(_logger, "checkbox_size_exc", "Failed to parse checkbox size")
            self._touch_target_size = 48

        initial_selection = 1.0 if self.value is True or self.value is None else 0.0
        self._state_layer_anim: Animatable[float] = Animatable(0.0, motion=_STATE_LAYER_MOTION)
        self.bind(self._state_layer_anim.subscribe(lambda _: self.invalidate()))
        self._selection_anim: Animatable[float] = Animatable(initial_selection, motion=_SELECTION_MOTION)
        self.bind(self._selection_anim.subscribe(lambda _: self.invalidate()))

    def _effective_value_from_external(self) -> Optional[bool]:
        if self._checked_external_tri is not None:
            return self._checked_external_tri.value

        checked_value = self.value
        if self._checked_external_bool is not None:
            checked_value = bool(self._checked_external_bool.value)

        if self._indeterminate_external is not None:
            is_indeterminate = bool(self._indeterminate_external.value)
        else:
            is_indeterminate = False

        return None if is_indeterminate else bool(checked_value)

    def _sync_from_external(self) -> None:
        if (
            self._checked_external_tri is None
            and self._checked_external_bool is None
            and self._indeterminate_external is None
        ):
            return

        try:
            next_value = self._effective_value_from_external()
        except Exception:
            return

        if self.value is next_value:
            return

        self.value = next_value

    def on_mount(self) -> None:
        super().on_mount()

        if self._checked_external_tri is not None:
            self.observe(self._checked_external_tri, lambda _v: self._sync_from_external())
        if self._checked_external_bool is not None:
            self.observe(self._checked_external_bool, lambda _v: self._sync_from_external())
        if self._indeterminate_external is not None:
            self.observe(self._indeterminate_external, lambda _v: self._sync_from_external())

        self._sync_from_external()

        # If padding was not provided by user, update it from theme style
        if self._user_padding is None and self._style is None:
            try:
                style = self.style  # This resolves from theme
                if style.padding != 0:
                    self.padding = style.padding
                    self.invalidate()
            except Exception:
                pass

    def _get_state_layer_target_opacity(self) -> float:
        state = self.state
        if state.dragging:
            return float(self._DRAG_OPACITY)
        if state.pressed:
            return float(self._PRESS_OPACITY)
        if state.hovered:
            return float(self._HOVER_OPACITY)
        return 0.0

    def _get_active_state_layer_opacity(self) -> float:
        target = self._get_state_layer_target_opacity()
        if abs(self._state_layer_anim.target - target) > 1e-6:
            self._state_layer_anim.target = target
        return float(self._state_layer_anim.value)

    def _get_selection_target(self) -> float:
        return 1.0 if self.value is True or self.value is None else 0.0

    def _get_selection_progress(self) -> float:
        target = self._get_selection_target()
        if abs(self._selection_anim.target - target) > 1e-6:
            self._selection_anim.target = target
        return float(self._selection_anim.value)

    def _handle_click(self) -> None:
        if self.disabled:
            return

        current = self.value

        # Tri-state value source.
        if self._checked_external_tri is not None:
            if current is None:
                new_val: Optional[bool] = True
            else:
                new_val = not bool(current)

            try:
                self._checked_external_tri.value = new_val
            except Exception:
                pass

            self.value = new_val
            if self.on_change:
                self.on_change(new_val)
            return

        # Separate checked/indeterminate sources.
        if self._checked_external_bool is not None or self._indeterminate_external is not None:
            is_indeterminate = current is None
            if self._indeterminate_external is not None:
                try:
                    is_indeterminate = bool(self._indeterminate_external.value)
                except Exception:
                    pass

            if is_indeterminate:
                next_checked = True
                next_indeterminate = False
            else:
                next_checked = not bool(current)
                next_indeterminate = False

            if self._indeterminate_external is not None:
                try:
                    self._indeterminate_external.value = next_indeterminate
                except Exception:
                    pass

            if self._checked_external_bool is not None:
                try:
                    self._checked_external_bool.value = next_checked
                except Exception:
                    pass

            new_val = None if next_indeterminate else bool(next_checked)
            self.value = new_val
            if self.on_change:
                self.on_change(new_val)
            return

        # Local state.
        super()._handle_click()

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred size including padding (M3準拠)."""
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            width = self._touch_target_size

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = self._touch_target_size

        l, t, r, b = self.padding
        total_w = width + l + r
        total_h = height + t + b

        if max_width is not None:
            total_w = min(int(total_w), int(max_width))
        if max_height is not None:
            total_h = min(int(total_h), int(max_height))

        return (int(total_w), int(total_h))

    @property
    def style(self):
        if self._style is not None:
            return self._style
        from nuiitivet.theme.manager import manager
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme = manager.current.extension(MaterialThemeData)
        if theme is None:
            raise ValueError("MaterialThemeData not found in current theme")
        return theme.checkbox_style

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """Paint checkbox with padding support (M3準拠)."""
        try:
            from nuiitivet.rendering.skia import (
                draw_oval,
                draw_round_rect,
                make_paint,
                make_path,
                make_rect,
                path_line_to,
                path_move_to,
                skcolor,
            )

            content_x, content_y, content_w, content_h = self.content_rect(x, y, width, height)
            touch_sz = min(content_w, content_h)
            if touch_sz <= 0:
                return

            cx = content_x + (content_w - touch_sz) // 2
            cy = content_y + (content_h - touch_sz) // 2

            self.set_last_rect(x, y, width, height)

            sizes = self.style.compute_sizes(touch_sz)
            icon_sz = sizes["icon_size"]
            corner = sizes["corner_radius"]
            stroke_w = sizes["stroke_width"]
            state_diam = sizes["state_layer_size"]

            icon_x = cx + (touch_sz - icon_sz) // 2
            icon_y = cy + (touch_sz - icon_sz) // 2

            focus_stroke = max(1.0, float(3.0 * (touch_sz / 48.0)))
            focus_offset = float(2.0 * (touch_sz / 48.0))

            from nuiitivet.theme import manager as theme_manager
            from nuiitivet.material.theme.color_role import ColorRole
            from nuiitivet.material.theme.theme_data import MaterialThemeData

            mat = theme_manager.current.extension(MaterialThemeData)
            roles = mat.roles if mat is not None else {}

            fg_hex = roles.get(ColorRole.ON_SURFACE, "#000000")
            stroke_color = skcolor(fg_hex, 0.54)
            stroke_p = make_paint(color=stroke_color, style="stroke", stroke_width=stroke_w, aa=True)
            rect = make_rect(icon_x, icon_y, icon_sz, icon_sz)

            # Check for keyboard focus (Ring visible)
            is_keyboard_focus = self.should_show_focus_ring

            # Determine State Layer opacity
            overlay_alpha = self._get_active_state_layer_opacity()

            if overlay_alpha > 0.0:
                cx_center = float(cx + touch_sz / 2.0)
                cy_center = float(cy + touch_sz / 2.0)
                r = float(state_diam / 2.0)

                # State Layer color (Checked=Primary, Unchecked=OnSurface)
                is_checked = self.value is True or self.value is None
                base_color_role = ColorRole.PRIMARY if is_checked else ColorRole.ON_SURFACE
                base_color = roles.get(base_color_role, "#000000")

                ov = skcolor(base_color, overlay_alpha)
                p_ov = make_paint(color=ov, style="fill", aa=True)
                try:
                    canvas.drawCircle(cx_center, cy_center, r, p_ov)
                except Exception:
                    draw_oval(canvas, make_rect(cx_center - r, cy_center - r, state_diam, state_diam), p_ov)

            if rect is not None and stroke_p is not None:
                draw_round_rect(canvas, rect, corner, stroke_p)

            if is_keyboard_focus:
                focus_alpha = 0.12
                prim = roles.get(ColorRole.PRIMARY, "#000000")
                focus_col = skcolor(prim, focus_alpha)
                focus_p = make_paint(color=focus_col, style="stroke", stroke_width=focus_stroke, aa=True)
                try:
                    radius = float(state_diam / 2.0 + focus_offset + (focus_stroke / 2.0))
                    canvas.drawCircle(
                        cx + touch_sz / 2.0,
                        cy + touch_sz / 2.0,
                        radius,
                        focus_p,
                    )
                except Exception:
                    ox = cx + touch_sz / 2.0 - (state_diam / 2.0 + 4.0)
                    oy = cy + touch_sz / 2.0 - (state_diam / 2.0 + 4.0)
                    side = state_diam + 8.0
                    draw_oval(canvas, make_rect(ox, oy, side, side), focus_p)

            val = self.value
            selection_progress = self._get_selection_progress()
            if selection_progress > 1e-6:
                prim = roles.get(ColorRole.PRIMARY, "#000000")
                fill_p = make_paint(color=skcolor(prim, selection_progress), style="fill", aa=True)
                if rect is not None and fill_p is not None:
                    draw_round_rect(canvas, rect, corner, fill_p)

            # Secondary overlay check (legacy or box-specific?)
            # We use the same opacity logic
            overlay_alpha_box = overlay_alpha

            if overlay_alpha_box and overlay_alpha_box > 0.0:
                base = "#000000" if self.state.pressed else "#FFFFFF"
                ov = skcolor(base, overlay_alpha_box)
                p_ov = make_paint(color=ov, style="fill", aa=True)
                if rect is not None and p_ov is not None:
                    draw_round_rect(canvas, rect, corner, p_ov)

            if (val is True or val is None) and selection_progress > 1e-6:
                mark_is_none = val is None
                mark_style = "stroke" if not mark_is_none else "fill"
                onp = roles.get(ColorRole.ON_PRIMARY, "#000000")
                mark_p = make_paint(
                    color=skcolor(onp, selection_progress),
                    style=mark_style,
                    stroke_width=max(1.0, icon_sz * 0.12),
                    aa=True,
                )
                if mark_p is None:
                    return

                if mark_is_none:
                    bar_w = icon_sz * 0.5
                    bar_h = max(1.0, icon_sz * 0.12)
                    bx = icon_x + (icon_sz - bar_w) / 2.0
                    by = icon_y + (icon_sz - bar_h) / 2.0
                    r_bar = make_rect(bx, by, bar_w, bar_h)
                    if r_bar is not None:
                        canvas.drawRect(r_bar, mark_p)
                else:
                    x1 = icon_x + icon_sz * 0.18
                    y1 = icon_y + icon_sz * 0.52
                    x2 = icon_x + icon_sz * 0.42
                    y2 = icon_y + icon_sz * 0.72
                    x3 = icon_x + icon_sz * 0.78
                    y3 = icon_y + icon_sz * 0.30
                    try:
                        canvas.drawLine(x1, y1, x2, y2, mark_p)
                        canvas.drawLine(x2, y2, x3, y3, mark_p)
                    except Exception:
                        path = make_path()
                        if path_move_to(path, x1, y1) and path_line_to(path, x2, y2) and path_line_to(path, x3, y3):
                            canvas.drawPath(path, mark_p)
        except Exception:
            exception_once(_logger, "checkbox_paint_exc", "Checkbox paint raised")
            return


class RadioGroup(Container):
    """Container that manages a single selected value for descendant RadioButtons."""

    def __init__(
        self,
        child: Widget,
        *,
        value: object | ObservableProtocol[object | None] | None = None,
        on_change: Optional[Callable[[object | None], None]] = None,
    ) -> None:
        """Initialize RadioGroup.

        Args:
            child: Root child subtree that contains radio options.
            value: Selected value or external observable selected value.
            on_change: Callback invoked when selection changes.
        """
        if not isinstance(child, Widget):
            raise TypeError(f"child must be Widget, got {type(child)}")
        super().__init__(child=child)

        self._value_external: ObservableProtocol[object | None] | None = None
        if hasattr(value, "subscribe") and hasattr(value, "value"):
            self._value_external = cast("ObservableProtocol[object | None]", value)
            initial_value = self._value_external.value
        else:
            initial_value = value

        self._value_internal: Observable[object | None] = Observable(initial_value)
        self._on_change = on_change

    @property
    def value(self) -> object | None:
        """Current selected value."""
        if self._value_external is not None:
            return self._value_external.value
        return self._value_internal.value

    @value.setter
    def value(self, new_value: object | None) -> None:
        self._set_value(new_value, emit=False)

    def on_mount(self) -> None:
        super().on_mount()
        if self._value_external is not None:
            self.observe(self._value_external, lambda _v: self._invalidate_descendant_radios())

    def select(self, new_value: object | None) -> None:
        """Select a new value and notify listeners."""
        self._set_value(new_value, emit=True)

    def _set_value(self, new_value: object | None, *, emit: bool) -> None:
        if self.value == new_value:
            return

        if self._value_external is not None:
            self._value_external.value = new_value
        else:
            self._value_internal.value = new_value

        self._invalidate_descendant_radios()

        if emit and self._on_change is not None:
            self._on_change(new_value)

    def _invalidate_descendant_radios(self) -> None:
        self.invalidate()

        def _walk(node: Widget) -> None:
            for child in node.children_snapshot():
                if not isinstance(child, Widget):
                    continue
                if isinstance(child, RadioGroup):
                    continue
                if isinstance(child, RadioButton):
                    child._sync_selected_state()
                    child.invalidate()
                _walk(child)

        _walk(self)


class RadioButton(Toggleable, InteractiveWidget):
    """Material Design 3 RadioButton controlled by nearest RadioGroup."""

    def __init__(
        self,
        value: object | None,
        *,
        disabled: bool | ObservableProtocol[bool] = False,
        size: SizingLike = 48,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["RadioButtonStyle"] = None,
    ) -> None:
        """Initialize RadioButton.

        Args:
            value: Option value represented by this radio button.
            disabled: Disable interaction when True.
            size: Touch target size.
            padding: Space around the touch target.
            style: Style override. Uses theme style when omitted.
        """
        self.option_value = value
        self._style = style

        final_padding = padding if padding is not None else (style.padding if style is not None else 0)
        self._user_padding = padding

        super().__init__(
            value=False,
            on_change=None,
            tristate=False,
            disabled=disabled,
            width=size,
            height=size,
            padding=final_padding,
        )

        try:
            from nuiitivet.rendering.sizing import parse_sizing

            parsed = parse_sizing(size, default=None)
            if parsed.kind == "fixed":
                self._touch_target_size = int(parsed.value)
            else:
                self._touch_target_size = 48
        except Exception:
            self._touch_target_size = 48

        self._state_layer_anim: Animatable[float] = Animatable(0.0, motion=_STATE_LAYER_MOTION)
        self.bind(self._state_layer_anim.subscribe(lambda _: self.invalidate()))

        self._selection_anim: Animatable[float] = Animatable(0.0, motion=_SELECTION_MOTION)
        self.bind(self._selection_anim.subscribe(lambda _: self.invalidate()))

    @property
    def style(self) -> "RadioButtonStyle":
        """Resolved style for this RadioButton."""
        if self._style is not None:
            return self._style
        from nuiitivet.theme.manager import manager
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme = manager.current.extension(MaterialThemeData)
        if theme is None:
            raise ValueError("MaterialThemeData not found in current theme")
        return theme.radio_button_style

    def on_mount(self) -> None:
        super().on_mount()
        if self._user_padding is None and self._style is None:
            try:
                style = self.style
                if style.padding != 0:
                    self.padding = style.padding
                    self.invalidate()
            except Exception:
                pass
        self._sync_selected_state()

    def _selected(self) -> bool:
        group = self.find_ancestor(RadioGroup)
        if group is None:
            return bool(self.value)
        return group.value == self.option_value

    def _sync_selected_state(self) -> None:
        self.value = self._selected()

    def _handle_click(self) -> None:
        if self.disabled:
            return

        group = self.find_ancestor(RadioGroup)
        if group is None:
            return

        group.select(self.option_value)

    def _get_state_layer_target_opacity(self) -> float:
        state = self.state
        if state.dragging:
            return float(self._DRAG_OPACITY)
        if state.pressed:
            return float(self._PRESS_OPACITY)
        if state.hovered:
            return float(self._HOVER_OPACITY)
        return 0.0

    def _get_active_state_layer_opacity(self) -> float:
        target = self._get_state_layer_target_opacity()
        if abs(self._state_layer_anim.target - target) > 1e-6:
            self._state_layer_anim.target = target
        return float(self._state_layer_anim.value)

    def _get_selection_progress(self) -> float:
        self._sync_selected_state()
        target = 1.0 if bool(self.value) else 0.0
        if abs(self._selection_anim.target - target) > 1e-6:
            self._selection_anim.target = target
        return float(self._selection_anim.value)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred size including padding."""
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        width = int(w_dim.value) if w_dim.kind == "fixed" else self._touch_target_size
        height = int(h_dim.value) if h_dim.kind == "fixed" else self._touch_target_size

        l, t, r, b = self.padding
        total_w = width + l + r
        total_h = height + t + b

        if max_width is not None:
            total_w = min(int(total_w), int(max_width))
        if max_height is not None:
            total_h = min(int(total_h), int(max_height))
        return (int(total_w), int(total_h))

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint radio button with MD3-like visuals."""
        try:
            from nuiitivet.rendering.skia import draw_oval, make_paint, make_rect, skcolor
            from nuiitivet.material.theme.color_role import ColorRole
            from nuiitivet.material.theme.theme_data import MaterialThemeData
            from nuiitivet.theme import manager as theme_manager

            content_x, content_y, content_w, content_h = self.content_rect(x, y, width, height)
            touch_sz = min(content_w, content_h)
            if touch_sz <= 0:
                return

            cx = content_x + (content_w - touch_sz) // 2
            cy = content_y + (content_h - touch_sz) // 2

            self.set_last_rect(x, y, width, height)

            sizes = self.style.compute_sizes(touch_sz)
            icon_diameter = float(cast(float, sizes["icon_diameter"]))
            inner_dot = float(cast(float, sizes["inner_dot"]))
            stroke_width = float(cast(float, sizes["stroke_width"]))
            state_layer_size = float(cast(float, sizes["state_layer_size"]))

            icon_x = cx + (touch_sz - icon_diameter) / 2.0
            icon_y = cy + (touch_sz - icon_diameter) / 2.0

            mat = theme_manager.current.extension(MaterialThemeData)
            roles = mat.roles if mat is not None else {}

            selected = bool(self.value)
            if self.disabled:
                stroke_hex = roles.get(ColorRole.ON_SURFACE, "#000000")
                stroke_alpha = self.style.disabled_alpha
            else:
                stroke_hex = roles.get(
                    ColorRole.PRIMARY if selected else ColorRole.ON_SURFACE_VARIANT,
                    "#000000",
                )
                stroke_alpha = 1.0

            overlay_alpha = self._get_active_state_layer_opacity()
            if overlay_alpha > 0.0:
                base = roles.get(ColorRole.PRIMARY if selected else ColorRole.ON_SURFACE, "#000000")
                layer_paint = make_paint(color=skcolor(base, overlay_alpha), style="fill", aa=True)
                layer_rect = make_rect(
                    cx + (touch_sz - state_layer_size) / 2.0,
                    cy + (touch_sz - state_layer_size) / 2.0,
                    state_layer_size,
                    state_layer_size,
                )
                if layer_rect is not None and layer_paint is not None:
                    draw_oval(canvas, layer_rect, layer_paint)

            ring_paint = make_paint(
                color=skcolor(stroke_hex, stroke_alpha),
                style="stroke",
                stroke_width=stroke_width,
                aa=True,
            )
            ring_rect = make_rect(icon_x, icon_y, icon_diameter, icon_diameter)
            if ring_rect is not None and ring_paint is not None:
                draw_oval(canvas, ring_rect, ring_paint)

            progress = self._get_selection_progress()
            if progress > 1e-6:
                dot_color = roles.get(ColorRole.PRIMARY, "#000000")
                dot_paint = make_paint(
                    color=skcolor(dot_color, progress * (self.style.disabled_alpha if self.disabled else 1.0)),
                    style="fill",
                    aa=True,
                )
                dot_size = inner_dot * progress
                dot_rect = make_rect(
                    cx + (touch_sz - dot_size) / 2.0,
                    cy + (touch_sz - dot_size) / 2.0,
                    dot_size,
                    dot_size,
                )
                if dot_rect is not None and dot_paint is not None:
                    draw_oval(canvas, dot_rect, dot_paint)

            if self.should_show_focus_ring:
                focus_stroke = float(cast(float, sizes["focus_stroke"]))
                focus_offset = float(cast(float, sizes["focus_offset"]))
                focus_color = roles.get(ColorRole.PRIMARY, "#000000")
                focus_size = state_layer_size + (focus_offset * 2.0)
                focus_rect = make_rect(
                    cx + (touch_sz - focus_size) / 2.0,
                    cy + (touch_sz - focus_size) / 2.0,
                    focus_size,
                    focus_size,
                )
                focus_paint = make_paint(
                    color=skcolor(focus_color, self.style.focus_alpha),
                    style="stroke",
                    stroke_width=focus_stroke,
                    aa=True,
                )
                if focus_rect is not None and focus_paint is not None:
                    draw_oval(canvas, focus_rect, focus_paint)
        except Exception:
            exception_once(_logger, "radio_button_paint_exc", "RadioButton paint raised")


class Switch(Toggleable, InteractiveWidget):
    """Material Design 3 Switch widget."""

    def __init__(
        self,
        checked: bool | ObservableProtocol[bool] = False,
        *,
        on_change: Optional[Callable[[bool], None]] = None,
        disabled: bool | ObservableProtocol[bool] = False,
        size: SizingLike = 48,
        padding: Optional[Union[int, Tuple[int, int], Tuple[int, int, int, int]]] = None,
        style: Optional["SwitchStyle"] = None,
    ) -> None:
        """Initialize Switch.

        Args:
            checked: Checked state source (bool or observable bool).
            on_change: Callback invoked when checked state changes.
            disabled: Disable interaction when True.
            size: Touch target size.
            padding: Space around the switch.
            style: Style override. Uses theme style when omitted.
        """
        self._style = style
        self._user_padding = padding
        self._on_change_bool = on_change

        final_padding = padding if padding is not None else (style.padding if style is not None else 0)

        def _on_toggle(next_val: Optional[bool]) -> None:
            if self._on_change_bool is not None:
                self._on_change_bool(bool(next_val))

        toggleable_value = cast("bool | ObservableProtocol[Optional[bool]]", checked)

        super().__init__(
            value=toggleable_value,
            on_change=_on_toggle,
            tristate=False,
            disabled=disabled,
            width=size,
            height=size,
            padding=final_padding,
        )

        try:
            from nuiitivet.rendering.sizing import parse_sizing

            parsed = parse_sizing(size, default=None)
            if parsed.kind == "fixed":
                self._touch_target_size = int(parsed.value)
            else:
                self._touch_target_size = 48
        except Exception:
            self._touch_target_size = 48

        self._state_layer_anim: Animatable[float] = Animatable(0.0, motion=_STATE_LAYER_MOTION)
        self.bind(self._state_layer_anim.subscribe(lambda _: self.invalidate()))
        initial_selection = 1.0 if bool(self.value) else 0.0
        self._selection_anim: Animatable[float] = Animatable(initial_selection, motion=_SELECTION_MOTION)
        self.bind(self._selection_anim.subscribe(lambda _: self.invalidate()))

    @property
    def style(self) -> "SwitchStyle":
        """Resolved style for this Switch."""
        if self._style is not None:
            return self._style
        from nuiitivet.theme.manager import manager
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme = manager.current.extension(MaterialThemeData)
        if theme is None:
            raise ValueError("MaterialThemeData not found in current theme")
        return theme.switch_style

    def on_mount(self) -> None:
        super().on_mount()
        if self._user_padding is None and self._style is None:
            try:
                style = self.style
                if style.padding != 0:
                    self.padding = style.padding
                    self.invalidate()
            except Exception:
                pass

    def _get_state_layer_target_opacity(self) -> float:
        state = self.state
        if state.dragging:
            return float(self._DRAG_OPACITY)
        if state.pressed:
            return float(self._PRESS_OPACITY)
        if state.hovered:
            return float(self._HOVER_OPACITY)
        return 0.0

    def _get_active_state_layer_opacity(self) -> float:
        target = self._get_state_layer_target_opacity()
        if abs(self._state_layer_anim.target - target) > 1e-6:
            self._state_layer_anim.target = target
        return float(self._state_layer_anim.value)

    def _get_selection_progress(self) -> float:
        target = 1.0 if bool(self.value) else 0.0
        if abs(self._selection_anim.target - target) > 1e-6:
            self._selection_anim.target = target
        return float(self._selection_anim.value)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred size including padding."""
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        width = int(w_dim.value) if w_dim.kind == "fixed" else self._touch_target_size
        height = int(h_dim.value) if h_dim.kind == "fixed" else self._touch_target_size

        l, t, r, b = self.padding
        total_w = width + l + r
        total_h = height + t + b

        if max_width is not None:
            total_w = min(int(total_w), int(max_width))
        if max_height is not None:
            total_h = min(int(total_h), int(max_height))
        return (int(total_w), int(total_h))

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint switch with animated thumb and track."""
        try:
            from nuiitivet.material.theme.color_role import ColorRole
            from nuiitivet.material.theme.theme_data import MaterialThemeData
            from nuiitivet.rendering.skia import draw_oval, draw_round_rect, make_paint, make_rect, skcolor
            from nuiitivet.theme import manager as theme_manager

            content_x, content_y, content_w, content_h = self.content_rect(x, y, width, height)
            touch_sz = min(content_w, content_h)
            if touch_sz <= 0:
                return

            cx = content_x + (content_w - touch_sz) // 2
            cy = content_y + (content_h - touch_sz) // 2
            self.set_last_rect(x, y, width, height)

            sizes = self.style.compute_sizes(touch_sz)
            track_w = float(cast(float, sizes["track_width"]))
            track_h = float(cast(float, sizes["track_height"]))
            thumb_d = float(cast(float, sizes["thumb_diameter"]))
            state_layer_size = float(cast(float, sizes["state_layer_size"]))
            track_radius = track_h / 2.0

            track_x = cx + (touch_sz - track_w) / 2.0
            track_y = cy + (touch_sz - track_h) / 2.0

            mat = theme_manager.current.extension(MaterialThemeData)
            roles = mat.roles if mat is not None else {}

            progress = self._get_selection_progress()

            unchecked_track_hex = roles.get(ColorRole.SURFACE_CONTAINER_HIGHEST, "#9E9E9E")
            checked_track_hex = roles.get(ColorRole.PRIMARY, "#000000")
            unchecked_thumb_hex = roles.get(ColorRole.OUTLINE, "#616161")
            checked_thumb_hex = roles.get(ColorRole.ON_PRIMARY, "#FFFFFF")

            track_hex = checked_track_hex if progress >= 0.5 else unchecked_track_hex
            thumb_hex = checked_thumb_hex if progress >= 0.5 else unchecked_thumb_hex

            alpha = self.style.disabled_alpha if self.disabled else 1.0
            track_paint = make_paint(color=skcolor(track_hex, alpha), style="fill", aa=True)
            track_rect = make_rect(track_x, track_y, track_w, track_h)
            if track_rect is not None and track_paint is not None:
                draw_round_rect(canvas, track_rect, track_radius, track_paint)

            thumb_start = track_x + (track_h - thumb_d) / 2.0
            thumb_end = track_x + track_w - track_h + (track_h - thumb_d) / 2.0
            thumb_x = thumb_start + (thumb_end - thumb_start) * progress
            thumb_y = track_y + (track_h - thumb_d) / 2.0

            overlay_alpha = self._get_active_state_layer_opacity()
            if overlay_alpha > 0.0:
                overlay_rect = make_rect(
                    thumb_x + (thumb_d - state_layer_size) / 2.0,
                    thumb_y + (thumb_d - state_layer_size) / 2.0,
                    state_layer_size,
                    state_layer_size,
                )
                overlay_color = roles.get(ColorRole.ON_SURFACE, "#000000")
                overlay_paint = make_paint(color=skcolor(overlay_color, overlay_alpha), style="fill", aa=True)
                if overlay_rect is not None and overlay_paint is not None:
                    draw_oval(canvas, overlay_rect, overlay_paint)

            thumb_paint = make_paint(color=skcolor(thumb_hex, alpha), style="fill", aa=True)
            thumb_rect = make_rect(thumb_x, thumb_y, thumb_d, thumb_d)
            if thumb_rect is not None and thumb_paint is not None:
                draw_oval(canvas, thumb_rect, thumb_paint)

            if self.should_show_focus_ring:
                focus_stroke = float(cast(float, sizes["focus_stroke"]))
                focus_offset = float(cast(float, sizes["focus_offset"]))
                focus_color = roles.get(ColorRole.PRIMARY, "#000000")
                focus_size = state_layer_size + (focus_offset * 2.0)
                focus_rect = make_rect(
                    thumb_x + (thumb_d - focus_size) / 2.0,
                    thumb_y + (thumb_d - focus_size) / 2.0,
                    focus_size,
                    focus_size,
                )
                focus_paint = make_paint(
                    color=skcolor(focus_color, self.style.focus_alpha),
                    style="stroke",
                    stroke_width=focus_stroke,
                    aa=True,
                )
                if focus_rect is not None and focus_paint is not None:
                    draw_oval(canvas, focus_rect, focus_paint)
        except Exception:
            exception_once(_logger, "switch_paint_exc", "Switch paint raised")


__all__ = ["Checkbox", "RadioGroup", "RadioButton", "Switch"]
