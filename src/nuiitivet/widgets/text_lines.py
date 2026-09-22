"""Lines of a text under edit: where they break, and where a caret sits in them.

Pure functions over a text and a width measurer, so ``EditableText`` and the
dev runner's inline field lay their lines out the same way and the caret
moves the same way in both. A line is a :class:`TextRange` of the text: it
ends before the ``'\\n'`` that breaks it, or where the width ran out.
"""

from __future__ import annotations

import unicodedata
from typing import Callable, Optional, Sequence

from nuiitivet.widgets.text_editing import TextEditingValue, TextRange

#: The advance width of a string, in the caller's units.
Measure = Callable[[str], float]


def break_lines(text: str, measure: Measure, width: Optional[float] = None) -> list[TextRange]:
    """Split *text* into lines: at every ``'\\n'``, and where a line would exceed *width*.

    A soft break lands after the last space that fits, or before an ideographic
    character; a run with no such place breaks at the character. Every line
    keeps at least one character, so a narrow width never loops. ``None``
    never breaks softly. The result is never empty: an empty text is one
    empty line.
    """
    lines: list[TextRange] = []
    start = 0
    while True:
        end = text.find("\n", start)
        hard_end = len(text) if end < 0 else end
        lines.extend(_wrap(text, start, hard_end, measure, width))
        if end < 0:
            return lines
        start = end + 1


def _wrap(text: str, start: int, end: int, measure: Measure, width: Optional[float]) -> list[TextRange]:
    if width is None or measure(text[start:end]) <= width:
        return [TextRange(start, end)]
    lines: list[TextRange] = []
    line_start = start
    opportunity = -1
    i = start
    while i < end:
        ch = text[i]
        # A space may hang past the edge, so a line never opens with one.
        if not ch.isspace() and i > line_start and measure(text[line_start : i + 1]) > width:
            cut = opportunity if opportunity > line_start else i
            lines.append(TextRange(line_start, cut))
            line_start = cut
            opportunity = -1
            i = cut
            continue
        if ch.isspace():
            opportunity = i + 1
        elif _is_ideographic(ch):
            # A break is allowed on either side of an ideograph.
            if i > line_start:
                opportunity = i
            if i + 1 <= end:
                opportunity = max(opportunity, i + 1)
        i += 1
    lines.append(TextRange(line_start, end))
    return lines


def _is_ideographic(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")


def line_of(lines: Sequence[TextRange], index: int) -> int:
    """The line whose text holds the caret at *index*.

    A caret at a soft break sits on the line that follows it, so typing at a
    wrapped line's end continues on the next line. The last line takes its own
    end.
    """
    last = len(lines) - 1
    for i, line in enumerate(lines):
        if index < line.end or (index == line.end and (i == last or _hard_break_after(lines, i))):
            return i
    return last


def _hard_break_after(lines: Sequence[TextRange], i: int) -> bool:
    return lines[i + 1].start > lines[i].end


def caret_x(text: str, line: TextRange, index: int, measure: Measure) -> float:
    """The x of the caret at *index* within *line*, from the line's left edge."""
    return measure(text[line.start : max(line.start, min(index, line.end))])


def index_at(text: str, line: TextRange, x: float, measure: Measure) -> int:
    """The caret index in *line* nearest to *x* from its left edge."""
    if x <= 0:
        return line.start
    prev_w = 0.0
    for i in range(line.start + 1, line.end + 1):
        w = measure(text[line.start : i])
        if w > x:
            return i - 1 if x - prev_w < w - x else i
        prev_w = w
    return line.end


def move_lines(
    value: TextEditingValue,
    lines: Sequence[TextRange],
    delta: int,
    measure: Measure,
    *,
    goal_x: Optional[float] = None,
    select: bool = False,
) -> tuple[Optional[TextEditingValue], Optional[float]]:
    """Move the caret *delta* lines, keeping its x; extend the selection with *select*.

    *goal_x* is the x a run of vertical moves aims for, so a short line in
    between does not pull the caret left for good; the second value returned
    is the x to pass to the next move. Above the first line the caret goes to
    the start of the text, below the last to its end. The first value is
    ``None`` when nothing moves.
    """
    text, selection = value.text, value.selection
    focus = selection.end
    current = line_of(lines, focus)
    x = caret_x(text, lines[current], focus, measure) if goal_x is None else goal_x
    target = current + delta
    if target < 0:
        moved_to = 0
    elif target >= len(lines):
        moved_to = len(text)
    else:
        moved_to = index_at(text, lines[target], x, measure)
    moved = TextRange(selection.start, moved_to) if select else TextRange(moved_to, moved_to)
    if moved == selection:
        return None, x
    return value.copy_with(selection=moved), x


def line_edge(
    value: TextEditingValue, lines: Sequence[TextRange], *, end: bool, select: bool
) -> Optional[TextEditingValue]:
    """Move the caret to its line's start, or with *end* its end; ``None`` when it is there."""
    selection = value.selection
    line = lines[line_of(lines, selection.end)]
    focus = line.end if end else line.start
    moved = TextRange(selection.start, focus) if select else TextRange(focus, focus)
    return value.copy_with(selection=moved) if moved != selection else None


__all__ = [
    "Measure",
    "break_lines",
    "caret_x",
    "index_at",
    "line_edge",
    "line_of",
    "move_lines",
]
