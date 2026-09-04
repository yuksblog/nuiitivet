from dataclasses import dataclass
from ..widgeting.modifier import ModifierElement
from ..widgeting.widget import Widget
from ..rendering.shadow import ShadowLike, Shadows, normalize_shadows
from ..widgets.box import Box, ModifierBox


@dataclass
class ShadowModifier(ModifierElement):
    """Applies one or more shadow layers to a widget."""

    layers: Shadows

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


def shadows(layers: ShadowLike) -> ShadowModifier:
    """Draw a stack of shadow layers behind the widget.

    Args:
        layers: A ``Shadow``, a sequence of them ordered back to front, or
            ``None`` for no shadow. Material Design's elevation, for
            instance, is a key layer over a wider ambient one.

    Returns:
        The modifier to apply.
    """
    return ShadowModifier(layers=normalize_shadows(layers))
