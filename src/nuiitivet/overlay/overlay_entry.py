"""OverlayEntry manages a single overlay widget."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional

from nuiitivet.common.logging_once import exception_once


logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from nuiitivet.widgeting.widget import Widget


class OverlayEntry:
    """Represents a single overlay entry (dialog, toast, etc.).

    An overlay entry manages the lifecycle of a widget that should be
    displayed on top of other content. It uses a builder pattern to
    create the widget on demand.

    Example:
        def build_dialog():
            return AlertDialog(
                title=Text("Confirm"),
                content=Text("Are you sure?"),
                actions=[
                    TextButton("Cancel", on_click=lambda: overlay.close(False)),
                    TextButton("OK", on_click=lambda: overlay.close(True)),
                ]
            )

        entry = OverlayEntry(builder=build_dialog)
    """

    def __init__(self, builder: Callable[[], Widget], *, on_dispose: Callable[[], None] | None = None):
        """Create an overlay entry.

        Args:
            builder: A function that returns a Widget to display.
            on_dispose: Optional callback invoked when the entry is disposed.
        """
        self.builder = builder
        self._on_dispose = on_dispose
        self._widget: Optional[Widget] = None
        self._is_visible = True

    def build_widget(self) -> Widget:
        """Build and cache the widget.

        Returns:
            The widget to display in the overlay.
        """
        if self._widget is None:
            self._widget = self.builder()
        return self._widget

    @property
    def is_visible(self) -> bool:
        """Check if this entry is visible."""
        return self._is_visible

    def mark_for_removal(self) -> None:
        """Mark this entry for removal from the overlay."""
        self._is_visible = False

    def dispose(self) -> None:
        """Clean up resources associated with this entry."""
        if self._on_dispose is not None:
            try:
                self._on_dispose()
            except Exception:
                exception_once(logger, "overlay_entry_on_dispose_exc", "OverlayEntry on_dispose callback raised")
        if self._widget is not None:
            if hasattr(self._widget, "unmount"):
                try:
                    self._widget.unmount()
                except Exception:
                    exception_once(
                        logger,
                        f"overlay_entry_widget_unmount_exc:{type(self._widget).__name__}",
                        "OverlayEntry widget.unmount raised (widget=%s)",
                        type(self._widget).__name__,
                    )
        self._widget = None
        self._is_visible = False
