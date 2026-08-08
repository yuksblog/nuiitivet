"""Typed Material overlay surface for ViewModels."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from nuiitivet.material.overlay import WhileLoading
from nuiitivet.material.snackbar import Snackbar
from nuiitivet.overlay.overlay_handle import OverlayHandle
from nuiitivet.overlay.protocols import OverlayProtocol
from nuiitivet.widgeting.widget import Widget


class MaterialOverlayProtocol(OverlayProtocol, Protocol):
    """The Material overlay surface a ViewModel depends on.

    Exported as ``nuiitivet.material.OverlayProtocol``, mirroring how
    ``nuiitivet.material.Overlay`` names
    :class:`~nuiitivet.material.overlay.MaterialOverlay`. Annotate an injected
    overlay with it so the ViewModel presents content without owning widgets::

        class ItemViewModel:
            def __init__(self, overlay: nv.OverlayProtocol) -> None:
                self._overlay = overlay

            async def delete(self) -> None:
                await self._overlay.dialog(BasicDialogIntent(title="Delete?"))

    Prefer passing intents rather than widgets: ``dialog`` and ``loading``
    resolve them through the overlay's intent resolver, keeping widget
    construction in the View layer. The sheet methods still require a widget --
    intent support for them is not implemented yet.
    """

    def dialog(
        self,
        dialog: Widget | Any,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal dialog from a widget or an intent."""
        ...

    def snackbar(
        self,
        message: str | Snackbar,
        *,
        duration: float = 3.0,
    ) -> OverlayHandle[None]:
        """Display a brief, non-blocking snackbar."""
        ...

    def loading(
        self,
        indicator: Widget | Any | None = None,
    ) -> OverlayHandle[Any]:
        """Show a loading indicator and return a handle for manual dismissal."""
        ...

    def while_loading(
        self,
        indicator: Widget | Any | None = None,
    ) -> WhileLoading:
        """Return a (sync or async) context manager that shows a loading indicator."""
        ...

    def side_sheet(
        self,
        sheet: Widget,
        *,
        side: Literal["right", "left"] = "right",
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal side sheet."""
        ...

    def bottom_sheet(
        self,
        sheet: Widget,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal bottom sheet."""
        ...
