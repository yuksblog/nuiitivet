"""What ``Overlay.proxy(widget)`` returns."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from nuiitivet.widgeting.context_lookup import ContextProxy
from nuiitivet.widgeting.widget import Widget

from .protocols import OverlayProtocol

OverlayT = TypeVar("OverlayT", bound=OverlayProtocol)


class OverlayProxy(ContextProxy[OverlayT], Generic[OverlayT]):
    """Forwards :class:`~nuiitivet.overlay.protocols.OverlayProtocol` to the overlay of one widget.

    A call after the widget is unmounted does nothing.
    """

    def close(self, value: Any = None, target: Widget | None = None) -> None:
        """Close an overlay entry, optionally with a result value.

        Args:
            value: Result delivered to the awaiting caller.
            target: A widget inside the entry to close. Defaults to the
                topmost entry.
        """
        overlay = self._provider()
        if overlay is not None:
            overlay.close(value, target)
