"""Material Design 3 Selection Controls.

This module contains the implementation of Material Design 3 selection controls:
- Checkbox
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional, Tuple, Union, cast

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import Disposable, ObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgets.toggleable import Toggleable
from nuiitivet.widgets.interaction import FocusNode

if TYPE_CHECKING:
    from nuiitivet.material.styles.checkbox_style import CheckboxStyle


_logger = logging.getLogger(__name__)


class Checkbox(Toggleable):
    """A minimal Material-like Checkbox widget (M3準拠).

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
        self._external_unsubs: list[Disposable] = []

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

        # Configure FocusNode
        self._focused = False
        self._focus_from_pointer = False

        node = self.get_node(FocusNode)
        if node and isinstance(node, FocusNode):
            node._on_key = lambda k, m: self.on_key_event(k, m)
            node._on_focus_change = self._handle_focus_change

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

        def _subscribe(obs: object) -> None:
            subscribe = getattr(obs, "subscribe", None)
            if not callable(subscribe):
                return
            try:
                unsub = subscribe(lambda _v: self._sync_from_external())
                if hasattr(unsub, "dispose"):
                    self._external_unsubs.append(cast(Disposable, unsub))
            except Exception:
                return

        if self._checked_external_tri is not None:
            _subscribe(self._checked_external_tri)
        if self._checked_external_bool is not None:
            _subscribe(self._checked_external_bool)
        if self._indeterminate_external is not None:
            _subscribe(self._indeterminate_external)

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

    def on_unmount(self) -> None:
        for unsub in self._external_unsubs:
            try:
                unsub.dispose()
            except Exception:
                pass
        self._external_unsubs.clear()
        super().on_unmount()

    @property
    def observable_state(self) -> ObservableProtocol[Optional[bool]]:
        return self._get_state_obj()

    # Public focus API compatibility
    def focus(self) -> None:
        try:
            node = self.get_node(FocusNode)
            if node and isinstance(node, FocusNode):
                node.request_focus()
            else:
                self.state.focused = True
                self.invalidate()
        except Exception:
            exception_once(_logger, "checkbox_focus_exc", "Checkbox.focus failed")

    def blur(self) -> None:
        try:
            self.state.focused = False
            self.invalidate()
        except Exception:
            exception_once(_logger, "checkbox_blur_exc", "Checkbox.blur failed")

    def _handle_focus_change(self, focused: bool) -> None:
        self._focused = focused
        # state.focused is updated by FocusNode
        if not focused:
            self._focus_from_pointer = False
        self.invalidate()

    def request_focus_from_pointer(self) -> None:
        self._focus_from_pointer = True
        super().request_focus_from_pointer()
        if self._focused:
            self.invalidate()

    def on_key_event(self, key: str, modifiers: int = 0) -> bool:
        if key in ("space", "enter") and not self.disabled:
            self._handle_click()  # Toggleable method
            return True
        return False

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

    # Compatibility properties for tests
    @property
    def _hover(self) -> bool:
        return self.state.hovered

    @property
    def _pressed(self) -> bool:
        return self.state.pressed

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

            overlay_alpha = (
                self.style.pressed_alpha
                if self.state.pressed
                else (self.style.hover_alpha if self.state.hovered else 0.0)
            )

            if overlay_alpha and overlay_alpha > 0.0:
                cx_center = float(cx + touch_sz / 2.0)
                cy_center = float(cy + touch_sz / 2.0)
                r = float(state_diam / 2.0)
                on_surf = roles.get(ColorRole.ON_SURFACE, "#000000")
                ov = skcolor(on_surf, overlay_alpha)
                p_ov = make_paint(color=ov, style="fill", aa=True)
                try:
                    canvas.drawCircle(cx_center, cy_center, r, p_ov)
                except Exception:
                    draw_oval(canvas, make_rect(cx_center - r, cy_center - r, state_diam, state_diam), p_ov)

            if rect is not None and stroke_p is not None:
                draw_round_rect(canvas, rect, corner, stroke_p)

            show_focus_ring = getattr(self, "_focused", False) and not getattr(self, "_focus_from_pointer", False)
            if show_focus_ring:
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
            if val is True or val is None:
                prim = roles.get(ColorRole.PRIMARY, "#000000")
                fill_p = make_paint(color=skcolor(prim), style="fill", aa=True)
                if rect is not None and fill_p is not None:
                    draw_round_rect(canvas, rect, corner, fill_p)

            overlay_alpha = (
                self.style.pressed_alpha
                if self.state.pressed
                else (self.style.hover_alpha if self.state.hovered else 0.0)
            )

            if overlay_alpha and overlay_alpha > 0.0:
                base = "#000000" if self.state.pressed else "#FFFFFF"
                ov = skcolor(base, overlay_alpha)
                p_ov = make_paint(color=ov, style="fill", aa=True)
                if rect is not None and p_ov is not None:
                    draw_round_rect(canvas, rect, corner, p_ov)

            if val is True or val is None:
                mark_is_none = val is None
                mark_style = "stroke" if not mark_is_none else "fill"
                onp = roles.get(ColorRole.ON_PRIMARY, "#000000")
                mark_p = make_paint(
                    color=skcolor(onp),
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
