"""Scrollbar style definitions.

Lives in the framework-common ``scrolling`` package (not under ``material``):
the scrollbar is a generic widget, and this style carries no design-system
dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from nuiitivet.scrolling.scrollbar_theme_data import ScrollbarThemeData
from nuiitivet.theme.types import ColorSpec

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme

Rgba = Tuple[int, int, int, int]


@dataclass(frozen=True)
class ScrollbarStyle:
    """Immutable visual style for the scrollbar of a ``Scrollable``.

    Holds the bar's own appearance: geometry plus optional per-instance color
    overrides. Placement (viewport padding, offset from the edge, overlay vs.
    inline) lives in :class:`~nuiitivet.scrolling.ScrollableStyle`; dynamic
    visibility is controlled by the ``scrollbar_visible`` parameter of the
    scrollable widget, and interaction behavior (auto-hide, track clicks, etc.)
    lives in :class:`~nuiitivet.scrolling.ScrollbarBehavior`.

    Colors follow the framework-wide ``ThemeData`` / ``Style`` division: the
    app-wide default palette is supplied by the design system via
    :class:`~nuiitivet.scrolling.ScrollbarThemeData`, and the nullable
    ``ColorSpec`` fields here override it per instance. A ``None`` color falls
    back to the theme. Use :meth:`resolve_colors` to obtain concrete RGBA values.

    Attributes:
        thickness: Scrollbar thickness in pixels. Defaults to ``8``.
        min_thumb_length: Minimum thumb length in pixels. Defaults to ``24``.
        track: Per-instance override for the track color (``None`` → theme).
        thumb: Per-instance override for the idle thumb color (``None`` → theme).
        thumb_hover: Per-instance override for the hovered thumb color
            (``None`` → theme).
        thumb_active: Per-instance override for the pressed/dragging thumb color
            (``None`` → theme).
    """

    thickness: int = 8
    min_thumb_length: int = 24
    track: Optional[ColorSpec] = None
    thumb: Optional[ColorSpec] = None
    thumb_hover: Optional[ColorSpec] = None
    thumb_active: Optional[ColorSpec] = None

    def copy_with(self, **changes) -> "ScrollbarStyle":
        """Return a copy of this style with the given fields overridden.

        Args:
            **changes: Fields to override.

        Returns:
            A new :class:`ScrollbarStyle` with the specified changes applied.
        """
        return replace(self, **changes)

    def resolve_colors(
        self,
        theme_data: Optional[ScrollbarThemeData] = None,
        theme: "Theme | None" = None,
    ) -> Dict[str, Rgba]:
        """Resolve track/thumb colors to concrete RGBA values.

        Per-instance overrides on this style win over ``theme_data``; any slot
        left ``None`` falls back to ``theme_data`` (or, when no design system is
        registered, the neutral :class:`ScrollbarThemeData` defaults). Tokens are
        resolved against ``theme`` so a single palette renders correctly across
        light and dark modes.

        Args:
            theme_data: App-wide default palette from the active theme.
            theme: The active theme, used to resolve design-system tokens.

        Returns:
            A dict with ``track`` / ``thumb`` / ``thumb_hover`` / ``thumb_active``
            RGBA tuples (ints 0-255).
        """
        from nuiitivet.theme.resolver import resolve_color_to_rgba

        base = theme_data or ScrollbarThemeData()

        def _pick(override: Optional[ColorSpec], default: ColorSpec) -> ColorSpec:
            return override if override is not None else default

        return {
            "track": resolve_color_to_rgba(_pick(self.track, base.track), theme=theme),
            "thumb": resolve_color_to_rgba(_pick(self.thumb, base.thumb), theme=theme),
            "thumb_hover": resolve_color_to_rgba(_pick(self.thumb_hover, base.thumb_hover), theme=theme),
            "thumb_active": resolve_color_to_rgba(_pick(self.thumb_active, base.thumb_active), theme=theme),
        }
