"""The :class:`Size` value type published by :class:`Geometry`."""

from __future__ import annotations

from typing import NamedTuple


class Size(NamedTuple):
    """An immutable ``(width, height)`` pair in logical pixels.

    A ``NamedTuple`` so it is compared by value: two equal sizes are ``==``,
    which lets an ``Observable[Size]`` de-dupe an unchanged measurement without
    a custom comparator. It also unpacks like a tuple (``w, h = size``).
    """

    width: int
    height: int


__all__ = ["Size"]
