"""Material Design 3 Text Field.

This module provides the unified :class:`TextField` widget. The visual
variant (filled, outlined) is expressed entirely through the ``style``
argument; use :meth:`TextFieldStyle.filled` or :meth:`TextFieldStyle.outlined`
to obtain the standard M3 presets.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union, TYPE_CHECKING, cast

from nuiitivet.input.pointer import PointerEvent
from nuiitivet.widgeting.widget import Widget
from nuiitivet.observable import ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgets.interaction import FocusNode
from nuiitivet.material.styles.text_field_style import TextFieldStyle
from nuiitivet.rendering.skia import (
    draw_round_rect,
    get_skia,
    make_font,
    make_paint,
    make_rect,
    make_text_blob,
    get_typeface,
)
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.manager import manager as theme_manager
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.common.logging_once import exception_once
from nuiitivet.platform import get_system_clipboard
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.theme.color_role import ColorRole
from nuiitivet.animation import Animatable, RgbaTupleConverter
from nuiitivet.material.motion import EXPRESSIVE_DEFAULT_EFFECTS

if TYPE_CHECKING:
    from nuiitivet.material.symbols import Symbol


_logger = logging.getLogger(__name__)


_Symbol: Optional[Type["Symbol"]] = None
try:
    from nuiitivet.material.symbols import Symbol as _ImportedSymbol

    _Symbol = _ImportedSymbol
except Exception:
    _Symbol = None


def _build_text_field_icon(
    icon: Any,
    *,
    arg_name: str,
) -> Optional[Widget]:
    if icon is None:
        return None

    if isinstance(icon, Widget):
        raise TypeError(
            f"{arg_name} does not accept Widget instances. " "Pass a Symbol/str (or an Observable of them)."
        )

    ok = (
        isinstance(icon, str)
        or (_Symbol is not None and isinstance(icon, _Symbol))
        or (hasattr(icon, "subscribe") and hasattr(icon, "value"))
    )
    if not ok:
        raise TypeError(f"{arg_name} must be a Symbol/str (or an Observable of them). " f"Got: {type(icon)!r}")

    from nuiitivet.material.icon import Icon

    return Icon(icon, size=24, padding=0)


class TextField(InteractiveWidget):
    """A text input widget base class.

    Note:
        The constructor `TextField(value=observable)` establishes a **one-way binding**.
        Changes in the observable will update the text field, but user input will NOT
        update the observable automatically.

        For **two-way binding**, use the `TextField.two_way(observable)` factory method.

    Parameters:
    - value: Initial text value (str or TextEditingValue) OR External observable
    - on_change: Callback when value changes
    - label: Floating label text (supports Observable)
    - leading_icon: Icon source (Symbol/str or Observable of them)
    - on_tap_leading_icon: Callback invoked when the leading icon is tapped
    - trailing_icon: Icon source (Symbol/str or Observable of them)
    - on_tap_trailing_icon: Callback invoked when the trailing icon is tapped
    - obscure_text: Whether to mask text display (password-style)
    - supporting_text: Supporting text to display below the field (supports Observable)
    - is_error: Whether the field is in error state (supports Observable)
    - style: Custom style configuration
    - width: Explicit width sizing
    - height: Explicit height sizing
    - padding: Space around the text field
    - disabled: Disable interaction (supports Observable)
    """

    TTextField = TypeVar("TTextField", bound="TextField")

    @classmethod
    def two_way(
        cls: type[TTextField],
        value: ObservableProtocol[str],
        *,
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> TTextField:
        """Create a two-way bound TextField.

        Args:
            value: The observable value to bind to.
            on_change: Optional callback when value changes (in addition to updating the observable).
            **kwargs: Additional arguments passed to the constructor.

        Returns:
            Review instance of the TextField class.
        """

        def _bound_on_change(new_text: str) -> None:
            try:
                value.value = new_text
            except Exception:
                exception_once(_logger, "text_field_two_way_set_value_exc", "TextField.two_way failed to set value")
            if on_change is not None:
                try:
                    on_change(new_text)
                except Exception:
                    exception_once(_logger, "text_field_two_way_on_change_exc", "TextField.two_way on_change raised")

        return cls(value=value, on_change=_bound_on_change, **kwargs)

    def __init__(
        self,
        value: Union[str, ObservableProtocol[str]] = "",
        on_change: Optional[Callable[[str], None]] = None,
        *,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        leading_icon: Symbol | str | ReadOnlyObservableProtocol[Symbol] | ReadOnlyObservableProtocol[str] | None = None,
        on_tap_leading_icon: Optional[Callable[[], None]] = None,
        trailing_icon: (
            Symbol | str | ReadOnlyObservableProtocol[Symbol] | ReadOnlyObservableProtocol[str] | None
        ) = None,
        on_tap_trailing_icon: Optional[Callable[[], None]] = None,
        obscure_text: bool = False,
        supporting_text: str | ReadOnlyObservableProtocol[str | None] | None = None,
        is_error: bool | ObservableProtocol[bool] | None = None,
        error_text: str | ReadOnlyObservableProtocol[str | None] | None = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = 200,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional[TextFieldStyle] = None,
    ):
        """Initialize TextField.

        Args:
            value: Initial text value or observable.
            on_change: Callback when value changes.
            label: Floating label text.
            leading_icon: Icon displayed before the text.
            on_tap_leading_icon: Callback invoked when the leading icon is tapped.
            trailing_icon: Icon displayed after the text.
            on_tap_trailing_icon: Callback invoked when the trailing icon is tapped.
            obscure_text: Whether to mask text display (password-style).
            supporting_text: Supporting text displayed below the field.
            is_error: Whether to use error colors for the field.
            error_text: Deprecated alias for supporting_text.
            disabled: Whether the text field is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding around the text field.
            style: Custom style configuration.
        """
        super().__init__(
            width=width,
            height=height,
            padding=padding,
            on_click=lambda: self.focus(),
            state_layer_color=ColorRole.ON_SURFACE,
            disabled=False,  # Set initial disabled state below
        )

        self._label_source: ReadOnlyObservableProtocol[str] | None = None
        self._supporting_text_source: ReadOnlyObservableProtocol[str | None] | None = None
        self._is_error_source: ObservableProtocol[bool] | None = None
        self._disabled_source: ObservableProtocol[bool] | None = None

        label_value: str | None
        if hasattr(label, "subscribe") and hasattr(label, "value"):
            self._label_source = cast("ReadOnlyObservableProtocol[str]", label)
            try:
                label_value = str(self._label_source.value)
            except Exception:
                label_value = None
        else:
            label_value = str(label) if label is not None else None

        self._legacy_error_text_mode = supporting_text is None and error_text is not None and is_error is None

        supporting_text_value: str | None
        supporting_source = supporting_text if supporting_text is not None else error_text
        if hasattr(supporting_source, "subscribe") and hasattr(supporting_source, "value"):
            self._supporting_text_source = cast("ReadOnlyObservableProtocol[str | None]", supporting_source)
            try:
                v = self._supporting_text_source.value
                supporting_text_value = str(v) if v is not None else None
            except Exception:
                supporting_text_value = None
        else:
            supporting_text_value = str(supporting_source) if supporting_source is not None else None

        initial_is_error: bool
        if hasattr(is_error, "subscribe") and hasattr(is_error, "value"):
            self._is_error_source = cast("ObservableProtocol[bool]", is_error)
            try:
                initial_is_error = bool(self._is_error_source.value)
            except Exception:
                initial_is_error = False
        elif is_error is None:
            initial_is_error = self._legacy_error_text_mode and supporting_text_value is not None
        else:
            initial_is_error = bool(is_error)

        initial_disabled: bool
        if hasattr(disabled, "subscribe") and hasattr(disabled, "value"):
            self._disabled_source = cast("ObservableProtocol[bool]", disabled)
            try:
                initial_disabled = bool(self._disabled_source.value)
            except Exception:
                initial_disabled = False
        else:
            initial_disabled = bool(disabled)

        self.label = label_value
        self.leading_icon = _build_text_field_icon(leading_icon, arg_name="leading_icon")
        self.trailing_icon = _build_text_field_icon(trailing_icon, arg_name="trailing_icon")
        self._on_tap_leading_icon = on_tap_leading_icon
        self._on_tap_trailing_icon = on_tap_trailing_icon
        self.supporting_text = supporting_text_value
        self.is_error = initial_is_error

        if self._on_tap_leading_icon is not None and self.leading_icon is None:
            raise ValueError("on_tap_leading_icon requires leading_icon to be provided")
        if self._on_tap_trailing_icon is not None and self.trailing_icon is None:
            raise ValueError("on_tap_trailing_icon requires trailing_icon to be provided")

        self._user_style = style

        self._on_change = on_change

        # Children
        if self.leading_icon is not None:
            self.add_child(self.leading_icon)
        if self.trailing_icon is not None:
            self.add_child(self.trailing_icon)

        # EditableText
        style = self.style
        self._editable = EditableText(
            value=value,
            on_change=self._handle_editable_change,
            on_focus_change=self._on_editable_focus_change,
            text_color=style.text_color,
            cursor_color=style.error_cursor_color if self.is_error else style.cursor_color,
            selection_color=style.selection_color,
            font_size=16,  # BodyLarge
            disabled=initial_disabled,
            obscure_text=bool(obscure_text),
        )
        self.add_child(self._editable)

        # Animation state
        has_text = bool(self._editable.value)
        self._label_progress = Animatable(
            1.0 if has_text else 0.0,
            motion=EXPRESSIVE_DEFAULT_EFFECTS,
        )
        self._label_progress.subscribe(lambda _: self.invalidate())

        # Indicator Animations
        init_ind_width = style.indicator_width
        self._anim_indicator_width = Animatable(
            float(init_ind_width),
            motion=EXPRESSIVE_DEFAULT_EFFECTS,
        )
        self._anim_indicator_width.subscribe(lambda _: self.invalidate())

        init_ind_color = resolve_color_to_rgba(style.indicator_color, theme=theme_manager.current)
        self._anim_indicator_color = Animatable.vector(
            init_ind_color,
            converter=RgbaTupleConverter(),
            motion=EXPRESSIVE_DEFAULT_EFFECTS,
        )
        self._anim_indicator_color.subscribe(lambda _: self.invalidate())

        init_label_color = resolve_color_to_rgba(style.label_color, theme=theme_manager.current)
        self._anim_label_color = Animatable.vector(
            init_label_color,
            converter=RgbaTupleConverter(),
            motion=EXPRESSIVE_DEFAULT_EFFECTS,
        )
        self._anim_label_color.subscribe(lambda _: self.invalidate())

        # Handle initial disabled state
        if initial_disabled:
            self._apply_disabled(True)

        # Initialize label state
        self._update_label_state()

        # Preserve existing click behavior while adding press handling for icon taps.
        self.enable_click(on_press=self._handle_press)

    @property
    def should_show_focus_ring(self) -> bool:
        """Override to check internal editable focus interaction."""
        return self._editable.state.focused and not self._focus_from_pointer

    def corner_radii_pixels(self, width: float, height: float) -> Tuple[float, float, float, float]:
        style = self.style
        r = style.border_radius
        if style.mode == "filled":
            return (r, r, 0, 0)
        return (r, r, r, r)

    def _apply_disabled(self, value: bool) -> None:
        next_disabled = bool(value)

        self.state.disabled = next_disabled
        self._editable.state.disabled = next_disabled

        if next_disabled:
            # Ensure visual state doesn't get stuck.
            self.state.hovered = False
            self.state.pressed = False
            self.state.pointer_position = None
            self.state.press_position = None
            self.state.focused = False

            try:
                node = self._editable.get_node(FocusNode)
                if node is not None and isinstance(node, FocusNode):
                    node._set_focused(False)
            except Exception:
                pass
            self._editable.state.focused = False

        self.invalidate()

    def _set_label(self, value: Any) -> None:
        self.label = str(value) if value is not None else None
        self.invalidate()

    def _set_supporting_text(self, value: Any) -> None:
        self.supporting_text = str(value) if value is not None else None
        if self._legacy_error_text_mode:
            self.is_error = self.supporting_text is not None
        style = self.style
        self._editable.cursor_color = style.error_cursor_color if self.is_error else style.cursor_color
        self._update_label_state()
        self.mark_needs_layout()

    def _set_is_error(self, value: Any) -> None:
        self.is_error = bool(value)
        style = self.style
        self._editable.cursor_color = style.error_cursor_color if self.is_error else style.cursor_color
        self._update_label_state()
        self.invalidate()

    @property
    def error_text(self) -> str | None:
        """Deprecated alias for supporting_text."""
        return self.supporting_text

    @error_text.setter
    def error_text(self, value: str | None) -> None:
        self.supporting_text = value
        self.is_error = value is not None
        style = self.style
        self._editable.cursor_color = style.error_cursor_color if self.is_error else style.cursor_color
        self._update_label_state()
        self.mark_needs_layout()

    def on_mount(self) -> None:
        super().on_mount()

        # Ensure visual state matches the current theme/focus on mount.
        # This handles cases where initial theme might have been different or
        # Animatable needs a kick (if initial values were somehow problematic).
        self._update_label_state()

        if self._label_source is not None:
            try:
                self.bind_to(self._label_source, self._set_label, dependency="label")
                self._set_label(self._label_source.value)
            except Exception:
                exception_once(_logger, "text_field_bind_label_exc", "TextField failed to bind label")

        if self._supporting_text_source is not None:
            try:
                self.bind_to(self._supporting_text_source, self._set_supporting_text, dependency="supporting_text")
                self._set_supporting_text(self._supporting_text_source.value)
            except Exception:
                exception_once(
                    _logger,
                    "text_field_bind_supporting_text_exc",
                    "TextField failed to bind supporting_text",
                )

        if self._is_error_source is not None:
            try:
                self.bind_to(self._is_error_source, self._set_is_error, dependency="is_error")
                self._set_is_error(self._is_error_source.value)
            except Exception:
                exception_once(_logger, "text_field_bind_is_error_exc", "TextField failed to bind is_error")

        if self._disabled_source is not None:
            try:
                self.bind_to(self._disabled_source, self._apply_disabled, dependency="disabled")
                self._apply_disabled(bool(self._disabled_source.value))
            except Exception:
                exception_once(_logger, "text_field_bind_disabled_exc", "TextField failed to bind disabled")

    def _handle_focus_change(self, focused: bool) -> None:
        super()._handle_focus_change(focused)
        if focused and hasattr(self, "_editable"):
            self._editable.focus()

    @property
    def style(self) -> TextFieldStyle:
        if self._user_style is not None:
            return self._user_style

        from nuiitivet.theme.manager import manager
        from nuiitivet.material.styles.text_field_style import TextFieldStyle

        return TextFieldStyle.from_theme(manager.current)

    @property
    def value(self) -> str:
        return self._editable.value

    @value.setter
    def value(self, new_text: str):
        self._editable.value = new_text

    @property
    def obscure_text(self) -> bool:
        return self._editable.obscure_text

    @obscure_text.setter
    def obscure_text(self, value: bool) -> None:
        self._editable.obscure_text = bool(value)

    def _handle_editable_change(self, new_text: str) -> None:
        self._update_label_state()
        if self._on_change:
            self._on_change(new_text)

    def _on_editable_focus_change(self, focused: bool) -> None:
        self._update_label_state()
        self.invalidate()

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return the preferred (width, height) for this TextField."""
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        default_width = 200
        default_height = 56  # M3 default height

        font = self._get_font()
        style = self.style
        if not style:
            return (default_width, default_height)

        pl, pt, pr, pb = style.content_padding

        icon_w = 0
        if self.leading_icon:
            lw, _ = self.leading_icon.preferred_size()
            icon_w += lw + 24
        if self.trailing_icon:
            tw, _ = self.trailing_icon.preferred_size()
            icon_w += tw + 24

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            if font:
                char_width = font.measureText("M")
                width = int(char_width * 15) + pl + pr + icon_w
            else:
                width = default_width

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = default_height
            if self.supporting_text and font:
                font.setSize(12)
                metrics = font.getMetrics()
                error_h = -metrics.fAscent + metrics.fDescent
                height += int(error_h + 4)

        l, t, r, b = self.padding
        total_w = width + l + r
        total_h = height + t + b

        if max_width is not None:
            total_w = min(int(total_w), int(max_width))
        if max_height is not None:
            total_h = min(int(total_h), int(max_height))

        return (int(total_w), int(total_h))

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)

        l, t, r, b = self.padding
        cx = l
        cy = t
        cw = width - l - r
        ch = height - t - b

        # Reserve space for error text
        self._error_height = 0
        if self.supporting_text:
            font = self._get_font()
            if font:
                font.setSize(12)
                metrics = font.getMetrics()
                self._error_height = int(-metrics.fAscent + metrics.fDescent + 4)
                ch -= self._error_height

        style = self.style
        if not style:
            return

        pl, pt, pr, pb = style.content_padding

        # When the floating label is shown inside the container (filled mode),
        # reserve a 16dp band at the top for the populated label text. This
        # matches MD3 spec: container 56dp = 8 (top) + 16 (floating label) + 24
        # (input text) + 8 (bottom). The rest-state (large) label still uses
        # the full content area; this offset only affects the input text and
        # populated label position.
        self._label_band = 0
        if self.label and style.mode == "filled":
            self._label_band = 16
            pt = pt + self._label_band

        # Leading Icon
        leading_w = 0
        if self.leading_icon:
            lw, lh = self.leading_icon.preferred_size()
            iy = cy + (ch - lh) // 2
            ix = cx + 12
            self.leading_icon.layout(lw, lh)
            self.leading_icon.set_layout_rect(ix, iy, lw, lh)
            leading_w = 12 + lw

        # Trailing Icon
        trailing_w = 0
        if self.trailing_icon:
            tw, th = self.trailing_icon.preferred_size()
            iy = cy + (ch - th) // 2
            ix = cx + cw - 12 - tw
            self.trailing_icon.layout(tw, th)
            self.trailing_icon.set_layout_rect(ix, iy, tw, th)
            trailing_w = 12 + tw

        # EditableText Layout
        text_x = cx + leading_w + pl
        text_y = cy + pt
        text_w = cw - leading_w - trailing_w - pl - pr
        text_h = ch - pt - pb

        self._editable.layout(text_w, text_h)
        self._editable.set_layout_rect(text_x, text_y, text_w, text_h)

        # Store text rect for label positioning
        self._text_rect = (text_x, text_y, text_w, text_h)

    def focus(self) -> None:
        self._editable.focus()

    def _handle_press(self, event: PointerEvent) -> None:
        if self.disabled:
            return

        if self._is_point_in_icon_rect(event, self.leading_icon):
            self._invoke_icon_tap_callback(self._on_tap_leading_icon, key="leading")
            self.focus()
            return

        if self._is_point_in_icon_rect(event, self.trailing_icon):
            self._invoke_icon_tap_callback(self._on_tap_trailing_icon, key="trailing")
            self.focus()
            return

        self.focus()

    def _is_point_in_icon_rect(self, event: PointerEvent, icon: Optional[Widget]) -> bool:
        if icon is None:
            return False
        rect = icon.layout_rect
        if rect is None:
            return False

        rx, ry, rw, rh = rect
        return rx <= event.x <= (rx + rw) and ry <= event.y <= (ry + rh)

    def _invoke_icon_tap_callback(self, cb: Optional[Callable[[], None]], *, key: str) -> None:
        if cb is None:
            return
        try:
            cb()
        except Exception:
            exception_once(
                _logger,
                f"text_field_tap_{key}_icon_exc",
                "TextField %s icon tap callback raised",
                key,
            )

    def _get_font(self):
        tf = get_typeface(
            candidate_files=None,
            family_candidates=("DejaVu Sans", "Arial", "Helvetica", "Liberation Sans"),
            pkg_font_dir=None,
            fallback_to_default=True,
        )
        return make_font(tf, 14)

    def _update_label_state(self):
        has_text = bool(self._editable.value)
        is_focused = self._editable.state.focused
        should_float = has_text or is_focused

        target = 1.0 if should_float else 0.0
        self._label_progress.target = target

        # Style updates
        style = self.style
        is_error = bool(self.is_error)

        def _resolve(c):
            return resolve_color_to_rgba(c, theme=theme_manager.current)

        # 1. Label Color
        if is_error:
            target_label_c = style.error_label_color
        elif is_focused:
            target_label_c = style.focused_label_color
        else:
            target_label_c = style.label_color
        if hasattr(self, "_anim_label_color"):
            self._anim_label_color.target = _resolve(target_label_c)

        # 2. Indicator Color
        if is_error:
            target_ind_c = style.error_indicator_color
        elif is_focused:
            target_ind_c = style.focused_indicator_color
        else:
            target_ind_c = style.indicator_color
        if hasattr(self, "_anim_indicator_color"):
            self._anim_indicator_color.target = _resolve(target_ind_c)

        # 3. Indicator Width
        if is_focused:
            target_w = style.focused_indicator_width
        else:
            target_w = style.indicator_width
        if hasattr(self, "_anim_indicator_width"):
            self._anim_indicator_width.target = float(target_w)

    def build(self) -> Widget:
        return self

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        if canvas is None:
            return

        if hasattr(self, "_text_rect"):
            tx, ty, tw, th = self._text_rect
            l, t, r, b = self.padding
            cx = x + l
            cy = y + t
            cw = width - l - r
            ch = height - t - b

            error_h = getattr(self, "_error_height", 0)
            ch -= error_h

            text_x = x + tx
            text_y = y + ty
            text_h = th
        else:
            cx, cy, cw, ch = self.content_rect(x, y, width, height)
            text_x, text_y, _, text_h = cx, cy, cw, ch
            error_h = 0

        self._draw_container(canvas, cx, cy, cw, ch, text_x_abs=text_x)

        if not self.disabled:
            self.draw_state_layer(canvas, cx, cy, cw, ch)

        self._draw_editable(canvas, x, y)
        self._draw_label(canvas, text_x, text_y, text_h, cy)
        self._draw_icons(canvas, x, y)
        self._draw_supporting_text(canvas, cx, cy, ch)

        if self.should_show_focus_ring:
            self.draw_focus_indicator(canvas, cx, cy, cw, ch)

    def _draw_editable(self, canvas, x: int, y: int) -> None:
        rect = self._editable.layout_rect
        if rect is None:
            return

        rel_x, rel_y, w, h = rect
        cx = x + rel_x
        cy = y + rel_y
        self._editable.set_last_rect(cx, cy, w, h)
        self._editable.paint(canvas, cx, cy, w, h)

    def _draw_container(self, canvas, cx, cy, cw, ch, *, text_x_abs: int | None = None):
        style = self.style

        container_color = resolve_color_to_rgba(style.container_color, theme=theme_manager.current)
        paint_container = make_paint(color=container_color)
        rect = make_rect(cx, cy, cw, ch)

        indicator_color = self._anim_indicator_color.value
        indicator_width = self._anim_indicator_width.value

        if style.mode == "filled":
            if rect is not None and paint_container is not None:
                draw_round_rect(canvas, rect, [style.border_radius, style.border_radius, 0, 0], paint_container)
            paint_indicator = make_paint(color=indicator_color, style="stroke", stroke_width=indicator_width)
            canvas.drawLine(cx, cy + ch, cx + cw, cy + ch, paint_indicator)
            return

        # outlined
        if rect is not None and paint_container is not None:
            draw_round_rect(canvas, rect, style.border_radius, paint_container)
        paint_border = make_paint(color=indicator_color, style="stroke", stroke_width=indicator_width)
        if paint_border is None:
            return

        notch = self._compute_outline_notch(cx, cw, text_x_abs) if text_x_abs is not None else None
        if notch is None:
            if rect is not None:
                draw_round_rect(canvas, rect, style.border_radius, paint_border)
            return

        path = self._build_outlined_notched_path(cx, cy, cw, ch, style.border_radius, notch)
        if path is None:
            if rect is not None:
                draw_round_rect(canvas, rect, style.border_radius, paint_border)
            return
        canvas.drawPath(path, paint_border)

    def _compute_outline_notch(self, cx: int, cw: int, text_x_abs: int) -> Optional[Tuple[float, float]]:
        """Compute the outline notch range (absolute x) for the floating label.

        Returns None when no notch should be drawn (no label, rest state, or
        the resulting gap would be smaller than the corner radii).
        """
        if not self.label:
            return None
        progress = self._label_progress.value
        if progress <= 0.0:
            return None
        font = self._get_font()
        if font is None:
            return None
        font.setSize(12)
        label_w = font.measureText(self.label)
        if label_w <= 0:
            return None
        gap_pad = 4.0
        full_w = label_w + gap_pad * 2
        animated_w = full_w * progress
        center_x = text_x_abs + label_w / 2
        notch_left = center_x - animated_w / 2
        notch_right = center_x + animated_w / 2
        # Clamp inside corner radii so we don't cut into the rounded corners.
        r = self.style.border_radius
        min_x = cx + r + 1
        max_x = cx + cw - r - 1
        notch_left = max(min_x, notch_left)
        notch_right = min(max_x, notch_right)
        if notch_right - notch_left < 2:
            return None
        return (notch_left, notch_right)

    def _build_outlined_notched_path(
        self, cx: int, cy: int, cw: int, ch: int, r: float, notch: Tuple[float, float]
    ) -> Optional[Any]:
        """Build a Skia Path of the outlined border with a top-edge notch."""
        skia = get_skia()
        if skia is None:
            return None
        notch_left, notch_right = notch
        d = 2 * r
        path = skia.Path()
        # Top edge starts after the top-left corner arc.
        path.moveTo(cx + r, cy)
        path.lineTo(notch_left, cy)
        # Skip the notch.
        path.moveTo(notch_right, cy)
        path.lineTo(cx + cw - r, cy)
        # Top-right corner.
        path.arcTo(skia.Rect.MakeXYWH(cx + cw - d, cy, d, d), 270, 90, False)
        path.lineTo(cx + cw, cy + ch - r)
        # Bottom-right corner.
        path.arcTo(skia.Rect.MakeXYWH(cx + cw - d, cy + ch - d, d, d), 0, 90, False)
        path.lineTo(cx + r, cy + ch)
        # Bottom-left corner.
        path.arcTo(skia.Rect.MakeXYWH(cx, cy + ch - d, d, d), 90, 90, False)
        path.lineTo(cx, cy + r)
        # Top-left corner.
        path.arcTo(skia.Rect.MakeXYWH(cx, cy, d, d), 180, 90, False)
        return path

    def _draw_label(self, canvas, text_x, text_y, text_h, cy):
        if not self.label:
            return

        label_progress = self._label_progress.value

        start_size = 16
        end_size = 12
        current_size = start_size - (start_size - end_size) * label_progress

        label_font = self._get_font()
        if label_font:
            label_font.setSize(current_size)
            label_metrics = label_font.getMetrics()
            label_h = -label_metrics.fAscent + label_metrics.fDescent

            # Rest-state label is vertically centered in the full inner area
            # (i.e. as if the floating-label band were not reserved).
            band = getattr(self, "_label_band", 0)
            rest_text_y = text_y - band
            rest_text_h = text_h + band
            start_y = rest_text_y + (rest_text_h + label_h) / 2 - label_metrics.fDescent
            style = self.style
            if style.mode == "outlined":
                # MD3 outlined: floating label is centered on the top outline,
                # i.e. visually overlaps the border line.
                end_y = cy - (label_metrics.fAscent + label_metrics.fDescent) / 2
            else:
                # MD3 filled: floating label sits in the cy+8..cy+24 band.
                end_y = cy + 8 + (-label_metrics.fAscent)

            current_label_y = start_y - (start_y - end_y) * label_progress

            label_color = self._anim_label_color.value
            paint_label = make_paint(color=label_color)

            blob = make_text_blob(self.label, label_font)
            if blob:
                canvas.drawTextBlob(blob, text_x, current_label_y, paint_label)

    def _draw_icons(self, canvas, x, y):
        if self.leading_icon:
            rect = self.leading_icon.layout_rect
            if rect is not None:
                lx, ly, lw, lh = rect
                self.leading_icon.paint(canvas, x + lx, y + ly, lw, lh)

        if self.trailing_icon:
            rect = self.trailing_icon.layout_rect
            if rect is not None:
                tx, ty, tw, th = rect
                self.trailing_icon.paint(canvas, x + tx, y + ty, tw, th)

    def _draw_supporting_text(self, canvas, cx, cy, ch):
        if not self.supporting_text:
            return

        style = self.style
        supporting_font = self._get_font()
        if supporting_font:
            supporting_font.setSize(12)
            supporting_metrics = supporting_font.getMetrics()
            supporting_y = cy + ch + 4 - supporting_metrics.fAscent

            supporting_color_spec = style.error_supporting_text_color if self.is_error else style.supporting_text_color
            supporting_color = resolve_color_to_rgba(supporting_color_spec, theme=theme_manager.current)
            paint_supporting = make_paint(color=supporting_color)

            blob = make_text_blob(self.supporting_text, supporting_font)
            if blob:
                canvas.drawTextBlob(blob, cx + 16, supporting_y, paint_supporting)

    def _copy_to_clipboard(self, text: str) -> None:
        get_system_clipboard().set_text(text)

    def _get_from_clipboard(self) -> str:
        return get_system_clipboard().get_text() or ""
