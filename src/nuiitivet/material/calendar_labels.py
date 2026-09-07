"""Calendar display labels.

The names a calendar renders dates with -- month names, weekday column headers
-- and which weekday its grid starts on, gathered into one value the
application supplies::

    CalendarLabels(
        month_names=("1月", "2月", ..., "12月"),
        weekday_labels=("月", "火", "水", "木", "金", "土", "日"),
    )

The application supplies them rather than the process locale, because the
locale's data is the host C library's: the same locale name yields different
strings on different OSes, and ``LC_TIME`` is process-global mutable state no
widget can scope. The default is English with a Sunday-first week, so an
unconfigured calendar renders identically on every platform.

Weekday indexing follows :meth:`datetime.date.weekday`: Monday is 0, Sunday is
6, and the :mod:`calendar` constants (``calendar.MONDAY`` ... ``calendar.SUNDAY``)
name the values.
"""

from __future__ import annotations

import calendar as _calendar
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True, slots=True)
class CalendarLabels:
    """Names and week convention a calendar renders dates with.

    Args:
        month_names: Twelve month names, January first, indexed by
            ``month - 1``.
        weekday_labels: Seven weekday column headers, Monday first -- indexed
            by :meth:`datetime.date.weekday` regardless of
            *first_day_of_week*.
        first_day_of_week: The weekday the grid's first column shows, numbered
            as :meth:`datetime.date.weekday` does (``calendar.MONDAY`` is 0,
            ``calendar.SUNDAY`` is 6). Defaults to Sunday, matching the MD3
            spec; a calendar that starts on another day is a deliberate
            deviation from MD3, chosen by the application.

    Raises:
        ValueError: If *month_names* does not hold 12 entries,
            *weekday_labels* does not hold 7, or *first_day_of_week* is
            outside 0-6.
    """

    month_names: Tuple[str, ...] = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    weekday_labels: Tuple[str, ...] = ("M", "T", "W", "T", "F", "S", "S")
    first_day_of_week: int = _calendar.SUNDAY

    def __post_init__(self) -> None:
        """Validate the field shapes."""
        if len(self.month_names) != 12:
            raise ValueError(f"month_names holds {len(self.month_names)} entries, expected 12")
        if len(self.weekday_labels) != 7:
            raise ValueError(f"weekday_labels holds {len(self.weekday_labels)} entries, expected 7")
        if not 0 <= self.first_day_of_week <= 6:
            raise ValueError(
                f"first_day_of_week is {self.first_day_of_week}, expected 0 (Monday) to 6 (Sunday)"
            )

    def weekday_columns(self) -> Tuple[str, ...]:
        """The weekday headers in grid column order.

        Returns:
            The seven labels starting at :attr:`first_day_of_week`.
        """
        first = self.first_day_of_week
        return tuple(self.weekday_labels[(first + i) % 7] for i in range(7))


#: The labels used unless a widget is given others: English, Sunday-first.
DEFAULT_CALENDAR_LABELS = CalendarLabels()
