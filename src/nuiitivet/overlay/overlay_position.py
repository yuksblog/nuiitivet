"""Overlay positioning helpers."""

from __future__ import annotations

from typing import Tuple

from nuiitivet.layout.alignment import NINE_POINT_ALIGNMENTS


class OverlayPosition:
    """Represents how an overlay entry is positioned within the overlay root."""

    def __init__(self, alignment: str, *, offset: Tuple[float, float] = (0.0, 0.0)) -> None:
        key = str(alignment).strip().lower().replace("_", "-")
        if key not in NINE_POINT_ALIGNMENTS:
            allowed = ", ".join(sorted(NINE_POINT_ALIGNMENTS))
            raise ValueError(f"Invalid alignment: {alignment!r}. Allowed: {allowed}")
        dx, dy = offset
        self.alignment_key = key
        self.offset = (float(dx), float(dy))

    @classmethod
    def alignment(
        cls,
        alignment: str,
        *,
        offset: Tuple[float, float] = (0.0, 0.0),
    ) -> "OverlayPosition":
        return cls(alignment, offset=offset)
