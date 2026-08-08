"""Typed overlay surface for ViewModels."""

from __future__ import annotations

from typing import Any, Protocol

from nuiitivet.navigation.route import Route
from nuiitivet.widgeting.widget import Widget


class OverlayProtocol(Protocol):
    """The core overlay surface a ViewModel depends on.

    Core :class:`~nuiitivet.overlay.overlay.Overlay` offers no scenario-specific
    presentation APIs -- ``dialog``, ``snackbar``, and the sheets live on
    :class:`~nuiitivet.material.overlay.MaterialOverlay`. A ViewModel that only
    dismisses overlays can depend on this protocol; one that presents them
    should use ``nuiitivet.material.OverlayProtocol``
    (:class:`~nuiitivet.material.protocols.MaterialOverlayProtocol`), which
    extends this one.
    """

    def close(self, value: Any = None, target: Widget | Route | None = None) -> None:
        """Close an overlay entry, optionally with a result value.

        Args:
            value: Result delivered to the awaiting caller.
            target: Entry to close, identified by its route or a widget inside
                it. Defaults to the topmost entry.
        """
        ...
