from __future__ import annotations

import logging
from typing import Optional, Tuple, Union, cast

from nuiitivet.input.pointer import PointerEvent
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.callbacks import invoke_event_handler, StrCallback
from nuiitivet.input.codes import (
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    TEXT_MOTION_DOWN,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_UP,
)
from nuiitivet.observable import Disposable, Observable, ObservableProtocol, ReadOnlyObservableProtocol
from nuiitivet.platform import get_system_clipboard
from nuiitivet.widgeting.context_lookup import find_window
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgets.interaction import (
    InteractionHostMixin,
    FocusNode,
    DraggableNode,
    FocusChangeCallback,
    FocusSource,
)
from nuiitivet.widgets.input_filter import InputFilter, InputFilterLike, to_input_filter
from nuiitivet.widgets.text_editing import (
    TextEditingValue,
    TextRange,
    apply_motion,
    apply_shortcut,
    compose_text,
    end_composition,
    insert_text,
)
from nuiitivet.widgets.text_lines import (
    Measure,
    break_lines,
    caret_x,
    index_at,
    line_edge,
    line_of,
    move_lines,
)
from nuiitivet.rendering.skia import (
    make_font,
    make_paint,
    make_rect,
    make_text_blob,
    get_typeface,
    get_default_font_fallbacks,
)
from nuiitivet.theme.resolver import resolve_color_to_rgba
from nuiitivet.theme.types import ColorSpec
from nuiitivet.common.logging_once import exception_once

_logger = logging.getLogger(__name__)


def _clamp_index(index: int, length: int) -> int:
    """Clamp a text index into ``[0, length]``."""
    return 0 if index < 0 else (length if index > length else index)


class EditableText(InteractionHostMixin, Widget):
    """
    A basic text input widget that handles text editing, selection, and cursor rendering.
    It does not include any decoration (borders, labels, etc.).

    With ``multiline`` the text takes several lines: it wraps at the width and
    Shift+Enter breaks a line. Enter keeps its meaning: it submits through
    ``on_submit``, and is left alone without one. The field shows ``min_lines``
    lines when empty, grows with the text to ``max_lines``, and then scrolls
    the caret's line into view.
    """

    _state_internal = Observable(TextEditingValue())

    def __init__(
        self,
        value: Union[str, ReadOnlyObservableProtocol[str]] = "",
        on_change: Optional[StrCallback] = None,
        on_user_edit: Optional[StrCallback] = None,
        on_focus_change: Optional[FocusChangeCallback] = None,
        on_submit: Optional[StrCallback] = None,
        input_filter: Optional[InputFilterLike] = None,
        multiline: bool = False,
        min_lines: int = 1,
        max_lines: Optional[int] = None,
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
        """Initialize EditableText.

        Args:
            value: Initial text, or the observable holding the field's value.
                Edits are written back to a writable observable; a read-only
                one displays only.
            on_change: Callback invoked with the text as it changes, by typing
                or by code. Not during an IME composition.
            on_user_edit: Callback invoked with the text the user produced,
                composition included, and never for an assignment by code.
            on_focus_change: Callback invoked with ``(focused, source)`` as
                focus arrives and leaves.
            on_submit: Callback invoked with the text on a bare Enter. Its
                presence makes the field claim the Enter key. Shift+Enter
                never submits: it breaks the line, or does nothing in a
                single-line field.
            input_filter: Rule applied to text as the user types it, a line
                break included.
            multiline: Whether the text takes several lines. It decides
                whether a line break can be typed at all; *input_filter* can
                only refuse one.
            min_lines: Lines shown when the text has fewer, at least 1. Read
                only with *multiline*.
            max_lines: Lines shown before the field scrolls, at least
                *min_lines*; ``None`` grows without bound. Neither bounds the
                text's own line count. Read only with *multiline*.
            text_color: Color of the text.
            cursor_color: Color of the caret.
            selection_color: Color behind the selected text.
            font_family: Font family; the default fallbacks otherwise.
            font_size: Font size in pixels.
            width: Width specification.
            height: Height specification.
            disabled: Whether the field ignores input.
            obscure_text: Whether every character is shown as a bullet.
        """
        super().__init__(width=width, height=height)

        self._multiline = False
        self._min_lines = 1
        self._max_lines: Optional[int] = None

        self._text_color = text_color
        self._cursor_color = cursor_color
        self._selection_color = selection_color
        self._font_family = font_family
        self._font_size = font_size
        self._obscure_text = obscure_text

        self._on_change = on_change
        # Fires for text the *user* produced -- typing, IME, paste, delete --
        # and never for an assignment made by code. ``on_change`` cannot answer
        # "did the user do this?": it is deliberately fired for every text
        # change, including ``value = ...`` and a push from a bound observable,
        # so decorators stay in sync. A caller that must react to the user
        # specifically (reopening an autocomplete panel the application just
        # closed, say) would otherwise mistake its own write-back for input.
        self._on_user_edit = on_user_edit
        self._on_focus_change_callback = on_focus_change
        # Fires on every Enter, and never on focus loss: it reports the user
        # asking for an action, not the value settling. Its presence is also
        # what makes the field claim the Enter key.
        self._on_submit = on_submit
        # Tracks whether the most recent input event committed an IME
        # composition. On macOS the commit arrives as ``on_text`` *before* the
        # Enter key's ``on_key_press`` (the composition is already cleared by
        # the time ``_handle_key`` sees the Enter), so ``is_composing`` alone
        # cannot tell the confirming Enter apart from a genuine submit. This
        # flag mirrors the browser's ``KeyboardEvent.isComposing`` signal: it
        # is set when a composition commits and consumed by the next key press.
        self._ime_just_committed = False
        self._external_str_obs: ReadOnlyObservableProtocol[str] | None = None
        # The same object as ``_external_str_obs`` when that source is writable.
        # Kept separately so the write-back path needs no repeated type check,
        # and so a read-only source is display-only rather than half-bound.
        self._external_writable: ObservableProtocol[str] | None = None
        self._external_sub: Optional[Disposable] = None
        self._input_filter: Optional[InputFilter] = (
            to_input_filter(input_filter) if input_filter is not None else None
        )

        # Scroll offsets (pixels) that keep the caret visible: horizontal for
        # a single line that outgrows the width, vertical for lines that
        # outgrow the height.
        self._scroll_x: float = 0.0
        self._scroll_y: float = 0.0
        # The x a run of Up/Down moves aims for, so a short line passed on the
        # way does not pull the caret left for good. Any other edit drops it.
        self._goal_x: Optional[float] = None
        # The size the last layout gave, which is the wrap width.
        self._viewport: Tuple[int, int] = (0, 0)
        # The lines of the text as last broken, keyed by what they depend on.
        self._lines_cache: Optional[Tuple[Tuple[str, Optional[float], int, Optional[str]], list[TextRange]]] = None
        self.set_lines(multiline, min_lines, max_lines)
        # Track whether the current pointer interaction is in drag mode so
        # that pointer MOVE events extend the selection from the press anchor.
        self._drag_anchor: Optional[int] = None
        # Whether the current focus arrived from a pointer interaction. Used
        # by the host (e.g. TextField) to suppress the keyboard-only focus
        # ring per MD3 spec.
        self._focus_from_pointer: bool = False

        # Initialize state. An observable passed here is the field's value
        # cell: edits are written back to it (see ``_update_value``), matching
        # every other input widget. A read-only source has nowhere to write, so
        # it displays only -- pair it with ``disabled=True``.
        initial_text = ""
        if hasattr(value, "subscribe") and hasattr(value, "value"):
            self._external_str_obs = cast("ReadOnlyObservableProtocol[str]", value)
            initial_text = self._external_str_obs.value
            if isinstance(value, ObservableProtocol):
                self._external_writable = cast("ObservableProtocol[str]", value)
        elif isinstance(value, str):
            initial_text = value

        initial_value = TextEditingValue(text=initial_text, selection=TextRange(len(initial_text), len(initial_text)))
        setattr(self, "_state_internal", initial_value)
        # The last text handed to the application, by either shape of the
        # announcement. See ``_announce``.
        self._announced_text = initial_text

        # Focus handling
        self.add_node(
            FocusNode(
                on_focus_change=self._handle_focus_change,
                on_key=self._handle_key,
                on_text=self._handle_text,
                on_text_motion=self._handle_text_motion,
                on_ime_composition=self._handle_ime_composition,
                on_ime_commit=self._commit_composition,
            )
        )

        # Drag handling for pointer-based range selection.
        self.add_node(
            DraggableNode(
                on_drag_start=self._handle_drag_start,
                on_drag_update=self._handle_drag_update,
                on_drag_end=self._handle_drag_end,
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

    @property
    def multiline(self) -> bool:
        """Whether the text takes several lines."""
        return self._multiline

    @property
    def min_lines(self) -> int:
        """Lines shown when the text has fewer."""
        return self._min_lines

    @property
    def max_lines(self) -> Optional[int]:
        """Lines shown before the field scrolls; ``None`` is unbounded."""
        return self._max_lines

    def set_lines(self, multiline: bool, min_lines: int = 1, max_lines: Optional[int] = None) -> None:
        """Switch the field between one line and several, and set the lines it shows.

        Args:
            multiline: Whether the text takes several lines.
            min_lines: Lines shown when the text has fewer, at least 1.
            max_lines: Lines shown before the field scrolls, at least
                *min_lines*; ``None`` grows without bound.
        """
        if min_lines < 1:
            raise ValueError(f"min_lines must be at least 1, got {min_lines}")
        if max_lines is not None and max_lines < min_lines:
            raise ValueError(f"max_lines must be at least min_lines ({min_lines}), got {max_lines}")
        self._multiline = bool(multiline)
        self._min_lines = min_lines
        self._max_lines = max_lines
        self._lines_cache = None
        self.mark_needs_layout()
        self.invalidate()

    def on_mount(self) -> None:
        super().on_mount()
        if self._external_str_obs:

            def _on_external_change(new_text: str):
                current = self._state_internal.value
                if current.text == new_text:
                    return

                # Keep the caret where the user left it, clamped into the new
                # text, rather than forcing it to the end. Normalizing on
                # write-back (upper-casing, trimming, reformatting) changes the
                # text under an actively edited field, and sending the caret to
                # the end on every keystroke would make such a field unusable.
                new_val = TextEditingValue(
                    text=new_text,
                    selection=TextRange(
                        _clamp_index(current.selection.start, len(new_text)),
                        _clamp_index(current.selection.end, len(new_text)),
                    ),
                )
                self._state_internal.value = new_val
                self._announced_text = new_text
                self._text_changed()
                # Notify listeners so that decorators (e.g. floating label
                # state in TextField) can synchronize with externally-driven
                # value changes. The ``current.text == new_text`` early-return
                # above guards against write-back loops in two-way bound
                # scenarios: an Observable -> on_change -> observable.value
                # cycle terminates because the second delivery is a no-op.
                if self._on_change:
                    invoke_event_handler(
                        self._on_change,
                        new_text,
                        error_key="editable_text_external_on_change",
                        error_msg="EditableText external on_change raised",
                        owner_name=type(self).__name__,
                    )

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

        # Assigned by code, not typed: no input filter, since a filter governs
        # what is typeable rather than what the owner may store.
        new_val = TextEditingValue(text=new_text, selection=TextRange(len(new_text), len(new_text)))
        self._update_value(new_val, user_edit=False)

    def _update_value(self, new_value: TextEditingValue, *, user_edit: bool = True) -> None:
        """Adopt *new_value* and notify.

        Every input handler lands here, so *user_edit* defaults to ``True`` and
        only the ``value`` setter -- the one path reached by code rather than by
        a key, an IME or a pointer -- opts out.
        """
        current = self._state_internal.value
        if current == new_value:
            return

        self._goal_x = None
        self._state_internal.value = new_value
        if current.text != new_value.text:
            self._text_changed()
        else:
            self.invalidate()
        self._announce(new_value)

        if user_edit and self._on_user_edit and current.text != new_value.text:
            # Deliberately *not* held back during a composition, unlike the
            # announcement above: this one reports that the user is typing, and
            # they are typing while they convert. A suggestion panel watching
            # it should be open throughout.
            invoke_event_handler(
                self._on_user_edit,
                new_value.text,
                error_key="editable_text_on_user_edit",
                error_msg="EditableText on_user_edit raised",
                owner_name=type(self).__name__,
            )

    def _text_changed(self) -> None:
        """Repaint, and in a multi-line field relayout: the line count may have moved."""
        if self.multiline:
            self.mark_needs_layout()
        self.invalidate()

    def _announce(self, new_value: TextEditingValue) -> None:
        """Publish the text the application is meant to see.

        The bound observable and ``on_change`` are the same signal in two
        shapes, so both are driven from here under one condition and can never
        disagree about what the application saw.

        Held back while an IME composition is active: the provisional text of a
        half-converted composition is not a value the application should see,
        and anything it wrote in response would fight the IME. The composition
        commits through ``_handle_text``, which lands here with the composing
        range cleared.

        The guard is a baseline rather than "did the text change in this
        update", because ending a composition has to reconcile even when it
        left the text alone -- confirming a single-character candidate clears
        the composing range without touching the text, and that is the moment
        the application first learns of it. A caret or selection move changes
        nothing here and announces nothing.
        """
        if new_value.is_composing or new_value.text == self._announced_text:
            return
        self._announced_text = new_value.text

        self._write_back(new_value.text)
        if self._on_change:
            invoke_event_handler(
                self._on_change,
                new_value.text,
                error_key="editable_text_on_change",
                error_msg="EditableText on_change raised",
                owner_name=type(self).__name__,
            )

    def _write_back(self, text: str) -> None:
        """Push the edited text into the bound observable, if there is one.

        The loop that the write starts terminates in ``_on_external_change``,
        which returns early once the text it is handed already matches.
        """
        obs = self._external_writable
        if obs is None:
            return
        try:
            if obs.value == text:
                return
            obs.value = text
        except Exception:
            exception_once(
                _logger,
                "editable_text_write_back_failed",
                "EditableText failed to write the edited value back to its observable",
            )

    # --- lines -----------------------------------------------------------------

    def line_height(self) -> int:
        """The height of one line of text in pixels, from the font's metrics."""
        font = self._get_font()
        if not font:
            return 0
        metrics = font.getMetrics()
        return int(-metrics.fAscent + metrics.fDescent)

    def line_count(self, width: Optional[float] = None) -> int:
        """How many lines the text takes when wrapped at *width*; at least 1.

        A single-line field always answers 1. ``None`` breaks at ``'\\n'`` only.
        """
        if not self.multiline:
            return 1
        font = self._get_font()
        if not font:
            return 1
        return len(self._lines(font, width))

    def _measure(self, font) -> Measure:
        return lambda s: float(font.measureText(s))

    def _lines(self, font, width: Optional[float]) -> list[TextRange]:
        """The text's lines wrapped at *width*; a single-line field is one line whatever it holds."""
        text = self._get_display_text(self._state_internal.value.text)
        if not self.multiline:
            return [TextRange(0, len(text))]
        key = (text, width, self._font_size, self._font_family)
        cached = self._lines_cache
        if cached is not None and cached[0] == key:
            return cached[1]
        lines = break_lines(text, self._measure(font), width)
        self._lines_cache = (key, lines)
        return lines

    def _wrap_width(self, width: Optional[float] = None) -> Optional[float]:
        """The width lines wrap at: the one given, else the last layout's; ``None`` for a single line."""
        if not self.multiline:
            return None
        if width is not None:
            return max(0.0, float(width))
        return float(self._viewport[0]) if self._viewport[0] > 0 else None

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        font = self._get_font()
        if not font:
            return (0, 0)

        text = self._state_internal.value.text
        display_text = self._get_display_text(text)
        metrics = font.getMetrics()
        line_h = int(-metrics.fAscent + metrics.fDescent)

        if not self.multiline:
            width = int(font.measureText(display_text)) if display_text else 0
            return (width, line_h)

        lines = self._lines(font, self._wrap_width(max_width))
        width = int(max(font.measureText(display_text[line.start : line.end]) for line in lines))
        count = max(self._min_lines, len(lines))
        if self._max_lines is not None:
            count = min(count, self._max_lines)
        return (width, line_h * count)

    def layout(self, width: int, height: int) -> None:
        # EditableText fills the space it is given; the width is where lines wrap.
        self._viewport = (int(width), int(height))

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

    def request_focus_from_pointer(self) -> None:
        # Mark this focus acquisition as pointer-driven so the host can
        # suppress the keyboard-only focus ring (MD3 spec). Reset is handled
        # in ``_handle_focus_change`` when focus is released.
        self._focus_from_pointer = True
        super().request_focus_from_pointer()

    @property
    def is_focus_from_pointer(self) -> bool:
        """Whether the current focus was acquired from a pointer interaction.

        Hosts (e.g. ``TextField``) read this to suppress the keyboard-only
        focus ring per MD3 spec. The flag is set by
        ``request_focus_from_pointer`` and cleared on blur.
        """
        return self._focus_from_pointer

    def _handle_press(self, event: PointerEvent) -> None:
        self.focus()

        index = self._index_at_event(event)
        self._drag_anchor = index

        current = self._state_internal.value
        if current.selection.start != index or current.selection.end != index:
            self._update_value(current.copy_with(selection=TextRange(index, index), composing=TextRange(-1, -1)))

    def _handle_drag_start(self, event: PointerEvent) -> None:
        # Selection anchor is set on press; the fallback below covers the
        # rare case where a drag is observed without a preceding press
        # (e.g. capture transferred mid-gesture). Without it the first
        # drag-update would have nothing to extend the selection from.
        if self._drag_anchor is None:
            self._drag_anchor = self._index_at_event(event)

    def _handle_drag_update(self, event: PointerEvent, dx: float, dy: float) -> None:
        if self._drag_anchor is None:
            return
        index = self._index_at_event(event)
        anchor = self._drag_anchor
        current = self._state_internal.value
        new_selection = TextRange(anchor, index)
        if new_selection != current.selection:
            self._update_value(current.copy_with(selection=new_selection, composing=TextRange(-1, -1)))

    def _handle_drag_end(self, event: PointerEvent) -> None:
        self._drag_anchor = None

    def _index_at_event(self, event: PointerEvent) -> int:
        local_x = event.x
        local_y = event.y
        rect = self.global_visual_rect
        if rect is not None:
            local_x -= rect[0]
            local_y -= rect[1]
        return self._get_index_at(local_x, local_y)

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

    def _get_index_at(self, x: float, y: float = 0.0) -> int:
        """The caret index nearest to the viewport-local point ``(x, y)``."""
        font = self._get_font()
        if font is None:
            return 0

        text = self._state_internal.value.text
        if not text:
            return 0

        lines = self._lines(font, self._wrap_width())
        if self.multiline:
            metrics = font.getMetrics()
            line_h = max(1.0, float(-metrics.fAscent + metrics.fDescent))
            row = int((y + self._scroll_y) // line_h)
            line = lines[max(0, min(row, len(lines) - 1))]
            return index_at(self._get_display_text(text), line, x, self._measure(font))
        return index_at(self._get_display_text(text), lines[0], x + self._scroll_x, self._measure(font))

    def _handle_focus_change(self, focused: bool, source: FocusSource):
        # A focus change (e.g. clicking away, which commits an active
        # composition) ends any input burst, so a pending IME-commit marker
        # must not survive to suppress a later, unrelated Enter.
        self._ime_just_committed = False
        if not focused:
            # Clear the pointer-origin marker so the next keyboard focus
            # acquisition correctly shows the focus ring.
            self._focus_from_pointer = False
        self.invalidate()
        if self._on_focus_change_callback:
            invoke_event_handler(
                self._on_focus_change_callback,
                focused,
                source,
                error_key="editable_text_on_focus_change",
                error_msg="EditableText on_focus_change raised",
                owner_name=type(self).__name__,
            )

    def _filter_input(self, old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        """Run the configured input filter over an insertion.

        Applied where text is *added* -- typing, an IME commit, a paste -- and
        nowhere else. Running it over deletions too would let a whole-string
        rule such as ``matching(r"\\d{3}-\\d{4}")`` reject the backspace that
        breaks the pattern, leaving a field whose contents cannot be erased.
        """
        if self._input_filter is None:
            return new
        try:
            return self._input_filter.apply(old, new)
        except Exception:
            exception_once(_logger, "editable_text_input_filter_raised", "EditableText input_filter raised")
            return new

    def _handle_text(self, text: str) -> bool:
        current_value = self._state_internal.value
        # Typed text never carries a line break: the Enter key is the line
        # break, and the ``'\r'`` some backends send with it would double it.
        new_value = insert_text(current_value, text, filter=self._filter_input)
        if new_value is None:
            return False
        # Committed text delivered while a composition is active means the IME
        # just confirmed the composition (e.g. pressing Enter on a converted
        # candidate). Remember it so the Enter that follows is treated as a
        # commit, not a submit. Plain typing clears any stale marker.
        self._ime_just_committed = current_value.is_composing
        if new_value != current_value:
            self._update_value(new_value)
            return True
        return False

    def _commit_composition(self) -> bool:
        """Commit a pending composition, keeping its text as committed text.

        Called through the focus node when the window loses the OS focus (the
        backend separately discards the OS-side conversation): clearing the
        composing range ends the composition, which also lets ``_announce``
        reconcile the text the application sees. The IME-commit marker is
        dropped either way — after a focus switch, the next Enter in this
        field is a genuine submit.
        """
        self._ime_just_committed = False
        new_value = end_composition(self._state_internal.value)
        if new_value is None:
            return False
        self._update_value(new_value)
        return True

    def _handle_ime_composition(self, text: str, start: int, length: int) -> bool:
        new_value = compose_text(self._state_internal.value, text, start, length)
        if new_value is None:
            return False
        self._update_value(new_value)
        return True

    def _handle_text_motion(self, motion: int, select: bool = False) -> bool:
        # Cursor navigation ends any input burst; drop a pending IME-commit
        # marker so it cannot suppress a later Enter.
        self._ime_just_committed = False
        current = self._state_internal.value
        if self.multiline and motion in (TEXT_MOTION_UP, TEXT_MOTION_DOWN, TEXT_MOTION_HOME, TEXT_MOTION_END):
            return self._move_in_lines(current, motion, select)
        if motion in (TEXT_MOTION_UP, TEXT_MOTION_DOWN):
            return False
        new_value = apply_motion(current, motion, select=select)
        if new_value is None:
            return False
        self._update_value(new_value)
        return True

    def _move_in_lines(self, current: TextEditingValue, motion: int, select: bool) -> bool:
        """Up, Down, Home and End over the lines as wrapped; ``True`` when the caret moved."""
        font = self._get_font()
        if font is None:
            return False
        lines = self._lines(font, self._wrap_width())
        if motion in (TEXT_MOTION_HOME, TEXT_MOTION_END):
            new_value = line_edge(current, lines, end=motion == TEXT_MOTION_END, select=select)
            if new_value is None:
                return False
            self._update_value(new_value)
            return True
        delta = -1 if motion == TEXT_MOTION_UP else 1
        new_value, goal_x = move_lines(
            current, lines, delta, self._measure(font), goal_x=self._goal_x, select=select
        )
        if new_value is None:
            return False
        self._update_value(new_value)
        self._goal_x = goal_x
        return True

    def _handle_key(self, key: str, modifier_keys: int) -> bool:
        current_value = self._state_internal.value

        # Any key press consumes a pending IME-commit marker: the commit's
        # confirming Enter is the very next key event after the commit, so the
        # flag only ever needs to survive a single key press.
        ime_just_committed = self._ime_just_committed
        self._ime_just_committed = False

        if key == "enter":
            # Do not submit when this Enter is confirming an IME composition:
            # either the composition is still active, or it committed on this
            # same keystroke just before the Enter reached us.
            if current_value.is_composing or ime_just_committed:
                return False
            # Shift+Enter is the line break, and never a submit: a single line
            # has nowhere to break, so there it does nothing.
            if modifier_keys & MOD_SHIFT:
                return self._insert_line_break(current_value) if self.multiline else False
            if self._on_submit is None:
                return False
            # Every press, with no "has it changed?" guard: pressing Enter
            # again on the same query means run it again, and only the caller
            # knows whether repeating its work is wasteful.
            invoke_event_handler(
                self._on_submit,
                current_value.text,
                error_key="editable_text_on_submit",
                error_msg="EditableText on_submit raised",
                owner_name=type(self).__name__,
            )
            return True

        if not modifier_keys & (MOD_CTRL | MOD_META):
            return False
        new_value = apply_shortcut(
            current_value, key, get_system_clipboard(), filter=self._filter_input, line_breaks=self.multiline
        )
        if new_value is None:
            return False
        self._update_value(new_value)
        return True

    def _insert_line_break(self, current_value: TextEditingValue) -> bool:
        new_value = insert_text(current_value, "\n", filter=self._filter_input, line_breaks=True)
        if new_value is None or new_value == current_value:
            return True
        self._update_value(new_value)
        return True

    # --- painting --------------------------------------------------------------

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        if canvas is None:
            return

        is_focused = self.state.focused
        current_value = self._state_internal.value
        text = current_value.text
        display_text = self._get_display_text(text)
        selection = current_value.selection

        font = self._get_font()
        if not font:
            return

        font_metrics = font.getMetrics()
        line_h = -font_metrics.fAscent + font_metrics.fDescent
        measure = self._measure(font)
        lines = self._lines(font, self._wrap_width(width))
        caret_line = line_of(lines, selection.end)
        caret_x_in_line = caret_x(display_text, lines[caret_line], selection.end, measure)

        # Scroll so that the caret stays within the viewport, as the
        # platform's inputs do: a single line scrolls sideways under the
        # caret, several lines scroll the caret's line into view.
        margin = 2.0  # Padding so the caret is not flush against the edge.
        if self.multiline:
            scroll_x = 0.0
            scroll_y = self._scroll_y
            total_h = line_h * len(lines)
            if total_h <= height:
                scroll_y = 0.0
            else:
                caret_top = line_h * caret_line
                if caret_top - scroll_y < 0:
                    scroll_y = caret_top
                elif caret_top + line_h - scroll_y > height:
                    scroll_y = caret_top + line_h - height
                scroll_y = max(0.0, min(scroll_y, total_h - height))
            # Lines start at the top; a single line sits centred.
            first_baseline = y - scroll_y - font_metrics.fAscent
        else:
            scroll_y = 0.0
            total_text_width = measure(display_text) if display_text else 0.0
            scroll_x = self._scroll_x
            if total_text_width <= max(0.0, width - margin):
                scroll_x = 0.0
            else:
                # Keep the caret visible.
                if caret_x_in_line - scroll_x < 0:
                    scroll_x = caret_x_in_line
                elif caret_x_in_line - scroll_x > width - margin:
                    scroll_x = caret_x_in_line - (width - margin)
                # Avoid leaving empty space at the right edge.
                max_scroll = max(0.0, total_text_width - (width - margin))
                scroll_x = max(0.0, min(scroll_x, max_scroll))
            first_baseline = y + (height + line_h) / 2 - font_metrics.fDescent
        self._scroll_x = scroll_x
        self._scroll_y = scroll_y

        # Clip drawing to the layout viewport so long text never bleeds
        # outside the field. Use a save/restore scope to avoid disturbing
        # parent clip state.
        clip_rect = make_rect(x, y, width, height)
        save_count = None
        if clip_rect is not None:
            try:
                save_count = canvas.save()
                canvas.clipRect(clip_rect)
            except Exception:
                exception_once(
                    _logger,
                    "editable_text_clip_rect_exc",
                    "EditableText canvas clipRect raised",
                )
                save_count = None

        try:
            from nuiitivet.theme.theme import Theme

            _theme = Theme.of(self)

            paint_sel = None
            if display_text and not selection.is_collapsed:
                paint_sel = make_paint(color=resolve_color_to_rgba(self.selection_color, theme=_theme))
            paint_text = None
            if display_text:
                paint_text = make_paint(color=resolve_color_to_rgba(self.text_color, theme=_theme))

            for i, line in enumerate(lines):
                ty = first_baseline + i * line_h
                if ty + font_metrics.fDescent < y or ty + font_metrics.fAscent > y + height:
                    continue
                line_text = display_text[line.start : line.end]

                # Selection highlight (behind the text). A selection that runs
                # past the line's end also covers the break, as a space would.
                if paint_sel is not None and selection.min <= line.end and selection.max >= line.start:
                    sel_start = max(selection.min, line.start)
                    sel_end = min(selection.max, line.end)
                    sx0 = measure(display_text[line.start : sel_start]) - scroll_x
                    sx1 = measure(display_text[line.start : sel_end]) - scroll_x
                    if selection.max > line.end and i < len(lines) - 1:
                        sx1 += measure(" ")
                    sel_rect = make_rect(int(x + sx0), int(ty + font_metrics.fAscent), int(sx1 - sx0), int(line_h))
                    if sel_rect is not None and sx1 > sx0:
                        try:
                            canvas.drawRect(sel_rect, paint_sel)
                        except Exception:
                            exception_once(
                                _logger,
                                "editable_text_draw_selection_exc",
                                "EditableText selection draw raised",
                            )

                if line_text and paint_text is not None:
                    blob = make_text_blob(line_text, font)
                    if blob:
                        canvas.drawTextBlob(blob, x - scroll_x, ty, paint_text)

            # Draw Cursor
            if is_focused and selection.is_collapsed:
                cursor_x = caret_x_in_line - scroll_x
                ty = first_baseline + caret_line * line_h
                cursor_top = ty + font_metrics.fAscent
                cursor_bottom = ty + font_metrics.fDescent

                # Into this window's IME state, so a focused field in another
                # window cannot race the candidate-window position. A bare
                # tree (offscreen measurement, tests) has no window: skip.
                window = find_window(self)
                if window is not None:
                    window.ime.update_cursor_rect(
                        x + cursor_x,
                        cursor_top,
                        2,
                        cursor_bottom - cursor_top,
                    )

                cursor_color = resolve_color_to_rgba(self.cursor_color, theme=_theme)
                paint_cursor = make_paint(color=cursor_color, style="stroke", stroke_width=2)
                if paint_cursor is not None:
                    canvas.drawLine(
                        x + cursor_x,
                        cursor_top,
                        x + cursor_x,
                        cursor_bottom,
                        paint_cursor,
                    )
        finally:
            if save_count is not None:
                try:
                    canvas.restoreToCount(save_count)
                except Exception:
                    try:
                        canvas.restore()
                    except Exception:
                        exception_once(
                            _logger,
                            "editable_text_canvas_restore_exc",
                            "EditableText canvas restore raised",
                        )

    def _get_display_text(self, text: str) -> str:
        if not self._obscure_text:
            return text
        return "•" * len(text)
