"""Input filters: rules applied to text as the user types it.

An input filter sits between a keystroke and the widget's value. It runs on
every insertion -- typing, an IME commit, a paste -- and decides what actually
lands in the field.

A filter defines **what is typeable, not what is valid**. The two are not the
same: a decimal field must let ``"1."`` be typed even though it is not a valid
decimal, because otherwise the ``.`` can never be entered. Rules about whether
a *finished* value is acceptable belong in ``is_error`` / ``error_text``, and
rules that reshape a finished value belong in ``on_submit``.

Filters are applied to user input only. A value the application assigns --
the initial ``value``, or a write to a bound observable -- is passed through
untouched: the field never silently rewrites what its owner put there.

Composition uses ``|``, matching the modifier vocabulary::

    input_filter=digits_only() | max_length(4)

The character-level filters (:func:`allow`, :func:`deny`, :func:`digits_only`)
know exactly which characters they removed and move the caret accordingly. A
bare ``Callable[[str], str]`` is accepted as a shorthand and adapted, but it
reports only the resulting string, so its caret is inferred from the length
change. That is exact for same-length rewrites (upper-casing, transliteration)
and approximate otherwise.

Masking -- displaying ``1,234,567`` while storing ``"1234567"`` -- is out of
scope. It needs the displayed and stored text to differ, which a filter cannot
express: whatever a filter returns *is* the value.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Callable, Pattern, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgets.text_editing import TextEditingValue, TextRange

_logger = logging.getLogger(__name__)


def _clamp(index: int, length: int) -> int:
    return 0 if index < 0 else (length if index > length else index)


class InputFilter(ABC):
    """A rule applied to text as the user types it.

    Subclasses implement :meth:`apply`, which receives the value before the
    edit and the value the edit proposes, and returns the value to accept.
    Returning ``old`` rejects the edit outright; returning ``new`` accepts it
    unchanged.
    """

    __slots__ = ()

    @abstractmethod
    def apply(self, old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        """Return the value to accept for an edit from ``old`` to ``new``."""

    def __or__(self, other: "InputFilterLike") -> "InputFilter":
        return _ChainedFilter((self, to_input_filter(other)))

    def __ror__(self, other: "InputFilterLike") -> "InputFilter":
        return _ChainedFilter((to_input_filter(other), self))


InputFilterLike = Union[InputFilter, Callable[[str], str]]
"""An :class:`InputFilter`, or a plain ``str -> str`` callable standing in for one."""


def to_input_filter(filter_like: InputFilterLike) -> InputFilter:
    """Adapt a ``str -> str`` callable to an :class:`InputFilter`, or pass one through."""
    if isinstance(filter_like, InputFilter):
        return filter_like
    return _CallableFilter(filter_like)


class _ChainedFilter(InputFilter):
    """Applies filters left to right, each seeing the previous one's result."""

    __slots__ = ("_filters",)

    _filters: tuple[InputFilter, ...]

    def __init__(self, filters: tuple[InputFilter, ...]) -> None:
        # Flatten so ``a | b | c`` is one chain rather than a nested pair. The
        # filters are pure, so the order of application is all that matters.
        flat: list[InputFilter] = []
        for f in filters:
            if isinstance(f, _ChainedFilter):
                flat.extend(f._filters)
            else:
                flat.append(f)
        self._filters = tuple(flat)

    def apply(self, old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        current = new
        for f in self._filters:
            current = f.apply(old, current)
        return current


class _CallableFilter(InputFilter):
    """Adapts a ``str -> str`` callable, inferring the caret from the length change.

    The callable reports only the resulting text, so where the characters it
    removed or added were is unknown. Shifting the caret by the length delta is
    exact for a rewrite that preserves length and correct for a rule that only
    edits at or before the caret, which covers the shorthand's intended uses.
    """

    __slots__ = ("_fn",)

    def __init__(self, fn: Callable[[str], str]) -> None:
        self._fn = fn

    def apply(self, old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        try:
            text = self._fn(new.text)
        except Exception:
            exception_once(_logger, "input_filter_callable_raised", "input_filter callable raised")
            return new
        if text == new.text:
            return new

        delta = len(text) - len(new.text)
        start = _clamp(new.selection.start + delta, len(text))
        end = _clamp(new.selection.end + delta, len(text))
        return new.copy_with(text=text, selection=TextRange(start, end))


class _CharacterFilter(InputFilter):
    """Keeps or drops individual characters, tracking the caret exactly."""

    __slots__ = ("_pattern", "_keep_matching")

    def __init__(self, pattern: Pattern[str], keep_matching: bool) -> None:
        self._pattern = pattern
        self._keep_matching = keep_matching

    def _keeps(self, char: str) -> bool:
        return bool(self._pattern.match(char)) is self._keep_matching

    def apply(self, old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        text = new.text
        kept: list[str] = []
        # Number of surviving characters strictly before each source index,
        # which is where an index in the old text lands in the new one.
        mapping: list[int] = []
        for char in text:
            mapping.append(len(kept))
            if self._keeps(char):
                kept.append(char)
        mapping.append(len(kept))

        if len(kept) == len(text):
            return new

        start = mapping[_clamp(new.selection.start, len(text))]
        end = mapping[_clamp(new.selection.end, len(text))]
        return new.copy_with(text="".join(kept), selection=TextRange(start, end))


class _MaxLengthFilter(InputFilter):
    """Truncates from the end once the text exceeds ``max_chars``."""

    __slots__ = ("_max_chars",)

    def __init__(self, max_chars: int) -> None:
        if max_chars < 0:
            raise ValueError(f"max_length must not be negative, got {max_chars}")
        self._max_chars = max_chars

    def apply(self, old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        if len(new.text) <= self._max_chars:
            return new
        text = new.text[: self._max_chars]
        return new.copy_with(
            text=text,
            selection=TextRange(_clamp(new.selection.start, len(text)), _clamp(new.selection.end, len(text))),
        )


class _MatchingFilter(InputFilter):
    """Rejects the whole edit unless the resulting text matches the pattern."""

    __slots__ = ("_pattern",)

    def __init__(self, pattern: Pattern[str]) -> None:
        self._pattern = pattern

    def apply(self, old: TextEditingValue, new: TextEditingValue) -> TextEditingValue:
        if self._pattern.fullmatch(new.text):
            return new
        return old


def _compile(pattern: Union[str, Pattern[str]]) -> Pattern[str]:
    return pattern if isinstance(pattern, re.Pattern) else re.compile(pattern)


def allow(pattern: Union[str, Pattern[str]]) -> InputFilter:
    """Keep only the characters that match ``pattern``, dropping the rest.

    The pattern is matched against one character at a time, so
    ``allow(r"[A-Za-z ]")`` yields a field that letters and spaces can be typed
    into and nothing else. Use :func:`matching` for a rule about the text as a
    whole.
    """
    return _CharacterFilter(_compile(pattern), keep_matching=True)


def deny(pattern: Union[str, Pattern[str]]) -> InputFilter:
    """Drop the characters that match ``pattern``, keeping the rest.

    The inverse of :func:`allow`, and the better fit when only a few characters
    are unwanted: ``deny(r"[\\s]")`` for a field that must not contain spaces.
    """
    return _CharacterFilter(_compile(pattern), keep_matching=False)


def digits_only() -> InputFilter:
    """Keep only ASCII digits. Equivalent to ``allow(r"[0-9]")``."""
    return allow(r"[0-9]")


def max_length(max_chars: int) -> InputFilter:
    """Limit the text to ``max_chars`` characters, truncating from the end."""
    return _MaxLengthFilter(max_chars)


def matching(pattern: Union[str, Pattern[str]]) -> InputFilter:
    """Reject an edit unless the resulting text matches ``pattern`` in full.

    Unlike :func:`allow`, which filters character by character and always
    accepts something, this rejects the keystroke outright when the result
    would not match -- the rule it enforces is about the text as a whole, so
    there is no partial result to keep. It is what expresses "at most one
    decimal point"::

        input_filter=matching(r"[0-9]*\\.?[0-9]*")

    The pattern must accept every string the user has to be able to pass
    through on the way to a finished value, including ``""`` if the field is to
    be clearable.
    """
    return _MatchingFilter(_compile(pattern))
