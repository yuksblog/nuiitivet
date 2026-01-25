from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
