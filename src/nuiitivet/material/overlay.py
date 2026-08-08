"""Material-specific overlay helpers."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Any, Callable, Literal, Mapping, Protocol, TypeVar

from nuiitivet.material.loading_indicator import LoadingIndicator
from nuiitivet.material.buttons import Button
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.material.snackbar import Snackbar
from nuiitivet.navigation.route import Route
from nuiitivet.overlay.overlay_route import OverlayRoute
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.intent_resolver import IntentResolver
from nuiitivet.overlay.overlay_handle import OverlayHandle
from nuiitivet.overlay.overlay_position import OverlayPosition
from nuiitivet.modifiers.corner_radius import corner_radius
from nuiitivet.widgeting.widget import Widget
from .overlay_visual_state import MaterialOverlayLayerComposer
from .sheet import BottomSheet, SideSheet
from .transition_spec import (
    MaterialTransitions,
)

from .intents import BasicDialogIntent, LoadingIntent

_T = TypeVar("_T", bound=Widget)


def _find_descendant(widget: Widget, target: type[_T]) -> _T | None:
    """Return the first descendant (or *widget* itself) of type *target*."""
    if isinstance(widget, target):
        return widget
    for child in widget.children:
        if isinstance(child, Widget):
            found = _find_descendant(child, target)
            if found is not None:
                return found
    return None


class _MappingIntentResolver(IntentResolver):
    def __init__(self, factories: Mapping[type[Any], Callable[[Any], Widget | Route]]) -> None:
        self._factories = dict(factories)

    def resolve(self, intent: Any) -> Widget | Route:
        factory = self._factories.get(type(intent))
        if factory is None:
            raise RuntimeError(f"No overlay intent is registered: {type(intent).__name__}")
        return factory(intent)


class _LoadingHost(Protocol):
    """The single method :class:`WhileLoading` delegates to.

    Typing the host structurally keeps :class:`WhileLoading` usable from a
    ViewModel test double that implements ``MaterialOverlayProtocol`` without
    inheriting :class:`MaterialOverlay`.
    """

    def loading(self, indicator: Widget | Any | None = None) -> OverlayHandle[Any]: ...


class WhileLoading(AbstractContextManager[None], AbstractAsyncContextManager[None]):
    """Context manager that shows a loading indicator for the duration of a block.

    Returned by :meth:`MaterialOverlay.while_loading`. Supports both ``with`` and
    ``async with`` usage::

        with MaterialOverlay.of(self).while_loading():
            do_work()

        async with MaterialOverlay.of(self).while_loading():
            await fetch_data()
    """

    def __init__(self, overlay: _LoadingHost, indicator: Widget | Any | None) -> None:
        self._overlay = overlay
        self._indicator = indicator
        self._handle: OverlayHandle[Any] | None = None

    def __enter__(self) -> None:
        self._handle = self._overlay.loading(self._indicator)
        return None

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
        handle = self._handle
        self._handle = None
        if handle is not None:
            handle.close(None)
        return False

    async def __aenter__(self) -> None:
        return self.__enter__()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return self.__exit__(exc_type, exc, tb)


class MaterialOverlay(Overlay):
    """Overlay subclass that provides Material-specific helpers."""

    def __init__(
        self,
        *,
        intent_resolver: IntentResolver | None = None,
        intents: Mapping[type[Any], Callable[[Any], Widget | Route]] | None = None,
    ) -> None:
        super().__init__(layer_composer=MaterialOverlayLayerComposer())

        if intent_resolver is not None and intents is not None:
            raise ValueError("Specify only one of intent_resolver or intents")

        if intent_resolver is None:
            defaults: dict[type[Any], Callable[[Any], Widget | Route]] = {
                BasicDialogIntent: lambda i: OverlayRoute(
                    builder=lambda: BasicDialog(
                        title=i.title,
                        message=i.message,
                        icon=i.icon,
                        actions=[
                            Button(
                                "OK",
                                on_click=lambda: Overlay.root().close(None),
                                width=80,
                                style=ButtonStyle.text(),
                            )
                        ],
                    ),
                    transition_spec=MaterialTransitions.dialog(),
                ),
                LoadingIntent: lambda _: OverlayRoute(
                    builder=lambda: LoadingIndicator(),
                    transition_spec=None,
                    barrier_dismissible=False,
                ),
            }
            if intents:
                defaults.update(intents)
            intent_resolver = _MappingIntentResolver(defaults)

        self._intent_resolver = intent_resolver

    def dialog(
        self,
        dialog: Widget | Any,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal Material dialog.

        Args:
            dialog: A :class:`Widget` to display as the dialog, or an intent
                resolved by the overlay's intent resolver (e.g.
                :class:`BasicDialogIntent`). To present a fully custom
                :class:`Route`, call :meth:`show_modal` directly.
            dismiss_on_outside_tap: Whether tapping the scrim dismisses the
                dialog. Defaults to ``True``.

        Returns:
            An :class:`OverlayHandle` for manual dismissal.
        """
        route = self._normalize_dialog_to_route(
            dialog,
            dismiss_on_outside_tap=dismiss_on_outside_tap,
        )

        return self.show_modal(
            route,
            dismiss_on_outside_tap=dismiss_on_outside_tap,
        )

    def _normalize_dialog_to_route(
        self,
        dialog: Widget | Any,
        *,
        dismiss_on_outside_tap: bool,
    ) -> Route:
        """Normalize dialog input to a Route.

        This is the single boundary adapter for `dialog(...)` input polymorphism.
        A :class:`Widget` is presented directly; any other value is resolved
        through the intent resolver, which may yield a :class:`Widget` or a
        :class:`Route`.
        """
        resolved: Widget | Route
        if isinstance(dialog, Widget):
            resolved = dialog
        else:
            resolved = self._intent_resolver.resolve(dialog)

        if isinstance(resolved, Route):
            return resolved

        widget = resolved
        return OverlayRoute(
            builder=lambda: widget,
            transition_spec=MaterialTransitions.dialog(),
            barrier_dismissible=bool(dismiss_on_outside_tap),
        )

    def snackbar(
        self,
        message: str | Snackbar,
        *,
        duration: float = 3.0,
    ) -> OverlayHandle[None]:
        """Display a brief, non-blocking Material snackbar.

        Args:
            message: The message text, or a pre-built :class:`Snackbar` widget.
            duration: Seconds before the snackbar auto-dismisses. Defaults to ``3.0``.

        Returns:
            An :class:`OverlayHandle` for the shown snackbar.
        """
        widget: Widget = message if isinstance(message, Snackbar) else Snackbar(str(message))
        return self.show_modeless(
            widget,
            timeout=float(duration),
            position=OverlayPosition.alignment("bottom-center", offset=(0.0, -24.0)),
            transition_spec=MaterialTransitions.snackbar(),
        )

    def loading(
        self,
        indicator: Widget | Any | None = None,
    ) -> OverlayHandle[Any]:
        """Show a loading indicator overlay and return a handle for manual dismissal.

        Args:
            indicator: Widget or intent to display as the loading indicator.
                Defaults to the built-in :class:`LoadingIndicator`, resolved
                through the :class:`LoadingIntent` (overridable via the app's
                ``overlay_routes``).

        Returns:
            An :class:`OverlayHandle` that can be closed via ``handle.close(None)``.
        """
        if indicator is None:
            resolved: Widget | Route = self._intent_resolver.resolve(LoadingIntent())
        elif isinstance(indicator, Widget):
            resolved = indicator
        else:
            resolved = self._intent_resolver.resolve(indicator)
        return self.show_modeless(
            resolved,
            timeout=None,
            position=OverlayPosition.alignment("center"),
        )

    def while_loading(
        self,
        indicator: Widget | Any | None = None,
    ) -> WhileLoading:
        """Return a context manager that shows a loading indicator for the duration of a block.

        Use this form when the loading state is scoped to a ``with`` or ``async with`` block::

            with MaterialOverlay.of(self).while_loading():
                do_work()

            async with MaterialOverlay.of(self).while_loading():
                await fetch_data()

        Internally delegates show/close to :meth:`loading`.

        Args:
            indicator: Widget or intent to display as the loading indicator.
                Defaults to the built-in :class:`LoadingIndicator`.

        Returns:
            A :class:`WhileLoading` context manager that shows the indicator on entry and closes it on exit.
        """
        return WhileLoading(self, indicator)

    def side_sheet(
        self,
        sheet: Widget,
        *,
        side: Literal["right", "left"] = "right",
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal side sheet.

        The slide-in edge is a placement concern owned by this method: ``side``
        controls the sheet's alignment, transition direction, and which (inner,
        away-from-edge) corners are rounded.  The corner rounding is applied here
        via the :func:`corner_radius` modifier, using the radius from
        ``SideSheet.style``; the :class:`SideSheet` widget itself renders a
        square container.

        Args:
            sheet: SideSheet widget (or a wrapper such as one produced by
                ``.modifier(will_pop(...))``) that defines content, headline,
                and styling.
            side: Edge the sheet slides in from (``"right"`` or ``"left"``).
                Defaults to ``"right"``.
            dismiss_on_outside_tap: Whether tapping the scrim dismisses the sheet.
                Defaults to ``True``.
        """
        inner = _find_descendant(sheet, SideSheet)
        if inner is None:
            raise TypeError("side_sheet() requires a SideSheet widget (possibly wrapped by modifiers)")

        cr = float(inner.style.corner_radius)
        # Round only the inner (away-from-edge) corners: (tl, tr, br, bl).
        radius = (cr, 0.0, 0.0, cr) if side == "right" else (0.0, cr, cr, 0.0)
        presented = sheet.modifier(corner_radius(radius))
        alignment = "top-right" if side == "right" else "top-left"

        route = OverlayRoute(
            builder=lambda: presented,
            transition_spec=MaterialTransitions.side_sheet(side=side),
            barrier_dismissible=bool(dismiss_on_outside_tap),
        )

        return self.show_modal(
            route,
            dismiss_on_outside_tap=bool(dismiss_on_outside_tap),
            position=OverlayPosition.alignment(alignment),
        )

    def bottom_sheet(
        self,
        sheet: Widget,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal bottom sheet sliding up from the bottom edge.

        Visual styling (background, size, corner radius) is fully owned by the
        :class:`BottomSheet` widget.

        Args:
            sheet: BottomSheet widget (or a wrapper such as one produced by
                ``.modifier(will_pop(...))``) that defines content, headline,
                and styling.
            dismiss_on_outside_tap: Whether tapping the scrim dismisses the sheet.
                Defaults to ``True``.
        """
        if _find_descendant(sheet, BottomSheet) is None:
            raise TypeError("bottom_sheet() requires a BottomSheet widget (possibly wrapped by modifiers)")
        route = OverlayRoute(
            builder=lambda: sheet,
            transition_spec=MaterialTransitions.bottom_sheet(),
            barrier_dismissible=bool(dismiss_on_outside_tap),
        )

        return self.show_modal(
            route,
            dismiss_on_outside_tap=bool(dismiss_on_outside_tap),
            position=OverlayPosition.alignment("bottom-center"),
        )
