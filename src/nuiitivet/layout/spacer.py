"""Spacer widget moved to its own module.

This module defines the Spacer widget which is a tiny utility that
reserves space in layouts.
"""

from typing import Optional, Tuple

from ..rendering.sizing import SizingLike
from ..widgeting.widget import Widget


class Spacer(Widget):
    """Invisible widget that reserves space.

    This single Spacer supports both fixed-size and flexible behavior.

    Args:
        width: preferred width (int, "auto", "{f}%", or Sizing)
        height: preferred height (same accepted formats as width)
    """

    def __init__(self, width: SizingLike = 0, height: SizingLike = 0):
        super().__init__(width=width, height=height)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred size based on Sizings.

        - fixed: return the fixed value
        - auto/flex: return 0 (minimum size, parent will allocate)
        """
        w_dim = self.width_sizing
        h_dim = self.height_sizing

        pref_w = int(w_dim.value) if w_dim.kind == "fixed" else 0
        pref_h = int(h_dim.value) if h_dim.kind == "fixed" else 0

        _ = (max_width, max_height)

        return (pref_w, pref_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        # record last rect (invisible widget)
        self.set_last_rect(x, y, width, height)
