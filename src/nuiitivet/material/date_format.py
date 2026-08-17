"""Date text formats.

One pattern does three jobs: it parses what the user types, renders a date back
as text, and reads as the hint shown under the field. Deriving all three from a
single string is what keeps them from disagreeing -- a parse and a format
supplied separately are required to be inverses, and nothing can check that.

The notation is the one an application would want to show a user::

    DateFormat("mm/dd/yyyy")
    DateFormat("dd.mm.yyyy")
    DateFormat("yyyy-mm-dd")
    DateFormat("yyyy年mm月dd日")

Four tokens are recognised -- ``yyyy``, ``yy``, ``mm``, ``dd`` -- and everything
else is a literal. An **ASCII letter** outside a token is refused instead, since
that is how a mistyped token (``MMM``, ``YYYY``) would look; letters in other
scripts cannot be confused with one and pass through.

Tokens are lowercase only: case is left free for a future time format, where
``mm`` for minutes against ``MM`` for months is the usual convention, and
quietly accepting both spellings now would foreclose it.
"""

from __future__ import annotations

from datetime import date as _Date, datetime as _DateTime
from typing import Dict, Optional, Sequence, Tuple

# Longest first, so ``yyyy`` is matched before ``yy``.
_TOKENS: Tuple[Tuple[str, str, str], ...] = (
    ("yyyy", "%Y", "year"),
    ("yy", "%y", "year"),
    ("mm", "%m", "month"),
    ("dd", "%d", "day"),
)

_FIELDS = ("year", "month", "day")


def _compile(pattern: str) -> str:
    """Translate a friendly pattern into a :func:`time.strptime` format.

    Args:
        pattern: A pattern such as ``"mm/dd/yyyy"``.

    Returns:
        The equivalent ``strptime`` / ``strftime`` format string.

    Raises:
        ValueError: If the pattern contains an ASCII letter outside a token,
            repeats a field, or does not name all three of year, month and day.
    """
    directives: list[str] = []
    seen: Dict[str, str] = {}
    i = 0
    while i < len(pattern):
        for token, directive, field in _TOKENS:
            if pattern.startswith(token, i):
                if field in seen:
                    raise ValueError(
                        f"date format {pattern!r} names the {field} twice "
                        f"({seen[field]!r} and {token!r})"
                    )
                seen[field] = token
                directives.append(directive)
                i += len(token)
                break
        else:
            char = pattern[i]
            # Only ASCII letters can be mistaken for a token, so only they are
            # worth refusing. Anything else -- punctuation, or the 年 / 月 / 日
            # of a Japanese pattern -- is unambiguously a literal.
            if char.isascii() and char.isalpha():
                raise ValueError(
                    f"date format {pattern!r} contains {char!r}, which is not part of a "
                    f"token; the tokens are 'yyyy', 'yy', 'mm' and 'dd', and they are "
                    f"lowercase"
                )
            directives.append("%%" if char == "%" else char)
            i += 1

    missing = [field for field in _FIELDS if field not in seen]
    if missing:
        raise ValueError(f"date format {pattern!r} does not name the {', '.join(missing)}")

    return "".join(directives)


class DateFormat:
    """How a date is written as text, and read back.

    Args:
        pattern: The format dates are rendered in, and the first one accepted
            when parsing. Also what :meth:`__str__` returns, so it can be shown
            to the user as a hint.
        also_accepts: Further patterns accepted when parsing, tried in order
            after *pattern*. Typing is worth being lenient about -- someone will
            enter ``2026-06-10`` into a ``mm/dd/yyyy`` field -- while output
            stays in one format.

    Raises:
        ValueError: If any pattern is malformed.  See :func:`_compile`.
    """

    __slots__ = ("_pattern", "_also_accepts", "_formats")

    def __init__(self, pattern: str = "mm/dd/yyyy", *, also_accepts: Sequence[str] = ()) -> None:
        """Initialize DateFormat."""
        self._pattern = pattern
        self._also_accepts: Tuple[str, ...] = tuple(also_accepts)
        self._formats: Tuple[str, ...] = tuple(_compile(p) for p in (pattern, *self._also_accepts))

    @property
    def pattern(self) -> str:
        """The output pattern, and the first one tried when parsing."""
        return self._pattern

    @property
    def also_accepts(self) -> Tuple[str, ...]:
        """Further patterns accepted when parsing."""
        return self._also_accepts

    def parse(self, text: str) -> Optional[_Date]:
        """Read ``text`` as a date.

        A bound method, so it can be handed straight to an operator::

            self.arrival = self.arrival_text.map(fmt.parse)

        Args:
            text: Raw user input.  Surrounding whitespace is ignored.

        Returns:
            The date, or ``None`` when ``text`` matches no accepted pattern --
            which includes empty and half-typed text.
        """
        stripped = text.strip()
        for fmt in self._formats:
            try:
                return _DateTime.strptime(stripped, fmt).date()
            except ValueError:
                continue
        return None

    def format(self, value: Optional[_Date]) -> str:
        """Render ``value`` in :attr:`pattern`, or ``""`` when unset.

        Args:
            value: The date to render, or ``None``.

        Returns:
            Text that :meth:`parse` reads back as ``value``.
        """
        if value is None:
            return ""
        return value.strftime(self._formats[0])

    def matches(self, text: str) -> bool:
        """Whether :meth:`parse` can read ``text``.

        The predicate form, for the ``filter()`` step of a derived date::

            self.arrival = self.arrival_text.filter(fmt.matches, initial="").map(fmt.parse)

        Args:
            text: Raw user input.

        Returns:
            ``True`` when ``text`` parses, ``False`` otherwise.
        """
        return self.parse(text) is not None

    def __str__(self) -> str:
        """Return the pattern, so the format can be shown to the user as a hint."""
        return self._pattern

    def __repr__(self) -> str:
        """Return a reconstructable representation."""
        if self._also_accepts:
            return f"DateFormat({self._pattern!r}, also_accepts={self._also_accepts!r})"
        return f"DateFormat({self._pattern!r})"

    def __eq__(self, other: object) -> bool:
        """Two formats are equal when they accept and emit the same patterns."""
        if not isinstance(other, DateFormat):
            return NotImplemented
        return self._pattern == other._pattern and self._also_accepts == other._also_accepts

    def __hash__(self) -> int:
        """Hash consistent with :meth:`__eq__`."""
        return hash((self._pattern, self._also_accepts))


#: The format used unless a widget is given another one.  Emits ``mm/dd/yyyy``
#: and additionally accepts ``mm-dd-yyyy`` and ``yyyy-mm-dd`` when parsing.
DEFAULT_DATE_FORMAT = DateFormat("mm/dd/yyyy", also_accepts=("mm-dd-yyyy", "yyyy-mm-dd"))


def parse_date(text: str) -> Optional[_Date]:
    """Read ``text`` as a date using :data:`DEFAULT_DATE_FORMAT`.

    Args:
        text: Raw user input.

    Returns:
        The date, or ``None`` when the text matches no accepted pattern.
    """
    return DEFAULT_DATE_FORMAT.parse(text)


def format_date(value: Optional[_Date]) -> str:
    """Render ``value`` as ``mm/dd/yyyy``, or ``""`` when unset.

    Args:
        value: The date to render, or ``None``.

    Returns:
        Text that :func:`parse_date` reads back as ``value``.
    """
    return DEFAULT_DATE_FORMAT.format(value)


def is_date(text: str) -> bool:
    """Whether :func:`parse_date` can read ``text`` as a date.

    Written for the ``filter()`` step of a derived date, where the application
    wants the last valid date held while the user types an incomplete one::

        self.date_text = nv.Observable("")
        self.date = self.date_text.filter(nv.is_date, initial="").map(nv.parse_date)

    The seed is filtered text, not a date, so it goes through ``map`` as well:
    ``initial=""`` reads back as ``None`` until the first valid date arrives.

    Args:
        text: Raw user input.

    Returns:
        ``True`` when ``text`` parses, ``False`` otherwise.
    """
    return DEFAULT_DATE_FORMAT.matches(text)
