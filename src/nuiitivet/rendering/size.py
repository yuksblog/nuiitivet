"""The :class:`Size` value type: a widget's *measured* box.

Sits next to :mod:`nuiitivet.rendering.sizing`, its counterpart: a ``Sizing`` is
the space a widget *requests* along an axis, a ``Size`` is the space it actually
*got* after layout. Both the ``on_size_changed`` modifier and ``Geometry`` report
their measurement as a ``Size``.
"""

from __future__ import annotations

from typing import NamedTuple


class Size(NamedTuple):
    """An immutable ``(width, height)`` pair in logical pixels.

    A ``NamedTuple`` so it is compared by value: two equal sizes are ``==``,
    which lets a size report de-dupe an unchanged measurement without a custom
    comparator. It also unpacks like a tuple (``w, h = size``).
    """

    width: int
    height: int


__all__ = ["Size"]
