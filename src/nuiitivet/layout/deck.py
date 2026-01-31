"""Deck layout: display only one child at a time."""

from typing import Optional, Sequence, Tuple, Union

from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from ..observable.value import _ObservableValue
from .measure import preferred_size as measure_preferred_size


class Deck(Widget):
    """Display only one child at a time.

    All children remain mounted (state preserved), but only the selected
    child is visible and rendered.

    Usage:
        Deck(children=[HomeTab(), SearchTab(), ProfileTab()], index=0)

    For type-safe index, use IntEnum:
        class Section(IntEnum):
            HOME = 0
            SEARCH = 1
        Deck(children=[...], index=Section.HOME)

    For animated tabs with gesture support, see DeckController.
    """

    def __init__(
        self,
        children: Optional[Sequence[Widget]] = None,
        index: Union[int, _ObservableValue[int]] = 0,
        *,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Union[int, Tuple[int, int], Tuple[int, int, int, int]] = 0,
    ) -> None:
        """Initialize the Deck layout.

        Args:
            children: A list of child widgets. All are mounted, but only one is visible.
            index: The index of the child to display. Can be an integer or an Observable[int].
                Defaults to 0.
            width: The preferred width of the container. Defaults to None.
            height: The preferred height of the container. Defaults to None.
            padding: Padding to apply around the visible child. Defaults to 0.
        """
        super().__init__(width=width, height=height, padding=padding)

        # Add all children
        if children:
            for child in children:
                self.add_child(child)

        # Handle index (Observable or plain int)
        self._index_observable: Optional[_ObservableValue[int]] = None
        self._index_subscription = None
        if isinstance(index, _ObservableValue):
            self._index_observable = index
            self._current_index = index.value
            # Subscribe to changes
            self._index_subscription = index.subscribe(self._on_index_changed)
        else:
            self._current_index = int(index)

        # Validate initial index
        self._validate_index()

    def _on_index_changed(self, new_index: int) -> None:
        """Handle Observable index changes."""
        old_index = self._current_index
        self._current_index = new_index
        self._validate_index()
        if old_index != self._current_index:
            self.mark_needs_layout()

    def _validate_index(self) -> None:
        """Ensure index is within valid range."""
        children = self.children_snapshot()
        if not children:
            self._current_index = 0
            return

        if self._current_index < 0 or self._current_index >= len(children):
            # Clamp to valid range
            self._current_index = max(0, min(self._current_index, len(children) - 1))

    @property
    def current_index(self) -> int:
        """Get the currently selected child index."""
        return self._current_index

    def set_index(self, index: int) -> None:
        """Set the selected child index (for non-Observable usage)."""
        if self._index_observable is not None:
            raise ValueError("Cannot set_index when using Observable index")
        old_index = self._current_index
        self._current_index = index
        self._validate_index()
        if old_index != self._current_index:
            self.mark_needs_layout()

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        children = self.children_snapshot()
        if not children or self._current_index >= len(children):
            # No children or invalid index
            pad_left, pad_top, pad_right, pad_bottom = self.padding
            width = pad_left + pad_right
            height = pad_top + pad_bottom
            if max_width is not None and self.width_sizing.kind != "fixed":
                width = min(width, int(max_width))
            if max_height is not None and self.height_sizing.kind != "fixed":
                height = min(height, int(max_height))
            return (width, height)

        # Get size from currently selected child
        selected_child = children[self._current_index]
        pad_left, pad_top, pad_right, pad_bottom = self.padding
        child_max_w: Optional[int] = None
        child_max_h: Optional[int] = None
        if max_width is not None:
            child_max_w = max(0, int(max_width) - int(pad_left) - int(pad_right))
        elif self.width_sizing.kind == "fixed":
            child_max_w = max(0, int(self.width_sizing.value) - int(pad_left) - int(pad_right))
        if max_height is not None:
            child_max_h = max(0, int(max_height) - int(pad_top) - int(pad_bottom))
        elif self.height_sizing.kind == "fixed":
            child_max_h = max(0, int(self.height_sizing.value) - int(pad_top) - int(pad_bottom))
        child_w, child_h = measure_preferred_size(selected_child, max_width=child_max_w, max_height=child_max_h)

        width = int(child_w) + int(pad_left) + int(pad_right)
        height = int(child_h) + int(pad_top) + int(pad_bottom)

        w_dim = self.width_sizing
        h_dim = self.height_sizing
        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        elif max_width is not None:
            width = min(width, int(max_width))

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        elif max_height is not None:
            height = min(height, int(max_height))

        return (width, height)

    def layout(self, width: int, height: int) -> None:
        """Layout all children (to preserve state), position selected child."""
        super().layout(width, height)
        children = self.children_snapshot()
        if not children:
            return

        pad_left, pad_top, pad_right, pad_bottom = self.padding
        available_w = max(0, width - pad_left - pad_right)
        available_h = max(0, height - pad_top - pad_bottom)

        # Layout ALL children so they maintain state
        for child in children:
            child.layout(available_w, available_h)

        # Position selected child (others will not be painted)
        if 0 <= self._current_index < len(children):
            selected_child = children[self._current_index]
            selected_child.set_layout_rect(pad_left, pad_top, available_w, available_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        """Paint only the selected child."""
        children = self.children_snapshot()
        if not children or self._current_index >= len(children):
            return

        # Auto-layout fallback for tests or direct paint calls
        if any(c.layout_rect is None for c in children):
            self.layout(width, height)

        # Only paint the selected child
        selected_child = children[self._current_index]
        rect = selected_child.layout_rect
        if rect is None:
            return

        rel_x, rel_y, w, h = rect
        abs_x = x + rel_x
        abs_y = y + rel_y

        selected_child.set_last_rect(abs_x, abs_y, w, h)
        selected_child.paint(canvas, abs_x, abs_y, w, h)

    def hit_test(self, x: int, y: int) -> bool:
        """Only allow hit testing on the selected child."""
        children = self.children_snapshot()
        if not children or self._current_index >= len(children):
            return False

        # Only the selected child should participate in hit testing
        selected_child = children[self._current_index]
        return selected_child.hit_test(x, y)

    def dispose(self) -> None:
        """Clean up subscriptions."""
        if self._index_subscription is not None:
            self._index_subscription.dispose()
            self._index_subscription = None
        # Note: Widget class doesn't have dispose, but we follow the pattern
        # for future compatibility
