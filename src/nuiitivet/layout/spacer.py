"""Spacer widget moved to its own module.

This module defines the Spacer widget which is a tiny utility that
reserves space in layouts.
"""

from typing import Optional, Tuple

from ..rendering.padding import PaddingLike
from ..rendering.sizing import SizingLike
from ..widgeting.widget import Widget


class Spacer(Widget):
    """Invisible widget that reserves space.

    This single Spacer supports both fixed-size and space-filling behavior.

    Args:
        width: preferred width (int, "auto", "wt", "wt{n}", or Sizing)
        height: preferred height (same accepted formats as width)
        padding: insets added around the reserved space
    """

    def __init__(
        self,
        *,
        width: SizingLike = 0,
        height: SizingLike = 0,
        padding: PaddingLike = 0,
        key: Optional[str] = None,
    ):
        """Initialize a Spacer.

        Args:
            width: Preferred width. Use Sizing.weight() or 0 for filling space.
            height: Preferred height. Use Sizing.weight() or 0 for filling space.
            padding: Insets from the allocated rect to the reserved space.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(width=width, height=height, padding=padding, key=key)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        """Return preferred size based on Sizings, plus padding.

        - fixed: return the fixed value
        - auto/weight: return 0 (minimum size, parent will allocate)
        """
        w_dim = self.width_sizing
        h_dim = self.height_sizing
        l, t, r, b = self.padding

        pref_w = (int(w_dim.value) if w_dim.kind == "fixed" else 0) + l + r
        pref_h = (int(h_dim.value) if h_dim.kind == "fixed" else 0) + t + b

        _ = (max_width, max_height)

        return (pref_w, pref_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        # record last rect (invisible widget)
        self.set_last_rect(x, y, width, height)
