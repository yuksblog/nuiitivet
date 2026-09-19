"""The single-line text field the dev modes open over the glass.

Layout edit mode opens it over a widget's text literal, comment mode over a
mark. It never enters the widget tree: the mode feeds it typed text, the input
method's composition and keys by name, and it runs the editing operations
``EditableText`` runs. The mode decides what a commit writes to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from nuiitivet.input.codes import MOD_SHIFT, resolve_modifiers, text_motion_for_key
from nuiitivet.platform import get_system_clipboard
from nuiitivet.widgets.text_editing import (
    TextEditingValue,
    TextRange,
    apply_motion,
    apply_shortcut,
    compose_text,
    insert_text,
)

from .gesture import accel_held
from .hud import CAPTION_BG, CAPTION_INK, FONT_SIZE, color

Rect = tuple[float, float, float, float]

#: What one key did to the field: it asked to commit, to cancel, or neither.
Outcome = Optional[Literal["commit", "cancel"]]


@dataclass
class InlineField:
    """The text under edit: ``value`` holds the text, the selection whose end is the caret, and the composing range."""

    value: TextEditingValue
    # Set by the commit that confirms a composition, which on macOS arrives
    # before that Enter's key press; read once by the next key.
    ime_just_committed: bool = False

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
        """Insert typed text at the caret, replacing any selection."""
        self.ime_just_committed = self.value.is_composing
        inserted = insert_text(self.value, text)
        if inserted is not None:
            self.value = inserted

    def compose(self, text: str, start: int, length: int) -> None:
        """Show the input method's uncommitted text at the caret."""
        composed = compose_text(self.value, text, start, length)
        if composed is not None:
            self.value = composed

    def key(self, key: str, modifier_keys: int) -> Outcome:
        """Apply one named key and return what it asked for.

        ``Enter`` asks to commit, unless ``Shift`` is held or it is the ``Enter``
        that confirms a composition; ``Escape`` asks to cancel; any other key edits
        in place.
        """
        just_committed, self.ime_just_committed = self.ime_just_committed, False
        shift = bool(resolve_modifiers(int(modifier_keys)) & MOD_SHIFT)
        if key == "escape":
            return "cancel"
        if key == "enter":
            if shift or self.value.is_composing or just_committed:
                return None
            return "commit"
        motion = text_motion_for_key(key)
        if motion is not None:
            moved = apply_motion(self.value, motion, select=shift)
            if moved is not None:
                self.value = moved
        elif accel_held(modifier_keys):
            changed = apply_shortcut(self.value, key, get_system_clipboard())
            if changed is not None:
                self.value = changed
        return None


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
    """Draw the field at ``rect``, its least size; the box grows to fit the text.

    The caret's rect is published to the window's IME state, so the candidate
    window opens beside it.
    """
    from nuiitivet.rendering.skia.font import make_text_blob, measure_text_width

    x, y, w, h = rect
    pad = 8.0
    text, selection = value.text, value.selection

    def at(index: int) -> float:
        return x + pad + measure_text_width(typeface, FONT_SIZE, text[:index])

    box_w = max(w, measure_text_width(typeface, FONT_SIZE, text) + pad * 2)
    box_h = max(h, 24.0)
    fill = skia.Paint(AntiAlias=True)
    fill.setColor(skia.Color(*CAPTION_BG))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, box_w, box_h), 5.0, 5.0, fill)
    edge = skia.Paint(AntiAlias=True)
    edge.setStyle(skia.Paint.kStroke_Style)
    edge.setStrokeWidth(2.0)
    edge.setColor(color(skia, accent, 0.95))
    canvas.drawRoundRect(skia.Rect.MakeXYWH(x, y, box_w, box_h), 5.0, 5.0, edge)
    if not selection.is_collapsed:
        highlight = skia.Paint(AntiAlias=True)
        highlight.setColor(color(skia, accent, 0.3))
        left, right = at(selection.min), at(selection.max)
        canvas.drawRect(skia.Rect.MakeXYWH(left, y + 4.0, right - left, box_h - 8.0), highlight)
    baseline = y + box_h / 2.0 + FONT_SIZE / 2.5
    blob = make_text_blob(text, font)
    if blob is not None:
        ink = skia.Paint(AntiAlias=True)
        ink.setColor(color(skia, CAPTION_INK, 1.0))
        canvas.drawTextBlob(blob, x + pad, baseline, ink)
    stroke = skia.Paint(AntiAlias=True)
    stroke.setStrokeWidth(1.5)
    stroke.setColor(color(skia, accent, 1.0))
    if value.is_composing:
        canvas.drawLine(at(value.composing.min), baseline + 3.0, at(value.composing.max), baseline + 3.0, stroke)
    caret_x = at(selection.end)
    if selection.is_collapsed:
        canvas.drawLine(caret_x, y + 4.0, caret_x, y + box_h - 4.0, stroke)
    ime = getattr(app, "ime", None)
    if ime is not None:
        ime.update_cursor_rect(caret_x, y + 4.0, 2.0, box_h - 8.0)


__all__ = ["InlineField", "Outcome", "paint_field"]
