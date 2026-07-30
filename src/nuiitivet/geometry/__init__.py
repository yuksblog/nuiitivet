"""Container-scoped measured geometry.

:class:`Geometry` measures its own box and publishes the result as an
``Observable[Size]``, read reactively via ``Geometry.of(context)``.
"""

from __future__ import annotations

from nuiitivet.rendering.size import Size

from .geometry import Geometry

__all__ = ["Geometry", "Size"]
