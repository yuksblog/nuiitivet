"""Menu bar color theme data.

Lives in the framework-common ``menubar`` package (not under ``material``):
the menu bar is a generic widget, so its palette is supplied through the
generic theme seam (:class:`~nuiitivet.theme.types.ThemeExtension`) rather
than by reading Material color roles directly — the same arrangement as
:class:`~nuiitivet.scrolling.ScrollbarThemeData`.

Each design system registers a :class:`MenuBarThemeData` into its
:class:`~nuiitivet.theme.theme.Theme` (see ``material.theme`` and
``theme.plain_theme``) with colors expressed as
:data:`~nuiitivet.theme.types.ColorSpec` **tokens**. Because the colors are
tokens — not baked RGBA — they are resolved at paint time against the
*current* theme, so light/dark switching works automatically.

The palette covers **both** surfaces the menu system draws: the horizontal
bar and its popups. The popups reuse the Material ``Menu`` widget machinery,
but their colors come from here, not from the Material menu defaults — a
non-Material design system must not get Material-colored popups under a
framework-common bar (see ``docs/design/MENU_BAR.md``, Section 8.4).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class MenuBarThemeData:
    """App-wide themeable colors for the menu bar, resolved at paint time.

    The defaults are neutral, design-system-agnostic literals so that a bare
    ``MenuBarThemeData()`` is usable even when no design system is registered.

    Attributes:
        bar_background: Background of the horizontal bar.
        bar_foreground: Label color of top-level bar items.
        bar_disabled_foreground: Label color of disabled top-level items.
        bar_open_background: Background of the top-level item whose menu is open.
        bar_state_layer: Hover/press state-layer color for bar items.
        popup_background: Popup container background.
        popup_foreground: Popup item label color.
        popup_accelerator: Accelerator text color in popup items.
        popup_disabled_foreground: Base color for disabled popup items.
        popup_state_layer: Hover/press/focus state-layer color for popup items.
        popup_divider: Separator line color inside popups.
    """

    bar_background: ColorSpec = ("#000000", 0.04)
    bar_foreground: ColorSpec = ("#000000", 0.87)
    bar_disabled_foreground: ColorSpec = ("#000000", 0.38)
    bar_open_background: ColorSpec = ("#000000", 0.12)
    bar_state_layer: ColorSpec = "#000000"
    popup_background: ColorSpec = "#FFFFFF"
    popup_foreground: ColorSpec = ("#000000", 0.87)
    popup_accelerator: ColorSpec = ("#000000", 0.60)
    popup_disabled_foreground: ColorSpec = "#000000"
    popup_state_layer: ColorSpec = "#000000"
    popup_divider: ColorSpec = ("#000000", 0.12)

    def copy_with(self, **changes: Any) -> "MenuBarThemeData":
        """Return a copy of this theme data with the given fields overridden."""
        return replace(self, **changes)
