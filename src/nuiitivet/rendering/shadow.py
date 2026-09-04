"""Renderer-level shadow values.

This module belongs to the rendering layer and has no knowledge of any
design system (e.g. Material Design 3). It describes *what* to draw in the
CSS ``box-shadow`` vocabulary — blur-radius and spread-radius — and leaves
the translation to Skia primitives (blur-radius is twice the Gaussian
sigma) to the renderer that draws it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple, Union

from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class Shadow:
    """A single shadow layer, in CSS ``box-shadow`` terms.

    A widget's shadow is one or more of these layers, stacked back to front.

    Args:
        color: Shadow color. Supports ``ColorRole``, hex string, RGBA tuple,
            or a ``(ColorRole, alpha)`` pair where *alpha* is 0.0-1.0.
        blur_radius: CSS blur-radius, in pixels. A value of 0.0 means a
            hard-edged shadow.
        offset: (dx, dy) translation of the shadow relative to the widget.
        spread_radius: CSS spread-radius, in pixels: outward inflation of
            the shadow rect, applied before the blur. Corner radii grow by
            the same amount. A negative value shrinks the rect.
    """

    color: ColorSpec
    blur_radius: float = 0.0
    offset: Tuple[float, float] = (0.0, 0.0)
    spread_radius: float = 0.0

    @property
    def is_visible(self) -> bool:
        """Return True when the shadow will produce any visible output."""
        return self.blur_radius > 0.0 or self.spread_radius != 0.0 or self.offset != (0.0, 0.0)


#: One or more shadow layers, stacked back to front.
Shadows = Tuple[Shadow, ...]

#: What a caller may pass where shadows are expected.
ShadowLike = Union[None, Shadow, Sequence[Shadow]]

#: A no-op sentinel that produces no shadow.
NO_SHADOWS: Shadows = ()


def normalize_shadows(value: ShadowLike) -> Shadows:
    """Coerce a shadow specification into a tuple of visible layers.

    Accepts ``None``, a single ``Shadow``, or any sequence of them. Layers
    that would draw nothing are dropped, so an all-invisible input
    normalizes to :data:`NO_SHADOWS`.

    Args:
        value: The shadow specification to normalize.

    Returns:
        A tuple of visible ``Shadow`` layers, possibly empty.

    Raises:
        TypeError: If *value* is neither ``None``, a ``Shadow``, nor a
            sequence of ``Shadow``.
    """
    if value is None:
        return NO_SHADOWS
    if isinstance(value, Shadow):
        layers: Iterable[Shadow] = (value,)
    elif isinstance(value, (list, tuple)):
        for item in value:
            if not isinstance(item, Shadow):
                raise TypeError(f"shadow layers must be Shadow, got {type(item).__name__}")
        layers = value
    else:
        raise TypeError(f"cannot interpret {type(value).__name__} as shadow layers")
    return tuple(layer for layer in layers if layer.is_visible)


def shadow_outsets(layers: Shadows, *, min_blur_pad: float = 4.0) -> Tuple[float, float, float, float]:
    """Return how far *layers* paint outside the widget rect.

    The result is the per-side maximum across every layer, so a single
    bounding box covers them all.

    Args:
        layers: The shadow layers to measure.
        min_blur_pad: Floor applied to a blurred layer's padding, matching
            the padding the renderer reserves around its blur pass.

    Returns:
        ``(left, top, right, bottom)`` in pixels, each non-negative.
    """
    left = top = right = bottom = 0.0
    for layer in layers:
        if not layer.is_visible:
            continue
        pad = 0.0
        if layer.blur_radius > 0.0:
            pad = max(float(min_blur_pad), layer.blur_radius * 1.5)
        pad += float(layer.spread_radius)
        dx, dy = layer.offset
        left = max(left, pad - float(dx))
        right = max(right, pad + float(dx))
        top = max(top, pad - float(dy))
        bottom = max(bottom, pad + float(dy))
    return (max(0.0, left), max(0.0, top), max(0.0, right), max(0.0, bottom))
