"""Title bar configuration for the application."""

from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from nuiitivet.widgeting.widget import Widget

from nuiitivet.widgets.interaction import InteractionRegion, DraggableNode


from nuiitivet.rendering.sizing import SizingLike


class TitleBar:
    """Base class for title bar configuration."""

    def __init__(self, title: Optional[str] = None):
        self.title = title


class DefaultTitleBar(TitleBar):
    """Configuration for the default OS title bar.

    Attributes:
        title: The window title.
        icon: Path to the window icon.
    """

    def __init__(
        self,
        title: Optional[str] = None,
        icon: Optional[str] = None,
    ):
        super().__init__(title)
        self.icon = icon

    def __repr__(self) -> str:
        return f"DefaultTitleBar(title={self.title!r}, icon={self.icon!r})"


class CustomTitleBar(TitleBar):
    """Configuration for a custom title bar."""

    def __init__(self, content: "Widget", title: Optional[str] = None):
        """Initialize with custom content.

        Args:
            content: The widget to render as the title bar.
            title: The window title (used for taskbar/dock, but not rendered by OS).
        """
        super().__init__(title)
        self.content = content


class WindowDragArea(InteractionRegion):
    """A widget that allows dragging the window."""

    def __init__(
        self,
        child: "Widget",
        on_drag: Callable[[float, float], None],
        width: SizingLike = None,
        height: SizingLike = None,
    ):
        super().__init__(child, width=width, height=height)
        self._draggable = DraggableNode(on_drag_update=lambda e, dx, dy: on_drag(dx, dy))
        self.add_node(self._draggable)

    def notify_window_moved(self, dx: float, dy: float) -> None:
        """Notify that the window has moved, so we can adjust internal drag state."""
        # Adjust the last position of the draggable node to account for window movement.
        # If the window moves by (dx, dy), the mouse position relative to the window
        # moves by (-dx, -dy). We update _last_pos so the next delta calculation is correct.
        if self._draggable._last_pos is not None:
            lx, ly = self._draggable._last_pos
            self._draggable._last_pos = (lx - dx, ly - dy)
