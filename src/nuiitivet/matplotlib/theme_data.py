"""The colors a matplotlib figure takes from the theme: a palette extension each design system registers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class MatplotlibFigureThemeData:
    """Which theme color each part of a figure takes.

    Every field is a :data:`ColorSpec`, resolved against the theme on each
    draw, so the figure follows a theme switch. ``series`` is the list
    matplotlib's default color cycle maps onto, in turn; empty keeps
    matplotlib's own cycle. A design system registers one instance in its
    theme; the defaults are neutral literals for a theme without one.
    """

    #: Titles, axis labels, figure text and legend text.
    text: ColorSpec = "#000000"
    #: Tick marks and tick labels.
    ticks: ColorSpec = ("#000000", 0.7)
    #: Spines, grid lines and the legend frame's edge.
    outline: ColorSpec = ("#000000", 0.6)
    #: The colors a series takes in turn; empty keeps matplotlib's cycle.
    series: tuple[ColorSpec, ...] = ()
    #: The legend frame's fill; ``None`` keeps matplotlib's.
    legend: ColorSpec = None
    #: The zoom rectangle a controller drags; ``None`` takes ``text``.
    rubberband: ColorSpec = None

    def copy_with(self, **changes: Any) -> "MatplotlibFigureThemeData":
        """A copy with *changes* applied."""
        return replace(self, **changes)


__all__ = ["MatplotlibFigureThemeData"]
