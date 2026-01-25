from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, Union, cast

from nuiitivet.input.pointer import PointerEvent
from nuiitivet.widgeting.widget import Widget
from nuiitivet.input.codes import (
    MOD_CTRL,
    MOD_META,
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_DELETE,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_LEFT,
    TEXT_MOTION_RIGHT,
)
from nuiitivet.observable import Disposable, Observable, ObservableProtocol
from nuiitivet.platform import IMEManager, get_system_clipboard
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgets.interaction import InteractionHostMixin, FocusNode
from nuiitivet.widgets.text_editing import TextEditingValue, TextRange
from nuiitivet.rendering.skia import make_font, make_paint, make_text_blob, get_typeface, get_default_font_fallbacks
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.types import ColorSpec
from nuiitivet.common.logging_once import exception_once

_logger = logging.getLogger(__name__)


class EditableText(InteractionHostMixin, Widget):
    """
    A basic text input widget that handles text editing, selection, and cursor rendering.
    It does not include any decoration (borders, labels, etc.).
    """

    _state_internal = Observable(TextEditingValue())

    def __init__(
        self,
        value: Union[str, ObservableProtocol[str]] = "",
        on_change: Optional[Callable[[str], None]] = None,
        on_focus_change: Optional[Callable[[bool], None]] = None,
        text_color: ColorSpec = "#000000",
        cursor_color: ColorSpec = "#000000",
        selection_color: ColorSpec = "#B3D7FF",  # Default selection color
        font_family: Optional[str] = None,
        font_size: int = 14,
        width: SizingLike = None,
        height: SizingLike = None,
        disabled: bool = False,
        obscure_text: bool = False,
    ):
        super().__init__(width=width, height=height)

        self._text_color = text_color
        self._cursor_color = cursor_color
        self._selection_color = selection_color
        self._font_family = font_family
        self._font_size = font_size
        self._obscure_text = obscure_text

        self._on_change = on_change
        self._on_focus_change_callback = on_focus_change
        self._external_str_obs: ObservableProtocol[str] | None = None
        self._external_sub: Optional[Disposable] = None

        # Initialize state
        initial_text = ""
        if hasattr(value, "subscribe") and hasattr(value, "value"):
            self._external_str_obs = cast("ObservableProtocol[str]", value)
            initial_text = self._external_str_obs.value
        elif isinstance(value, str):
            initial_text = value

        initial_value = TextEditingValue(text=initial_text, selection=TextRange(len(initial_text), len(initial_text)))
        setattr(self, "_state_internal", initial_value)

        # Focus handling
        self.add_node(
            FocusNode(
                on_focus_change=self._handle_focus_change,
                on_key=self._handle_key,
                on_text=self._handle_text,
                on_text_motion=self._handle_text_motion,
                on_ime_composition=self._handle_ime_composition,
            )
        )

        self.enable_click(on_press=self._handle_press)

        if disabled:
            self.state.disabled = True

    @property
    def text_color(self) -> ColorSpec:
        return self._text_color

    @text_color.setter
    def text_color(self, value: ColorSpec):
        if self._text_color != value:
            self._text_color = value
            self.invalidate()

    @property
    def cursor_color(self) -> ColorSpec:
        return self._cursor_color

    @cursor_color.setter
    def cursor_color(self, value: ColorSpec):
        if self._cursor_color != value:
            self._cursor_color = value
            self.invalidate()

    @property
    def selection_color(self) -> ColorSpec:
        return self._selection_color

    @selection_color.setter
    def selection_color(self, value: ColorSpec):
        if self._selection_color != value:
            self._selection_color = value
            self.invalidate()

    @property
    def font_family(self) -> Optional[str]:
        return self._font_family

    @font_family.setter
    def font_family(self, value: Optional[str]):
        if self._font_family != value:
            self._font_family = value
            self.invalidate()

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, value: int):
        if self._font_size != value:
            self._font_size = value
            self.invalidate()

    @property
    def obscure_text(self) -> bool:
        return self._obscure_text

    @obscure_text.setter
    def obscure_text(self, value: bool):
        if self._obscure_text != value:
            self._obscure_text = value
            self.invalidate()

    def on_mount(self) -> None:
        super().on_mount()
        if self._external_str_obs:

            def _on_external_change(new_text: str):
                current = self._state_internal.value
                if current.text == new_text:
                    return

                new_val = TextEditingValue(text=new_text, selection=TextRange(len(new_text), len(new_text)))
                self._state_internal.value = new_val
                self.invalidate()

            self._external_sub = self._external_str_obs.subscribe(_on_external_change)

    def on_unmount(self) -> None:
        super().on_unmount()
        if self._external_sub:
            self._external_sub.dispose()
            self._external_sub = None

    @property
    def value(self) -> str:
        return self._state_internal.value.text

    @value.setter
    def value(self, new_text: str):
        current = self._state_internal.value
        if current.text == new_text:
            return

        new_val = TextEditingValue(text=new_text, selection=TextRange(len(new_text), len(new_text)))
        self._update_value(new_val)

    def _update_value(self, new_value: TextEditingValue) -> None:
        current = self._state_internal.value
        if current == new_value:
            return

        self._state_internal.value = new_value
        self.invalidate()

        if current.text != new_value.text and self._on_change:
            self._on_change(new_value.text)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        font = self._get_font()
        if not font:
            return (0, 0)

        text = self._state_internal.value.text
        # If empty, measure a dummy character to get height
        measure_text = text if text else "M"

        width = int(font.measureText(measure_text)) if text else 0
        metrics = font.getMetrics()
        height = int(-metrics.fAscent + metrics.fDescent)

        return (width, height)

    def layout(self, width: int, height: int) -> None:
        # EditableText fills the available space or uses preferred size
        pass

    def focus(self) -> None:
        try:
            node = self.get_node(FocusNode)
            if node and isinstance(node, FocusNode):
                node.request_focus()
            else:
                self.state.focused = True
                self.invalidate()
        except Exception:
            exception_once(_logger, "editable_text_focus_exc", "EditableText.focus failed")

    def _handle_press(self, event: PointerEvent) -> None:
        self.focus()

        # Simple hit testing for cursor position
        local_x = event.x
        if self.global_layout_rect:
            local_x -= self.global_layout_rect[0]

        index = self._get_index_at(local_x)

        current = self._state_internal.value
        if current.selection.start != index or current.selection.end != index:
            self._update_value(current.copy_with(selection=TextRange(index, index), composing=TextRange(-1, -1)))

    def _get_font(self):
        fallbacks = get_default_font_fallbacks()
        candidates = (self.font_family,) + fallbacks if self.font_family else fallbacks

        tf = get_typeface(
            candidate_files=None,
            family_candidates=candidates,
            pkg_font_dir=None,
            fallback_to_default=True,
        )
        return make_font(tf, self.font_size)

    def _get_index_at(self, x: float) -> int:
        font = self._get_font()
        if font is None:
            return 0

        text = self._state_internal.value.text
        if not text:
            return 0

        if x < 0:
            return 0

        for i in range(len(text) + 1):
            sub = text[:i]
            w = font.measureText(sub)
            if w > x:
                prev_w = font.measureText(text[: i - 1]) if i > 0 else 0
                if x - prev_w < w - x:
                    return i - 1
                return i

        return len(text)

    def _handle_focus_change(self, focused: bool):
        self.invalidate()
        if self._on_focus_change_callback:
            self._on_focus_change_callback(focused)

    def _handle_text(self, text: str) -> bool:
        current_value = self._state_internal.value
        selection = current_value.selection
        full_text = current_value.text

        if current_value.is_composing:
            range_to_replace = current_value.composing
            new_text = range_to_replace.text_before(full_text) + text + range_to_replace.text_after(full_text)
            new_cursor_pos = range_to_replace.start + len(text)
        else:
            new_text = selection.text_before(full_text) + text + selection.text_after(full_text)
            new_cursor_pos = selection.min + len(text)

        new_value = current_value.copy_with(
            text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos), composing=TextRange(-1, -1)
        )

        if new_value != current_value:
            self._update_value(new_value)
            return True
        return False

    def _handle_ime_composition(self, text: str, start: int, length: int) -> bool:
        current_value = self._state_internal.value
        full_text = current_value.text

        if current_value.is_composing:
            range_to_replace = current_value.composing
            prefix = range_to_replace.text_before(full_text)
            suffix = range_to_replace.text_after(full_text)
        else:
            selection = current_value.selection
            prefix = selection.text_before(full_text)
            suffix = selection.text_after(full_text)
            range_to_replace = selection

        new_full_text = prefix + text + suffix

        new_composing_start = len(prefix)
        new_composing_end = new_composing_start + len(text)
        new_composing_range = TextRange(new_composing_start, new_composing_end)

        sel_start = new_composing_start + start
        sel_end = sel_start + length
        new_selection = TextRange(sel_start, sel_end)

        new_value = current_value.copy_with(text=new_full_text, selection=new_selection, composing=new_composing_range)

        self._update_value(new_value)
        return True

    def _handle_text_motion(self, motion: int, select: bool = False) -> bool:
        current_value = self._state_internal.value
        text = current_value.text
        selection = current_value.selection

        anchor = selection.start
        focus = selection.end
        new_focus = focus
        handled = False

        if motion == TEXT_MOTION_BACKSPACE:
            if not selection.is_collapsed:
                new_text = selection.text_before(text) + selection.text_after(text)
                new_cursor_pos = selection.min
                new_value = current_value.copy_with(text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos))
                self._update_value(new_value)
                return True
            if selection.min > 0:
                pos = selection.min
                new_text = text[: pos - 1] + text[pos:]
                new_cursor_pos = pos - 1
                new_value = current_value.copy_with(text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos))
                self._update_value(new_value)
                return True
            return False

        if motion == TEXT_MOTION_DELETE:
            if not selection.is_collapsed:
                new_text = selection.text_before(text) + selection.text_after(text)
                new_cursor_pos = selection.min
                new_value = current_value.copy_with(text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos))
                self._update_value(new_value)
                return True
            if selection.max < len(text):
                pos = selection.max
                new_text = text[:pos] + text[pos + 1 :]
                new_cursor_pos = selection.min
                new_value = current_value.copy_with(text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos))
                self._update_value(new_value)
                return True
            return False

        if motion == TEXT_MOTION_LEFT:
            if not select and not selection.is_collapsed:
                new_focus = selection.min
                handled = True
            elif focus > 0:
                new_focus = focus - 1
                handled = True
        elif motion == TEXT_MOTION_RIGHT:
            if not select and not selection.is_collapsed:
                new_focus = selection.max
                handled = True
            elif focus < len(text):
                new_focus = focus + 1
                handled = True
        elif motion == TEXT_MOTION_HOME:
            new_focus = 0
            handled = True
        elif motion == TEXT_MOTION_END:
            new_focus = len(text)
            handled = True

        if handled:
            if select:
                new_selection = TextRange(anchor, new_focus)
            else:
                new_selection = TextRange(new_focus, new_focus)

            if new_selection != selection:
                self._update_value(current_value.copy_with(selection=new_selection))
                return True

        return False

    def _handle_key(self, key: str, modifiers: int) -> bool:
        is_ctrl = bool(modifiers & (MOD_CTRL | MOD_META))

        if not is_ctrl:
            return False

        current_value = self._state_internal.value
        text = current_value.text
        selection = current_value.selection

        if key == "a":
            new_value = current_value.copy_with(selection=TextRange(0, len(text)))
            self._update_value(new_value)
            return True

        if key == "c":
            if not selection.is_collapsed:
                selected_text = selection.text_inside(text)
                self._copy_to_clipboard(selected_text)
            return True

        if key == "v":
            clipboard_text = self._get_from_clipboard()
            if clipboard_text:
                new_text = selection.text_before(text) + clipboard_text + selection.text_after(text)
                new_cursor_pos = selection.min + len(clipboard_text)
                new_value = current_value.copy_with(text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos))
                self._update_value(new_value)
            return True

        if key == "x":
            if not selection.is_collapsed:
                selected_text = selection.text_inside(text)
                self._copy_to_clipboard(selected_text)
                new_text = selection.text_before(text) + selection.text_after(text)
                new_cursor_pos = selection.min
                new_value = current_value.copy_with(text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos))
                self._update_value(new_value)
            return True

        return False

    def _copy_to_clipboard(self, text: str) -> None:
        get_system_clipboard().set_text(text)

    def _get_from_clipboard(self) -> str:
        return get_system_clipboard().get_text() or ""

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        if canvas is None:
            return

        is_focused = self.state.focused
        current_value = self._state_internal.value
        text = current_value.text
        selection = current_value.selection

        font = self._get_font()
        if font:
            font_metrics = font.getMetrics()
            # Align text vertically centered in the available height
            text_height = -font_metrics.fAscent + font_metrics.fDescent
            ty = y + (height + text_height) / 2 - font_metrics.fDescent

            # Draw Text
            if text:
                from nuiitivet.theme.manager import manager as theme_manager

                text_color = resolve_color_to_rgba(self.text_color, theme=theme_manager.current)
                paint_text = make_paint(color=text_color)
                blob = make_text_blob(text, font)
                if blob:
                    canvas.drawTextBlob(blob, x, ty, paint_text)

            # Draw Cursor
            if is_focused and selection.is_collapsed:
                cursor_text = text[: selection.end]
                cursor_x = font.measureText(cursor_text)

                cursor_top = ty + font_metrics.fAscent
                cursor_bottom = ty + font_metrics.fDescent

                IMEManager.get().update_cursor_rect(
                    x + cursor_x,
                    cursor_top,
                    2,
                    cursor_bottom - cursor_top,
                )

                from nuiitivet.theme.manager import manager as theme_manager

                cursor_color = resolve_color_to_rgba(self.cursor_color, theme=theme_manager.current)
                paint_cursor = make_paint(color=cursor_color, style="stroke", stroke_width=2)
                if paint_cursor is not None:
                    canvas.drawLine(
                        x + cursor_x,
                        cursor_top,
                        x + cursor_x,
                        cursor_bottom,
                        paint_cursor,
                    )
