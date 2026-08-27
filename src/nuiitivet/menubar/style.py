"""Menu bar style definitions.

Lives in the framework-common ``menubar`` package (not under ``material``):
the menu bar is a generic widget, and this style carries no design-system
dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Optional

from nuiitivet.theme.types import ColorSpec

from .theme_data import MenuBarThemeData


@dataclass(frozen=True)
class MenuBarStyle:
    """Immutable visual style for the in-app menu bar.

    Holds geometry plus optional per-instance color overrides, mirroring
    :class:`~nuiitivet.scrolling.ScrollbarStyle`: the app-wide default palette
    is supplied by the design system via
    :class:`~nuiitivet.menubar.MenuBarThemeData`, and the nullable ``ColorSpec``
    fields here override it per instance. A ``None`` color falls back to the
    theme. Attach it to the model root: ``MenuBar(items, style=...)``.

    On macOS (once the NSMenu bridge exists) none of this applies — the global
    menu bar is rendered by the OS.

    Attributes:
        bar_height: Height of the horizontal bar in pixels.
        bar_horizontal_padding: Padding at the left/right ends of the bar.
        item_horizontal_padding: Horizontal padding inside each top-level item.
        item_gap: Gap between top-level items.
        item_corner_radius: Corner radius of the top-level item highlight.
        label_size: Font size of top-level item labels.
        popup_corner_radius: Corner radius of popup surfaces.
        popup_min_width: Minimum popup width in pixels.
        bar_background: Per-instance override (``None`` → theme). The remaining
            color fields override the same-named
            :class:`~nuiitivet.menubar.MenuBarThemeData` slots.
    """

    bar_height: int = 34
    bar_horizontal_padding: int = 4
    item_horizontal_padding: int = 10
    item_gap: int = 2
    item_corner_radius: int = 6
    label_size: int = 13
    popup_corner_radius: int = 8
    popup_min_width: int = 180

    bar_background: Optional[ColorSpec] = None
    bar_foreground: Optional[ColorSpec] = None
    bar_disabled_foreground: Optional[ColorSpec] = None
    bar_open_background: Optional[ColorSpec] = None
    bar_state_layer: Optional[ColorSpec] = None
    popup_background: Optional[ColorSpec] = None
    popup_foreground: Optional[ColorSpec] = None
    popup_accelerator: Optional[ColorSpec] = None
    popup_disabled_foreground: Optional[ColorSpec] = None
    popup_state_layer: Optional[ColorSpec] = None
    popup_divider: Optional[ColorSpec] = None

    def copy_with(self, **changes) -> "MenuBarStyle":
        """Return a copy of this style with the given fields overridden."""
        return replace(self, **changes)

    def merged_palette(self, theme_data: Optional[MenuBarThemeData]) -> MenuBarThemeData:
        """The effective palette: theme data with this style's overrides applied.

        Args:
            theme_data: App-wide palette from the active theme, or ``None``
                when no design system registered one (the neutral defaults are
                used then).

        Returns:
            A :class:`MenuBarThemeData` where every slot named by a non-``None``
            color field on this style is replaced by that override.
        """
        base = theme_data or MenuBarThemeData()
        overrides = {}
        for field in fields(MenuBarThemeData):
            value = getattr(self, field.name, None)
            if value is not None:
                overrides[field.name] = value
        return base.copy_with(**overrides) if overrides else base
