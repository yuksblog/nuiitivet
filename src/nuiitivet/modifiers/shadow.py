from dataclasses import dataclass
from typing import Optional, Tuple
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..theme.types import ColorSpec
from ..rendering.shadow import ShadowLayers, ShadowLayersLike, ShadowParams, normalize_shadows
from ..widgets.box import Box, ModifierBox


@dataclass
class ShadowModifier(ModifierElement):
    """Applies one or more shadow layers to a widget."""

    layers: ShadowLayers

    def apply(self, widget: Widget) -> Widget:
        if isinstance(widget, Box):
            widget.shadows = self.layers
            return widget

        if isinstance(widget, ModifierBox):
            box = ModifierBox(
                child=widget.children[0] if widget.children else None,
                width=widget.width_sizing,
                height=widget.height_sizing,
                padding=widget.padding,
                modifier=widget._modifier_chain,
                background_color=widget.bgcolor,
                border_width=widget.border_width,
                border_color=widget.border_color,
                corner_radius=widget.corner_radius,
                shadows=self.layers,
                alignment=widget.alignment,
            )
            box.clip_content = widget.clip_content
            return box

        return ModifierBox(
            child=widget,
            shadows=self.layers,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )


def shadow(
    color: Optional[ColorSpec],
    blur: float = 0.0,
    offset: Tuple[float, float] = (0.0, 0.0),
    spread: float = 0.0,
) -> ShadowModifier:
    """Draw a single shadow layer behind the widget.

    Args:
        color: Shadow color. ``None`` draws no shadow.
        blur: Gaussian blur sigma. 0 gives a hard-edged shadow.
        offset: (dx, dy) translation of the shadow.
        spread: Outward inflation of the shadow rect, in pixels.

    Returns:
        The modifier to apply.
    """
    if color is None:
        return ShadowModifier(layers=())
    return ShadowModifier(layers=normalize_shadows(ShadowParams(sigma=blur, offset=offset, color=color, spread=spread)))


def shadows(layers: ShadowLayersLike) -> ShadowModifier:
    """Draw a stack of shadow layers behind the widget.

    Use this where one layer cannot express the shadow -- Material Design's
    elevation, for instance, is a key layer over a wider ambient one.

    Args:
        layers: A ``ShadowParams``, a sequence of them ordered back to front,
            or ``None`` for no shadow.

    Returns:
        The modifier to apply.
    """
    return ShadowModifier(layers=normalize_shadows(layers))
