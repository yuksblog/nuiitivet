"""Renderer-level shadow parameters.

This module belongs to the rendering layer and has no knowledge of any
design system (e.g. Material Design 3). It only describes *how* a shadow
should be drawn using Skia-level primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple, Union

from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class ShadowParams:
    """Concrete parameters for a single shadow draw pass.

    A shadow is drawn as one or more of these layers, stacked back to front.

    Args:
        sigma: Gaussian blur radius (Skia ImageFilters.Blur sigma).
            A value of 0.0 means no blur.
        offset: (dx, dy) translation of the shadow relative to the widget.
        color: Shadow color. Supports ``ColorRole``, hex string, RGBA tuple,
            or a ``(ColorRole, alpha)`` pair where *alpha* is 0.0-1.0.
        spread: Outward inflation of the shadow rect, in pixels, applied
            before the blur. Corner radii grow by the same amount. A negative
            value shrinks the rect. This is the CSS ``box-shadow`` spread.
    """

    sigma: float
    offset: Tuple[float, float]
    color: ColorSpec
    spread: float = 0.0

    @property
    def is_visible(self) -> bool:
        """Return True when the shadow will produce any visible output."""
        return self.sigma > 0.0 or self.spread != 0.0 or self.offset != (0.0, 0.0)

    @classmethod
    def from_css(
        cls,
        offset_x: float,
        offset_y: float,
        blur: float,
        spread: float,
        color: ColorSpec,
    ) -> "ShadowParams":
        """Build a layer from CSS ``box-shadow`` values.

        CSS states a blur *radius*, which is twice the Gaussian sigma a
        renderer applies, so *blur* is halved here.

        Args:
            offset_x: CSS offset-x, in pixels.
            offset_y: CSS offset-y, in pixels.
            blur: CSS blur-radius, in pixels.
            spread: CSS spread-radius, in pixels.
            color: Shadow color.

        Returns:
            The equivalent ``ShadowParams``.
        """
        return cls(
            sigma=float(blur) / 2.0,
            offset=(float(offset_x), float(offset_y)),
            color=color,
            spread=float(spread),
        )


#: One or more shadow layers, stacked back to front.
ShadowLayers = Tuple[ShadowParams, ...]

#: What a caller may pass where shadow layers are expected.
ShadowLayersLike = Union[None, ShadowParams, Sequence[ShadowParams]]

#: A no-op sentinel that produces no shadow.
NO_SHADOW: ShadowLayers = ()


def normalize_shadows(value: ShadowLayersLike) -> ShadowLayers:
    """Coerce a shadow specification into a tuple of visible layers.

    Accepts ``None``, a single ``ShadowParams``, or any sequence of them.
    Layers that would draw nothing are dropped, so an all-invisible input
    normalizes to :data:`NO_SHADOW`.

    Args:
        value: The shadow specification to normalize.

    Returns:
        A tuple of visible ``ShadowParams``, possibly empty.

    Raises:
        TypeError: If *value* is neither ``None``, a ``ShadowParams``, nor a
            sequence of ``ShadowParams``.
    """
    if value is None:
        return NO_SHADOW
    if isinstance(value, ShadowParams):
        layers: Iterable[ShadowParams] = (value,)
    elif isinstance(value, (list, tuple)):
        for item in value:
            if not isinstance(item, ShadowParams):
                raise TypeError(f"shadow layers must be ShadowParams, got {type(item).__name__}")
        layers = value
    else:
        raise TypeError(f"cannot interpret {type(value).__name__} as shadow layers")
    return tuple(layer for layer in layers if layer.is_visible)


def shadow_outsets(layers: ShadowLayers, *, min_blur_pad: float = 4.0) -> Tuple[float, float, float, float]:
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
        if layer.sigma > 0.0:
            pad = max(float(min_blur_pad), layer.sigma * 3.0)
        pad += float(layer.spread)
        dx, dy = layer.offset
        left = max(left, pad - float(dx))
        right = max(right, pad + float(dx))
        top = max(top, pad - float(dy))
        bottom = max(bottom, pad + float(dy))
    return (max(0.0, left), max(0.0, top), max(0.0, right), max(0.0, bottom))


def resolve_shadow_layers(owner: object) -> ShadowLayers:
    """Read normalized shadow layers off a widget, tolerating absence.

    Args:
        owner: The widget to read ``shadows`` from.

    Returns:
        The widget's layers, or :data:`NO_SHADOW` when it declares none.
    """
    value: Optional[ShadowLayersLike] = getattr(owner, "shadows", None)
    if value is None:
        return NO_SHADOW
    if isinstance(value, tuple) and all(isinstance(item, ShadowParams) for item in value):
        return value
    return normalize_shadows(value)
