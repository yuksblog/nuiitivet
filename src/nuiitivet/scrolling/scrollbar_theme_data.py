"""Scrollbar color theme data.

Lives in the framework-common ``scrolling`` package (not under ``material``):
the scrollbar is a generic widget, so its palette is supplied through the
generic theme seam (:class:`~nuiitivet.theme.types.ThemeExtension`) rather than
by reading Material color roles directly.

Each design system registers a :class:`ScrollbarThemeData` into its
:class:`~nuiitivet.theme.theme.Theme` (see ``material.theme`` and
``theme.plain_theme``) with colors expressed as
:data:`~nuiitivet.theme.types.ColorSpec` **tokens**. Because the colors are
tokens — not baked RGBA — they are resolved at paint time against the *current*
theme, so light/dark switching works automatically.

Role split (mirrors the Material ``ThemeData`` / ``Style`` division):

* **App-wide default palette** → :class:`ScrollbarThemeData` (this class),
  supplied by the design system via the theme.
* **Per-instance override** → nullable ``ColorSpec`` fields on
  :class:`~nuiitivet.scrolling.ScrollbarStyle`.
* **Shape** → :class:`~nuiitivet.scrolling.ScrollbarStyle` geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from nuiitivet.theme.types import ColorSpec


@dataclass(frozen=True)
class ScrollbarThemeData:
    """App-wide themeable colors for the scrollbar, resolved at paint time.

    Colors are :data:`~nuiitivet.theme.types.ColorSpec` values — literals or
    design-system tokens (optionally paired with an alpha multiplier). Storing
    tokens (rather than resolved RGBA) is what lets a single
    ``ScrollbarThemeData`` render correctly across light and dark modes: the
    token resolves against whichever :class:`~nuiitivet.theme.theme.Theme` is
    active when the scrollbar paints.

    The defaults are neutral, design-system-agnostic literals so that a bare
    ``ScrollbarThemeData()`` is usable even when no design system is registered.

    Attributes:
        track: Color of the scrollbar track.
        thumb: Color of the thumb when idle.
        thumb_hover: Color of the thumb while hovered.
        thumb_active: Color of the thumb while pressed / dragging.
    """

    track: ColorSpec = ("#000000", 0.12)
    thumb: ColorSpec = ("#000000", 0.70)
    thumb_hover: ColorSpec = ("#000000", 0.90)
    thumb_active: ColorSpec = ("#000000", 1.0)

    def copy_with(self, **changes: Any) -> "ScrollbarThemeData":
        """Return a copy of this theme data with the given fields overridden.

        Args:
            **changes: Fields to override.

        Returns:
            A new :class:`ScrollbarThemeData` with the specified changes applied.
        """
        return replace(self, **changes)
