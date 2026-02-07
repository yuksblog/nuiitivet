"""Material Design 3 Text Fields.

This module contains the implementation of Material Design 3 text fields:
- TextField (base class)
- FilledTextField
- OutlinedTextField
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
from nuiitivet.rendering.skia import draw_round_rect, make_font, make_paint, make_rect, make_text_blob, get_typeface
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.manager import manager as theme_manager
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.common.logging_once import exception_once
from nuiitivet.platform import get_system_clipboard
from nuiitivet.material.interactive_widget import InteractiveWidget
from nuiitivet.material.theme.color_role import ColorRole

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
    - trailing_icon: Icon source (Symbol/str or Observable of them)
    - error_text: Error message to display (supports Observable)
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
        trailing_icon: (
            Symbol | str | ReadOnlyObservableProtocol[Symbol] | ReadOnlyObservableProtocol[str] | None
        ) = None,
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
            trailing_icon: Icon displayed after the text.
            error_text: Error message to display.
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
        self._error_text_source: ReadOnlyObservableProtocol[str | None] | None = None
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

        error_text_value: str | None
        if hasattr(error_text, "subscribe") and hasattr(error_text, "value"):
            self._error_text_source = cast("ReadOnlyObservableProtocol[str | None]", error_text)
            try:
                v = self._error_text_source.value
                error_text_value = str(v) if v is not None else None
            except Exception:
                error_text_value = None
        else:
            error_text_value = str(error_text) if error_text is not None else None

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
        self.error_text = error_text_value

        self._user_style = style
        # Default variant for base class is filled
        if not hasattr(self, "_variant"):
            self._variant = "filled"

        self._on_change = on_change

        # Animation state
        self._label_progress = 0.0
        self._label_anim = None

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
            cursor_color=style.cursor_color if not self.error_text else style.error_cursor_color,
            selection_color=style.selection_color,
            font_size=16,  # BodyLarge
            disabled=initial_disabled,
        )
        self.add_child(self._editable)

        # Handle initial disabled state
        if initial_disabled:
            self._apply_disabled(True)

        # Initialize label state
        self._update_label_state()

    @property
    def should_show_focus_ring(self) -> bool:
        """Override to check internal editable focus interaction."""
        return self._editable.state.focused and not self._focus_from_pointer

    def corner_radii_pixels(self, width: float, height: float) -> Tuple[float, float, float, float]:
        style = self.style
        r = style.border_radius
        if self._variant == "filled":
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

    def _set_error_text(self, value: Any) -> None:
        self.error_text = str(value) if value is not None else None
        style = self.style
        self._editable.cursor_color = style.error_cursor_color if self.error_text else style.cursor_color
        self.mark_needs_layout()

    def on_mount(self) -> None:
        super().on_mount()

        if self._label_source is not None:
            try:
                self.bind_to(self._label_source, self._set_label, dependency="label")
                self._set_label(self._label_source.value)
            except Exception:
                exception_once(_logger, "text_field_bind_label_exc", "TextField failed to bind label")

        if self._error_text_source is not None:
            try:
                self.bind_to(self._error_text_source, self._set_error_text, dependency="error_text")
                self._set_error_text(self._error_text_source.value)
            except Exception:
                exception_once(_logger, "text_field_bind_error_text_exc", "TextField failed to bind error_text")

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
        if hasattr(self, "_user_style") and self._user_style is not None:
            return self._user_style

        from nuiitivet.theme.manager import manager
        from nuiitivet.material.styles.text_field_style import TextFieldStyle

        variant = getattr(self, "_variant", "filled")
        return TextFieldStyle.from_theme(manager.current, variant)

    @property
    def value(self) -> str:
        return self._editable.value

    @value.setter
    def value(self, new_text: str):
        self._editable.value = new_text

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
            if self.error_text and font:
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
        if self.error_text:
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
        self.focus()

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
        if self._label_progress == target:
            return

        if not getattr(self, "_app", None):
            self._label_progress = target
            return

        self._label_anim = self.animate_value(
            target=target,
            duration=0.2,
            start=self._label_progress,
            apply=lambda v: setattr(self, "_label_progress", v),
        )

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

        self._draw_container(canvas, cx, cy, cw, ch)

        if not self.disabled:
            self.draw_state_layer(canvas, cx, cy, cw, ch)

        self._draw_editable(canvas, x, y)
        self._draw_label(canvas, text_x, text_y, text_h, cy)
        self._draw_icons(canvas, x, y)
        self._draw_error(canvas, cx, cy, ch)

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

    def _draw_container(self, canvas, cx, cy, cw, ch):
        pass

    def _draw_label(self, canvas, text_x, text_y, text_h, cy):
        if not self.label:
            return

        style = self.style
        is_focused = self._editable.state.focused
        is_error = bool(self.error_text)

        label_progress = self._label_progress

        start_size = 16
        end_size = 12
        current_size = start_size - (start_size - end_size) * label_progress

        label_font = self._get_font()
        if label_font:
            label_font.setSize(current_size)
            label_metrics = label_font.getMetrics()
            label_h = -label_metrics.fAscent + label_metrics.fDescent

            start_y = text_y + (text_h + label_h) / 2 - label_metrics.fDescent
            end_y = cy + 8 + label_h

            current_label_y = start_y - (start_y - end_y) * label_progress

            label_color = resolve_color_to_rgba(
                (
                    style.error_label_color
                    if is_error
                    else (style.focused_label_color if is_focused else style.label_color)
                ),
                theme=theme_manager.current,
            )
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

    def _draw_error(self, canvas, cx, cy, ch):
        if not self.error_text:
            return

        style = self.style
        is_error = bool(self.error_text)

        if is_error:
            error_font = self._get_font()
            if error_font:
                error_font.setSize(12)
                error_metrics = error_font.getMetrics()
                error_y = cy + ch + 4 - error_metrics.fAscent

                error_color = resolve_color_to_rgba(style.error_label_color, theme=theme_manager.current)
                paint_error = make_paint(color=error_color)

                blob = make_text_blob(self.error_text, error_font)
                if blob:
                    canvas.drawTextBlob(blob, cx + 16, error_y, paint_error)

    def _copy_to_clipboard(self, text: str) -> None:
        get_system_clipboard().set_text(text)

    def _get_from_clipboard(self) -> str:
        return get_system_clipboard().get_text() or ""


class FilledTextField(TextField):
    """M3 Filled TextField.

    Note:
        The constructor `FilledTextField(value=observable)` establishes a **one-way binding**.
        Changes in the observable will update the text field, but user input will NOT
        update the observable automatically.

        For **two-way binding**, use the `FilledTextField.two_way(observable)` factory method.
    """

    def __init__(
        self,
        value: Union[str, ObservableProtocol[str]] = "",
        on_change: Optional[Callable[[str], None]] = None,
        *,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        leading_icon: Symbol | str | ReadOnlyObservableProtocol[Symbol] | ReadOnlyObservableProtocol[str] | None = None,
        trailing_icon: (
            Symbol | str | ReadOnlyObservableProtocol[Symbol] | ReadOnlyObservableProtocol[str] | None
        ) = None,
        error_text: str | ReadOnlyObservableProtocol[str | None] | None = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = 200,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional[TextFieldStyle] = None,
    ):
        """Initialize FilledTextField.

        Args:
            value: Initial text value or observable.
            on_change: Callback when value changes.
            label: Floating label text.
            leading_icon: Icon displayed before the text.
            trailing_icon: Icon displayed after the text.
            error_text: Error message to display.
            disabled: Whether the text field is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding around the text field.
            style: Custom style configuration.
        """
        self._variant = "filled"
        super().__init__(
            value=value,
            on_change=on_change,
            label=label,
            leading_icon=leading_icon,
            trailing_icon=trailing_icon,
            error_text=error_text,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            style=style,
        )

    def _draw_container(self, canvas, cx, cy, cw, ch):
        style = self.style
        is_focused = self._editable.state.focused
        is_error = bool(self.error_text)

        container_color = resolve_color_to_rgba(style.container_color, theme=theme_manager.current)
        paint_container = make_paint(color=container_color)
        rect = make_rect(cx, cy, cw, ch)
        if rect is not None and paint_container is not None:
            draw_round_rect(canvas, rect, [style.border_radius, style.border_radius, 0, 0], paint_container)

        indicator_color = resolve_color_to_rgba(
            (
                style.error_indicator_color
                if is_error
                else (style.focused_indicator_color if is_focused else style.indicator_color)
            ),
            theme=theme_manager.current,
        )
        indicator_width = style.focused_indicator_width if is_focused else style.indicator_width
        paint_indicator = make_paint(color=indicator_color, style="stroke", stroke_width=indicator_width)
        canvas.drawLine(cx, cy + ch, cx + cw, cy + ch, paint_indicator)


class OutlinedTextField(TextField):
    """M3 Outlined TextField.

    Note:
        The constructor `OutlinedTextField(value=observable)` establishes a **one-way binding**.
        Changes in the observable will update the text field, but user input will NOT
        update the observable automatically.

        For **two-way binding**, use the `OutlinedTextField.two_way(observable)` factory method.
    """

    def __init__(
        self,
        value: Union[str, ObservableProtocol[str]] = "",
        on_change: Optional[Callable[[str], None]] = None,
        *,
        label: str | ReadOnlyObservableProtocol[str] | None = None,
        leading_icon: Symbol | str | ReadOnlyObservableProtocol[Symbol] | ReadOnlyObservableProtocol[str] | None = None,
        trailing_icon: (
            Symbol | str | ReadOnlyObservableProtocol[Symbol] | ReadOnlyObservableProtocol[str] | None
        ) = None,
        error_text: str | ReadOnlyObservableProtocol[str | None] | None = None,
        disabled: bool | ObservableProtocol[bool] = False,
        width: SizingLike = 200,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        style: Optional[TextFieldStyle] = None,
    ):
        """Initialize OutlinedTextField.

        Args:
            value: Initial text value or observable.
            on_change: Callback when value changes.
            label: Floating label text.
            leading_icon: Icon displayed before the text.
            trailing_icon: Icon displayed after the text.
            error_text: Error message to display.
            disabled: Whether the text field is disabled.
            width: Width specification.
            height: Height specification.
            padding: Padding around the text field.
            style: Custom style configuration.
        """
        self._variant = "outlined"
        super().__init__(
            value=value,
            on_change=on_change,
            label=label,
            leading_icon=leading_icon,
            trailing_icon=trailing_icon,
            error_text=error_text,
            disabled=disabled,
            width=width,
            height=height,
            padding=padding,
            style=style,
        )

    def _draw_container(self, canvas, cx, cy, cw, ch):
        style = self.style
        is_focused = self._editable.state.focused
        is_error = bool(self.error_text)

        container_color = resolve_color_to_rgba(style.container_color, theme=theme_manager.current)
        paint_container = make_paint(color=container_color)
        rect = make_rect(cx, cy, cw, ch)
        if rect is not None and paint_container is not None:
            draw_round_rect(canvas, rect, style.border_radius, paint_container)

        indicator_color = resolve_color_to_rgba(
            (
                style.error_indicator_color
                if is_error
                else (style.focused_indicator_color if is_focused else style.indicator_color)
            ),
            theme=theme_manager.current,
        )
        indicator_width = style.focused_indicator_width if is_focused else style.indicator_width
        paint_border = make_paint(color=indicator_color, style="stroke", stroke_width=indicator_width)
        if rect is not None and paint_border is not None:
            draw_round_rect(canvas, rect, style.border_radius, paint_border)
