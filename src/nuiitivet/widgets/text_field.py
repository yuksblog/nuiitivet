"""Core text field implementation (design-agnostic).

Provides the base TextFieldBase class that handles text editing logic
without any specific design system styling.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple, TypeVar, Union

from nuiitivet.input.pointer import PointerEvent
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.observable import ObservableProtocol
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgets.interaction import InteractionHostMixin
from nuiitivet.widgets.editable_text import EditableText
from nuiitivet.common.logging_once import exception_once
from nuiitivet.platform import get_system_clipboard


_logger = logging.getLogger(__name__)


class TextFieldBase(InteractionHostMixin, ComposableWidget):
    """Base text input widget (design-agnostic).

    This class provides the core text editing functionality without any
    specific design system styling. Material Design specific features
    (floating labels, M3 styling) should be implemented in subclasses.

    Parameters:
    - value: Initial text value (str) OR External observable
    - on_change: Callback when value changes
    - text_color: Color for input text
    - cursor_color: Color for cursor
    - selection_color: Color for text selection
    - font_size: Font size for input text
    - width: Explicit width sizing
    - height: Explicit height sizing
    - padding: Space around the text field
    - disabled: Disable interaction
    """

    TTextFieldBase = TypeVar("TTextFieldBase", bound="TextFieldBase")

    @classmethod
    def two_way(
        cls: type[TTextFieldBase],
        value: ObservableProtocol[str],
        *,
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> TTextFieldBase:
        """Create a two-way bound TextField."""

        def _bound_on_change(new_text: str) -> None:
            try:
                value.value = new_text
            except Exception:
                exception_once(
                    _logger, "text_field_base_two_way_set_value_exc", "TextFieldBase.two_way failed to set value"
                )
            if on_change is not None:
                try:
                    on_change(new_text)
                except Exception:
                    exception_once(
                        _logger, "text_field_base_two_way_on_change_exc", "TextFieldBase.two_way on_change raised"
                    )

        return cls(value=value, on_change=_bound_on_change, **kwargs)

    def __init__(
        self,
        value: Union[str, ObservableProtocol[str]] = "",
        on_change: Optional[Callable[[str], None]] = None,
        text_color: str = "#000000",
        cursor_color: str = "#000000",
        selection_color: str = "#0000FF",
        font_size: int = 14,
        width: SizingLike = 200,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
        disabled: bool = False,
    ):
        super().__init__(width=width, height=height, padding=padding)

        self._on_change = on_change

        # EditableText
        self._editable = EditableText(
            value=value,
            on_change=self._handle_editable_change,
            on_focus_change=self._on_editable_focus_change,
            text_color=text_color,
            cursor_color=cursor_color,
            selection_color=selection_color,
            font_size=font_size,
            disabled=disabled,
        )
        self.add_child(self._editable)

        self.enable_click(on_press=self._handle_press)

        if disabled:
            self.state.disabled = True

    @property
    def value(self) -> str:
        """Get the current text value."""
        return self._editable.value

    @value.setter
    def value(self, new_text: str):
        """Set the text value."""
        self._editable.value = new_text

    def _handle_editable_change(self, new_text: str) -> None:
        """Called when the editable text changes."""
        if self._on_change:
            self._on_change(new_text)

    def _on_editable_focus_change(self, focused: bool) -> None:
        """Called when the editable text focus changes."""
        self.invalidate()

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return the preferred (width, height) for this TextField."""
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        default_width = 200
        default_height = 40

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        else:
            width = default_width

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        else:
            height = default_height

        l, t, r, b = self.padding
        total_w = width + l + r
        total_h = height + t + b

        if max_width is not None:
            total_w = min(int(total_w), int(max_width))
        if max_height is not None:
            total_h = min(int(total_h), int(max_height))

        return (int(total_w), int(total_h))

    def layout(self, width: int, height: int) -> None:
        """Layout the text field."""
        super().layout(width, height)

        cx, cy, cw, ch = self.content_rect(0, 0, width, height)

        # EditableText takes full content area by default
        self._editable.layout(cw, ch)
        self._editable.set_layout_rect(cx, cy, cw, ch)

    def focus(self) -> None:
        """Focus the text field."""
        self._editable.focus()

    def _handle_press(self, event: PointerEvent) -> None:
        """Handle press event."""
        self.focus()

    def build(self) -> Widget:
        """Build the widget tree."""
        return self

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        """Paint the text field."""
        if canvas is None:
            return

        self._draw_editable(canvas, x, y)

    def _draw_editable(self, canvas, x: int, y: int) -> None:
        """Draw the editable text."""
        rect = self._editable.layout_rect
        if rect is None:
            return

        rel_x, rel_y, w, h = rect
        cx = x + rel_x
        cy = y + rel_y
        self._editable.set_last_rect(cx, cy, w, h)
        self._editable.paint(canvas, cx, cy, w, h)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to system clipboard."""
        get_system_clipboard().set_text(text)

    def _get_from_clipboard(self) -> str:
        """Get text from system clipboard."""
        return get_system_clipboard().get_text() or ""
