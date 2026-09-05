"""Style configuration for the MD3 search widgets.

Both styles carry the *contained* (expressive) token values only. The
baseline/Divided variant is not implemented, so no field here has an elevation
or a divider colour — see :mod:`nuiitivet.material.search` for why.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from nuiitivet.animation.motion import Motion
from nuiitivet.material.motion import EXPRESSIVE_FAST_SPATIAL
from nuiitivet.theme.types import ColorSpec

from ..theme.color_role import ColorRole

if TYPE_CHECKING:
    from ...theme import Theme

# Focus margin animation (md.comp.search-bar.contained.motion.spring: fast spatial).
SEARCH_BAR_FOCUS_MARGIN: Motion = EXPRESSIVE_FAST_SPATIAL


@dataclass(frozen=True)
class SearchBarStyle:
    """Style configuration for :class:`~nuiitivet.material.search.SearchBar`.

    MD3 reference: ``md.comp.search-bar.*``, contained rows only.
    """

    # Container. The bar is fully rounded, so the radius is derived from the
    # height at paint time rather than stored; there is no elevation, because
    # the contained variant separates by surface role instead of by shadow.
    container_color: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGH
    container_height: float = 56.0

    # Outer margin, animated between the two endpoints on focus.
    # md.comp.search-bar.contained.leading-margin (24dp) ->
    # md.comp.search-view.contained.leading-margin (12dp).
    margin: float = 24.0
    focused_margin: float = 12.0

    # Width clamps. ``min_width`` yields to a narrower box rather than
    # overflowing it; ``max_width`` caps the bar and centres it.
    min_width: float = 360.0
    max_width: float = 720.0

    # Text
    input_text_color: ColorSpec = ColorRole.ON_SURFACE
    supporting_text_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    font_size: int = 16  # body-large

    # Icons
    leading_icon_color: ColorSpec = ColorRole.ON_SURFACE
    trailing_icon_color: ColorSpec = ColorRole.ON_SURFACE_VARIANT
    icon_size: int = 24

    # Cursor & selection
    cursor_color: ColorSpec = ColorRole.PRIMARY
    selection_color: ColorSpec = ColorRole.PRIMARY_CONTAINER

    # State layer / focus indicator
    state_layer_color: ColorSpec = ColorRole.ON_SURFACE
    focus_indicator_color: ColorSpec = ColorRole.SECONDARY

    # Inner spacing. v1 always carries a trailing action, so the 16dp
    # ``contained.no-actions.*`` rows never apply.
    leading_space: float = 4.0
    trailing_space: float = 4.0
    icon_label_gap: float = 4.0

    def copy_with(self, **changes) -> "SearchBarStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)

    @classmethod
    def from_theme(cls, theme: "Theme") -> "SearchBarStyle":
        """Resolve the default :class:`SearchBarStyle` for the given theme.

        The defaults are already theme roles rather than literal colours, so
        this returns the preset unless a Material theme extension overrides it.
        """
        from nuiitivet.material.theme.theme_data import MaterialThemeData

        theme_data = theme.extension(MaterialThemeData)
        if theme_data:
            return theme_data.search_bar_style
        return cls()


@dataclass(frozen=True)
class DockedSearchBarStyle:
    """Style configuration for :class:`~nuiitivet.material.search.DockedSearchBar`.

    MD3 reference: ``md.comp.search-view.contained.docked.*``.
    """

    bar: SearchBarStyle = field(default_factory=SearchBarStyle)

    # Suggestions container.
    container_color: ColorSpec = ColorRole.SURFACE_CONTAINER_HIGH
    corner_radius: float = 12.0  # md.sys.shape.corner.medium

    # md.comp.search-view.contained.docked.bar-results.gap
    gap: float = 2.0

    # Height range. ``max_height_ratio`` is measured against the window;
    # ``min_height`` is a floor that wins over it, so a window with less room
    # than the minimum is overflowed rather than shrunk into.
    min_height: float = 240.0
    max_height_ratio: float = 2.0 / 3.0

    def copy_with(self, **changes) -> "DockedSearchBarStyle":
        """Create a new style instance with specified fields changed."""
        return replace(self, **changes)
