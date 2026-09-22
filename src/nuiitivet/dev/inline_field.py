"""The text field the dev modes open over the glass.

Layout edit mode opens it over a widget's text literal, comment mode over a
mark. It never enters the widget tree: the mode feeds it typed text, the input
method's composition and keys by name, and it runs the editing operations
``EditableText`` runs. It takes several lines, broken by ``Shift+Enter`` and
never wrapped: the box grows to fit. The mode decides what a commit writes to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from nuiitivet.input.codes import (
    MOD_SHIFT,
    TEXT_MOTION_DOWN,
    TEXT_MOTION_UP,
    resolve_modifiers,
    text_motion_for_key,
)
from nuiitivet.platform import get_system_clipboard
from nuiitivet.widgets.text_editing import (
    TextEditingValue,
    TextRange,
    apply_motion,
    apply_shortcut,
    compose_text,
    insert_text,
)
from nuiitivet.widgets.text_lines import break_lines, caret_x, line_of, move_lines

from .gesture import accel_held
from .hud import CAPTION_BG, CAPTION_INK, FONT_SIZE, color

Rect = tuple[float, float, float, float]

#: What one key did to the field: it asked to commit, to cancel, or neither.
Outcome = Optional[Literal["commit", "cancel"]]

# The field's height with one line, and what each further line adds.
_BOX_H = 24.0
_LINE_H = 16.0


def measure(text: str) -> float:
    """The width of *text* at the HUD's font, or its length where no font can be loaded."""
    try:
        from nuiitivet.rendering.skia.font import get_default_font_fallbacks, get_typeface, measure_text_width

        typeface = get_typeface(family_candidates=get_default_font_fallbacks(), fallback_to_default=True)
        if typeface is not None:
            return float(measure_text_width(typeface, FONT_SIZE, text))
    except Exception:
        pass
    return float(len(text))


@dataclass
class InlineField:
    """The text under edit: ``value`` holds the text, the selection whose end is the caret, and the composing range."""

    value: TextEditingValue
    # Set by the commit that confirms a composition, which on macOS arrives
    # before that Enter's key press; read once by the next key.
    ime_just_committed: bool = False
    # The x a run of Up/Down aims for; any other edit drops it.
    goal_x: Optional[float] = None

    @classmethod
    def open(cls, text: str) -> InlineField:
        """A field holding ``text`` with the caret at its end."""
        caret = TextRange(len(text), len(text))
        return cls(TextEditingValue(text, caret))

    @property
    def text(self) -> str:
        """The text as it stands, composition included."""
        return self.value.text

    def type(self, text: str) -> None:
        """Insert typed text at the caret, replacing any selection. A line break comes from the key, not from here."""
        self.ime_just_committed = self.value.is_composing
        inserted = insert_text(self.value, text)
        if inserted is not None:
            self._adopt(inserted)

    def compose(self, text: str, start: int, length: int) -> None:
        """Show the input method's uncommitted text at the caret."""
        composed = compose_text(self.value, text, start, length)
        if composed is not None:
            self._adopt(composed)

    def key(self, key: str, modifier_keys: int) -> Outcome:
        """Apply one named key and return what it asked for.

        ``Enter`` asks to commit, unless it is the ``Enter`` that confirms a
        composition; ``Shift+Enter`` breaks the line; ``Escape`` asks to
        cancel; any other key edits in place.
        """
        just_committed, self.ime_just_committed = self.ime_just_committed, False
        shift = bool(resolve_modifiers(int(modifier_keys)) & MOD_SHIFT)
        if key == "escape":
            return "cancel"
        if key == "enter":
            if self.value.is_composing or just_committed:
                return None
            if not shift:
                return "commit"
            broken = insert_text(self.value, "\n", line_breaks=True)
            if broken is not None:
                self._adopt(broken)
            return None
        motion = text_motion_for_key(key)
        if motion in (TEXT_MOTION_UP, TEXT_MOTION_DOWN):
            lines = break_lines(self.value.text, measure)
            moved, goal_x = move_lines(
                self.value, lines, -1 if motion == TEXT_MOTION_UP else 1, measure, goal_x=self.goal_x, select=shift
            )
            if moved is not None:
                self.value = moved
            self.goal_x = goal_x
        elif motion is not None:
            moved = apply_motion(self.value, motion, select=shift)
            if moved is not None:
                self._adopt(moved)
        elif accel_held(modifier_keys):
            changed = apply_shortcut(self.value, key, get_system_clipboard(), line_breaks=True)
            if changed is not None:
                self._adopt(changed)
        return None

    def _adopt(self, value: TextEditingValue) -> None:
        self.value = value
        self.goal_x = None


def paint_field(
    skia: Any,
    canvas: Any,
    app: Any,
    rect: Rect,
    value: TextEditingValue,
    accent: tuple[int, int, int],
    font: Any,
    typeface: Any,
) -> None:
    """Draw the field at ``rect``, its least size; the box grows to fit the text, a line per ``'\\n'``.

    The caret's rect is published to the window's IME state, so the candidate
    window opens beside it.
    """
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    x, y, w, h = rect
    pad = 8.0
    text, selection = value.text, value.selection
    lines = break_lines(text, measure)

    def width_of(s: str) -> float:
        return float(measure_text_width(typeface, FONT_SIZE, s))

    def at(index: int) -> tuple[int, float]:
        row = line_of(lines, index)
        return row, x + pad + caret_x(text, lines[row], index, width_of)

    def baseline_of(row: int) -> float:
        return y + _BOX_H / 2.0 + FONT_SIZE / 2.5 + row * _LINE_H

    box_w = max(w, max(width_of(text[line.start : line.end]) for line in lines) + pad * 2)
    box_h = max(h, _BOX_H + (len(lines) - 1) * _LINE_H)
    fill = skia.Paint(AntiAlias=True)
    fill.setColor(skia.Color(*CAPTION_BG))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, box_w, box_h), 5.0, 5.0, fill)
    edge = skia.Paint(AntiAlias=True)
    edge.setStyle(skia.Paint.kStroke_Style)
    edge.setStrokeWidth(2.0)
    edge.setColor(color(skia, accent, 0.95))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, box_w, box_h), 5.0, 5.0, edge)
    ink = skia.Paint(AntiAlias=True)
    ink.setColor(color(skia, CAPTION_INK, 1.0))
    highlight = skia.Paint(AntiAlias=True)
    highlight.setColor(color(skia, accent, 0.3))
    stroke = skia.Paint(AntiAlias=True)
    stroke.setStrokeWidth(1.5)
    stroke.setColor(color(skia, accent, 1.0))
    for row, line in enumerate(lines):
        baseline = baseline_of(row)
        top = baseline - _BOX_H / 2.0 - FONT_SIZE / 2.5 + 4.0
        if not selection.is_collapsed and selection.min <= line.end and selection.max >= line.start:
            left = x + pad + caret_x(text, line, max(selection.min, line.start), width_of)
            right = x + pad + caret_x(text, line, min(selection.max, line.end), width_of)
            if selection.max > line.end and row < len(lines) - 1:
                right += width_of(" ")
            canvas.drawRect(skia.Rect.MakeXYWH(left, top, right - left, _BOX_H - 8.0), highlight)
        blob = make_text_blob(text[line.start : line.end], font)
        if blob is not None:
            canvas.drawTextBlob(blob, x + pad, baseline, ink)
        if value.is_composing and value.composing.min <= line.end and value.composing.max >= line.start:
            left = x + pad + caret_x(text, line, max(value.composing.min, line.start), width_of)
            right = x + pad + caret_x(text, line, min(value.composing.max, line.end), width_of)
            canvas.drawLine(left, baseline + 3.0, right, baseline + 3.0, stroke)
    caret_row, caret_px = at(selection.end)
    caret_top = baseline_of(caret_row) - _BOX_H / 2.0 - FONT_SIZE / 2.5 + 4.0
    if selection.is_collapsed:
        canvas.drawLine(caret_px, caret_top, caret_px, caret_top + _BOX_H - 8.0, stroke)
    ime = getattr(app, "ime", None)
    if ime is not None:
        ime.update_cursor_rect(caret_px, caret_top, 2.0, _BOX_H - 8.0)


__all__ = ["InlineField", "Outcome", "measure", "paint_field"]
