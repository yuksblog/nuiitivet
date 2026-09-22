from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional, Protocol

from nuiitivet.input.codes import (
    TEXT_MOTION_BACKSPACE,
    TEXT_MOTION_DELETE,
    TEXT_MOTION_END,
    TEXT_MOTION_HOME,
    TEXT_MOTION_LEFT,
    TEXT_MOTION_RIGHT,
)


@dataclass(frozen=True)
class TextRange:
    """A range of characters in a string of text.

    Attributes:
        start: The index of the first character in the range.
        end: The index of the character after the last character in the range.
    """

    start: int
    end: int

    @property
    def is_collapsed(self) -> bool:
        """Whether this range represents a cursor position (zero length)."""
        return self.start == self.end

    @property
    def is_normalized(self) -> bool:
        """Whether start is less than or equal to end."""
        return self.start <= self.end

    @property
    def min(self) -> int:
        """The lesser of the start and end values."""
        return self.start if self.start <= self.end else self.end

    @property
    def max(self) -> int:
        """The greater of the start and end values."""
        return self.start if self.start > self.end else self.end

    def text_before(self, text: str) -> str:
        """The text before the range."""
        return text[: self.min]

    def text_after(self, text: str) -> str:
        """The text after the range."""
        return text[self.max :]

    def text_inside(self, text: str) -> str:
        """The text inside the range."""
        return text[self.min : self.max]


@dataclass(frozen=True)
class TextEditingValue:
    """The current state of a TextField.

    Attributes:
        text: The current text string.
        selection: The currently selected range of text.
        composing: The range of text currently being composed (IME).
    """

    text: str = ""
    selection: TextRange = TextRange(0, 0)
    composing: TextRange = TextRange(-1, -1)

    @property
    def is_composing(self) -> bool:
        """Whether there is an active composition range."""
        return self.composing.start != -1 and self.composing.end != -1

    def copy_with(
        self, text: Optional[str] = None, selection: Optional[TextRange] = None, composing: Optional[TextRange] = None
    ) -> TextEditingValue:
        """Creates a copy of this value but with the given fields replaced with the new values."""
        return TextEditingValue(
            text=text if text is not None else self.text,
            selection=selection if selection is not None else self.selection,
            composing=composing if composing is not None else self.composing,
        )


# --- editing -------------------------------------------------------------------
#
# Every operation below is a pure function of a value: it returns the value
# that results, or ``None`` when the input changes nothing. ``EditableText``
# runs them over its observable state and the dev runner's inline field over a
# plain value, so a caret, a selection, a composition and the clipboard behave
# the same in both, and a fix lands in both.

#: Runs over an insertion -- typing, an IME commit, a paste -- with the value
#: before and after it, and returns the value to adopt.
InsertFilter = Callable[["TextEditingValue", "TextEditingValue"], "TextEditingValue"]


class ClipboardLike(Protocol):
    """What the clipboard shortcuts need of a clipboard."""

    def get_text(self) -> str: ...

    def set_text(self, text: str) -> None: ...


def normalize_input(text: str, *, line_breaks: bool = False) -> str:
    """Drop Unicode control characters (category ``Cc``) from *text*.

    Backends do not filter them uniformly: on macOS, Return reaches ``on_text``
    as ``'\\r'`` through a path that skips the guard every other key gets.
    With *line_breaks*, ``'\\r\\n'`` and a lone ``'\\r'`` become ``'\\n'`` and
    every ``'\\n'`` stays; without it, line breaks go with the rest.
    """
    if line_breaks:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(ch for ch in text if (line_breaks and ch == "\n") or unicodedata.category(ch) != "Cc")


def line_bounds(text: str, index: int) -> TextRange:
    """The line holding *index*: from after the previous ``'\\n'`` to the next one, excluded."""
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    return TextRange(start, len(text) if end < 0 else end)


def insert_text(
    value: TextEditingValue, text: str, *, filter: Optional[InsertFilter] = None, line_breaks: bool = False
) -> Optional[TextEditingValue]:
    """Insert committed *text* over the composition, or else over the selection.

    Control characters are dropped first, line breaks among them unless
    *line_breaks* keeps them (see :func:`normalize_input`); ``None`` when
    nothing is left. The composition ends, and the caret lands after the
    insertion. A caller that must tell an IME's confirming Enter from a submit
    remembers ``value.is_composing`` at this call: on macOS the commit arrives
    here before that Enter's key press.
    """
    text = normalize_input(text, line_breaks=line_breaks)
    if not text:
        return None
    replaced = value.composing if value.is_composing else value.selection
    caret = replaced.min + len(text)
    new = value.copy_with(
        text=replaced.text_before(value.text) + text + replaced.text_after(value.text),
        selection=TextRange(caret, caret),
        composing=TextRange(-1, -1),
    )
    return filter(value, new) if filter is not None else new


def compose_text(value: TextEditingValue, text: str, start: int, length: int) -> Optional[TextEditingValue]:
    """Show the input method's uncommitted *text*, with its own selection inside it.

    The first update replaces the selection, later ones the composition. An
    empty update ends the composition: the IME cancelled, or echoed the
    discard that follows a focus loss. ``None`` when there is no composition
    to end.
    """
    text = normalize_input(text)
    if not text:
        if not value.is_composing:
            return None
        caret = value.composing.min
        return value.copy_with(
            text=value.composing.text_before(value.text) + value.composing.text_after(value.text),
            selection=TextRange(caret, caret),
            composing=TextRange(-1, -1),
        )
    replaced = value.composing if value.is_composing else value.selection
    prefix = replaced.text_before(value.text)
    begin = len(prefix)
    return value.copy_with(
        text=prefix + text + replaced.text_after(value.text),
        selection=TextRange(begin + start, begin + start + length),
        composing=TextRange(begin, begin + len(text)),
    )


def end_composition(value: TextEditingValue) -> Optional[TextEditingValue]:
    """Keep the composition's text as committed text. ``None`` with none open."""
    if not value.is_composing:
        return None
    return value.copy_with(composing=TextRange(-1, -1))


def apply_motion(value: TextEditingValue, motion: int, *, select: bool = False) -> Optional[TextEditingValue]:
    """Move the caret, extend the selection, or erase one character.

    ``TEXT_MOTION_BACKSPACE`` and ``TEXT_MOTION_DELETE`` erase the selection
    when there is one, else the character before or after the caret. The
    others move the selection's end, collapsing it unless *select* holds it;
    an unselecting move out of a selection lands on its near edge. ``HOME``
    and ``END`` stop at the caret's line. ``None`` when nothing changes, and
    for a vertical motion, which needs the text's layout.
    """
    text, selection = value.text, value.selection
    if motion in (TEXT_MOTION_BACKSPACE, TEXT_MOTION_DELETE):
        if not selection.is_collapsed:
            return _replace(value, selection, "")
        if motion == TEXT_MOTION_BACKSPACE:
            return _replace(value, TextRange(selection.min - 1, selection.min), "") if selection.min > 0 else None
        return _replace(value, TextRange(selection.max, selection.max + 1), "") if selection.max < len(text) else None

    focus = selection.end
    if motion == TEXT_MOTION_LEFT:
        if not select and not selection.is_collapsed:
            focus = selection.min
        elif focus > 0:
            focus -= 1
    elif motion == TEXT_MOTION_RIGHT:
        if not select and not selection.is_collapsed:
            focus = selection.max
        elif focus < len(text):
            focus += 1
    elif motion == TEXT_MOTION_HOME:
        focus = line_bounds(text, focus).start
    elif motion == TEXT_MOTION_END:
        focus = line_bounds(text, focus).end
    else:
        return None
    moved = TextRange(selection.start, focus) if select else TextRange(focus, focus)
    return value.copy_with(selection=moved) if moved != selection else None


def apply_shortcut(
    value: TextEditingValue,
    key: str,
    clipboard: ClipboardLike,
    *,
    filter: Optional[InsertFilter] = None,
    line_breaks: bool = False,
) -> Optional[TextEditingValue]:
    """The accelerator's ``a`` / ``c`` / ``x`` / ``v``: select all, copy, cut, paste.

    The caller has checked the accelerator; *key* is the normalized name. A
    paste is normalized as an insertion is, keeping its line breaks only with
    *line_breaks*. The value returned is the one to adopt, unchanged for a
    copy, and ``None`` names a key that is not a shortcut.
    """
    text, selection = value.text, value.selection
    if key == "a":
        return value.copy_with(selection=TextRange(0, len(text)))
    if key == "c":
        if not selection.is_collapsed:
            clipboard.set_text(selection.text_inside(text))
        return value
    if key == "x":
        if selection.is_collapsed:
            return value
        clipboard.set_text(selection.text_inside(text))
        return _replace(value, selection, "")
    if key == "v":
        pasted = normalize_input(clipboard.get_text() or "", line_breaks=line_breaks)
        if not pasted:
            return value
        new = _replace(value, selection, pasted)
        return filter(value, new) if filter is not None else new
    return None


def _replace(value: TextEditingValue, span: TextRange, text: str) -> TextEditingValue:
    caret = span.min + len(text)
    return value.copy_with(
        text=span.text_before(value.text) + text + span.text_after(value.text), selection=TextRange(caret, caret)
    )
