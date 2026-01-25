from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple

from nuiitivet.common.logging_once import exception_once


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Elevation:
    level: float
    offset: Tuple[int, int]
    blur: float
    alpha: float

    @classmethod
    def from_level(cls, level: float) -> "Elevation":
        """Map a numeric elevation to shadow parameters.

        The mapping is a discrete level table derived from M3 tokens (approx.)
        and returns offset (dx,dy), blur radius and alpha for the shadow.
        """
        try:
            lv = float(level or 0.0)
        except Exception:
            exception_once(logger, "elevation_level_float_exc", "Failed to coerce elevation level to float")
            lv = 0.0

        # Continuous mapping using linear interpolation between buckets.
        # Define breakpoints inspired by M3 tokens (level, dy, blur, alpha).
        buckets = [
            (0.0, 0.0, 0.0, 0.0),
            (1.0, 1.0, 3.0, 0.06),
            (3.0, 2.0, 6.0, 0.08),
            (6.0, 6.0, 12.0, 0.12),
            (8.0, 8.0, 18.0, 0.16),
            (12.0, 12.0, 26.0, 0.22),
        ]

        # Clamp below/above
        if lv <= buckets[0][0]:
            return cls(level=lv, offset=(0, 0), blur=0.0, alpha=0.0)
        if lv >= buckets[-1][0]:
            dy, blur, alpha = buckets[-1][1], buckets[-1][2], buckets[-1][3]
            return cls(level=lv, offset=(0, int(round(dy))), blur=blur, alpha=alpha)

        # find surrounding buckets
        lower = buckets[0]
        upper = buckets[-1]
        for i in range(len(buckets) - 1):
            a = buckets[i]
            b = buckets[i + 1]
            if a[0] <= lv <= b[0]:
                lower = a
                upper = b
                break

        # interpolation factor
        t = 0.0
        if upper[0] != lower[0]:
            t = (lv - lower[0]) / (upper[0] - lower[0])

        def lerp(x, y, f):
            return x + (y - x) * f

        dy = lerp(lower[1], upper[1], t)
        blur = lerp(lower[2], upper[2], t)
        alpha = lerp(lower[3], upper[3], t)

        return cls(level=lv, offset=(0, int(round(dy))), blur=float(blur), alpha=float(alpha))


def compute_shadow_params(elevation: float):
    e = Elevation.from_level(elevation)
    return e.offset, e.blur, e.alpha
