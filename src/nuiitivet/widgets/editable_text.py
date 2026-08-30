from __future__ import annotations

import logging
import unicodedata
from typing import Optional, Tuple, Union, cast

from nuiitivet.input.pointer import PointerEvent
from nuiitivet.widgeting.widget import Widget
from nuiitivet.widgeting.callbacks import invoke_event_handler, StrCallback
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
from nuiitivet.widgets.text_editing import TextEditingValue, TextRange
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


def _strip_control_chars(text: str) -> str:
    """Remove Unicode control characters (category ``Cc``) from ``text``.

    Backends do not uniformly filter control characters out of the text they
    deliver. On macOS, for example, pressing Return dispatches ``on_text('\\r')``
    through a code path that bypasses the control-character guard applied to
    every other key (see issue #307). Filtering here keeps the widget's value
    free of stray control characters regardless of which backend feeds it.

    ``EditableText`` is single-line only, so newlines are dropped as well. When
    multi-line support lands, ``'\\r'`` should be normalized to ``'\\n'`` and only
    ``'\\n'`` permitted, rather than allowing raw control characters through here.
    """
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cc")


class EditableText(InteractionHostMixin, Widget):
    """
    A basic text input widget that handles text editing, selection, and cursor rendering.
    It does not include any decoration (borders, labels, etc.).
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

        # Horizontal scroll offset (pixels) used to keep the cursor visible
        # when the text exceeds the available width.
        self._scroll_x: float = 0.0
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
                self.invalidate()
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

        self._state_internal.value = new_value
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

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        font = self._get_font()
        if not font:
            return (0, 0)

        text = self._state_internal.value.text
        display_text = self._get_display_text(text)
        # If empty, measure a dummy character to get height
        measure_text = display_text if display_text else "M"

        width = int(font.measureText(measure_text)) if display_text else 0
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
        if self.global_layout_rect:
            local_x -= self.global_layout_rect[0]
        return self._get_index_at(local_x)

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

        display_text = self._get_display_text(text)

        # Translate viewport-local x into text-coordinate space.
        text_x = x + self._scroll_x

        if text_x < 0:
            return 0

        for i in range(len(text) + 1):
            sub = display_text[:i]
            w = font.measureText(sub)
            if w > text_x:
                prev_w = font.measureText(display_text[: i - 1]) if i > 0 else 0
                if text_x - prev_w < w - text_x:
                    return i - 1
                return i

        return len(text)

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
        text = _strip_control_chars(text)
        if not text:
            return False

        current_value = self._state_internal.value
        selection = current_value.selection
        full_text = current_value.text

        # Committed text delivered while a composition is active means the IME
        # just confirmed the composition (e.g. pressing Enter on a converted
        # candidate). Remember it so the Enter that follows is treated as a
        # commit, not a submit. Plain typing clears any stale marker.
        self._ime_just_committed = current_value.is_composing

        if current_value.is_composing:
            range_to_replace = current_value.composing
            new_text = range_to_replace.text_before(full_text) + text + range_to_replace.text_after(full_text)
            new_cursor_pos = range_to_replace.start + len(text)
        else:
            new_text = selection.text_before(full_text) + text + selection.text_after(full_text)
            new_cursor_pos = selection.min + len(text)

        new_value = self._filter_input(
            current_value,
            current_value.copy_with(
                text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos), composing=TextRange(-1, -1)
            ),
        )

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
        current_value = self._state_internal.value
        if not current_value.is_composing:
            return False
        self._update_value(current_value.copy_with(composing=TextRange(-1, -1)))
        return True

    def _handle_ime_composition(self, text: str, start: int, length: int) -> bool:
        text = _strip_control_chars(text)

        current_value = self._state_internal.value
        full_text = current_value.text

        # An empty update ends the composition rather than leaving an empty
        # composing range active (which would keep holding back announcements
        # and Enter handling): the IME cancelled, or echoed the discard that
        # follows a focus-loss commit. With no composition open there is
        # nothing to do at all.
        if not text:
            if not current_value.is_composing:
                return False
            range_to_replace = current_value.composing
            caret = range_to_replace.min
            self._update_value(
                current_value.copy_with(
                    text=range_to_replace.text_before(full_text) + range_to_replace.text_after(full_text),
                    selection=TextRange(caret, caret),
                    composing=TextRange(-1, -1),
                )
            )
            return True

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
        # Cursor navigation ends any input burst; drop a pending IME-commit
        # marker so it cannot suppress a later Enter.
        self._ime_just_committed = False

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

    def _handle_key(self, key: str, modifier_keys: int) -> bool:
        current_value = self._state_internal.value

        # Any key press consumes a pending IME-commit marker: the commit's
        # confirming Enter is the very next key event after the commit, so the
        # flag only ever needs to survive a single key press.
        ime_just_committed = self._ime_just_committed
        self._ime_just_committed = False

        if key == "enter":
            # Enter confirms the text. EditableText is single-line, so Enter
            # never inserts a newline; the value is left untouched (see #307).
            # Do not submit when this Enter is confirming an IME composition:
            # either the composition is still active, or it committed on this
            # same keystroke just before the Enter reached us.
            if current_value.is_composing or ime_just_committed:
                return False
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

        is_ctrl = bool(modifier_keys & (MOD_CTRL | MOD_META))

        if not is_ctrl:
            return False

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
                new_value = self._filter_input(
                    current_value,
                    current_value.copy_with(text=new_text, selection=TextRange(new_cursor_pos, new_cursor_pos)),
                )
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
        display_text = self._get_display_text(text)
        selection = current_value.selection

        font = self._get_font()
        if not font:
            return

        font_metrics = font.getMetrics()
        # Align text vertically centered in the available height
        text_height = -font_metrics.fAscent + font_metrics.fDescent
        ty = y + (height + text_height) / 2 - font_metrics.fDescent

        # Compute scroll offset so that the cursor remains within the visible
        # viewport, mirroring the behavior of single-line text inputs in the
        # platform: long values are not truncated mid-glyph but are scrolled
        # horizontally as the cursor moves.
        cursor_x_in_text = font.measureText(display_text[: selection.end])
        total_text_width = font.measureText(display_text) if display_text else 0.0
        margin = 2.0  # Padding so the caret is not flush against the edge.
        scroll = self._scroll_x
        if total_text_width <= max(0.0, width - margin):
            scroll = 0.0
        else:
            # Keep the caret visible.
            if cursor_x_in_text - scroll < 0:
                scroll = cursor_x_in_text
            elif cursor_x_in_text - scroll > width - margin:
                scroll = cursor_x_in_text - (width - margin)
            # Avoid leaving empty space at the right edge.
            max_scroll = max(0.0, total_text_width - (width - margin))
            scroll = max(0.0, min(scroll, max_scroll))
        self._scroll_x = scroll

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

            # Draw selection highlight (behind the text).
            if display_text and not selection.is_collapsed:
                sel_start = max(0, min(selection.min, len(display_text)))
                sel_end = max(0, min(selection.max, len(display_text)))
                if sel_end > sel_start:
                    sx0 = font.measureText(display_text[:sel_start]) - scroll
                    sx1 = font.measureText(display_text[:sel_end]) - scroll
                    sel_top = ty + font_metrics.fAscent
                    sel_bottom = ty + font_metrics.fDescent
                    sel_color = resolve_color_to_rgba(self.selection_color, theme=_theme)
                    paint_sel = make_paint(color=sel_color)
                    sel_rect = make_rect(int(x + sx0), int(sel_top), int(sx1 - sx0), int(sel_bottom - sel_top))
                    if sel_rect is not None and paint_sel is not None:
                        try:
                            canvas.drawRect(sel_rect, paint_sel)
                        except Exception:
                            exception_once(
                                _logger,
                                "editable_text_draw_selection_exc",
                                "EditableText selection draw raised",
                            )

            # Draw Text
            if display_text:
                text_color = resolve_color_to_rgba(self.text_color, theme=_theme)
                paint_text = make_paint(color=text_color)
                blob = make_text_blob(display_text, font)
                if blob:
                    canvas.drawTextBlob(blob, x - scroll, ty, paint_text)

            # Draw Cursor
            if is_focused and selection.is_collapsed:
                cursor_x = cursor_x_in_text - scroll

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
