"""Renderer-level shadow parameters.

This module belongs to the rendering layer and has no knowledge of any
design system (e.g. Material Design 3). It only describes *how* a shadow
should be drawn using Skia-level primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class ShadowParams:
    """Concrete parameters for a single shadow draw pass.

    Args:
        sigma: Gaussian blur radius (Skia ImageFilters.Blur sigma).
            A value of 0.0 means no blur (no shadow drawn).
        offset: (dx, dy) translation of the shadow relative to the widget.
        color: Shadow color. Supports ``ColorRole``, hex string, RGBA tuple,
            or a ``(ColorRole, alpha)`` pair where *alpha* is 0.0–1.0.
    """

    sigma: float
    offset: Tuple[float, float]
    color: ColorSpec

    @property
    def is_visible(self) -> bool:
        """Return True when the shadow will produce any visible output."""
        return self.sigma > 0.0 or self.offset != (0.0, 0.0)


#: A no-op sentinel that produces no shadow.
NO_SHADOW: ShadowParams = ShadowParams(sigma=0.0, offset=(0.0, 0.0), color=(0, 0, 0, 0))
