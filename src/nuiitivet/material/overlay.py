"""Material-specific overlay helpers."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Any, Callable, Literal, Mapping

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
from nuiitivet.widgeting.widget import Widget
from .overlay_visual_state import MaterialOverlayLayerComposer
from .sheet import BottomSheet, SideSheet
from .transition_spec import (
    MaterialTransitions,
)

from .intents import BasicDialogIntent, LoadingIntent


class _MappingIntentResolver(IntentResolver):
    def __init__(self, factories: Mapping[type[Any], Callable[[Any], Widget | Route]]) -> None:
        self._factories = dict(factories)

    def resolve(self, intent: Any) -> Widget | Route:
        factory = self._factories.get(type(intent))
        if factory is None:
            raise RuntimeError(f"No overlay intent is registered: {type(intent).__name__}")
        return factory(intent)


class WhileLoading(AbstractContextManager[None], AbstractAsyncContextManager[None]):
    """Context manager that shows a loading indicator for the duration of a block.

    Returned by :meth:`MaterialOverlay.while_loading`. Supports both ``with`` and
    ``async with`` usage::

        with MaterialOverlay.of(self).while_loading():
            do_work()

        async with MaterialOverlay.of(self).while_loading():
            await fetch_data()
    """

    def __init__(self, overlay: "MaterialOverlay", indicator: Widget | Route | Any | None) -> None:
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
                    transition_spec=MaterialTransitions.dialog(),
                    barrier_dismissible=False,
                ),
            }
            if intents:
                defaults.update(intents)
            intent_resolver = _MappingIntentResolver(defaults)

        self._intent_resolver = intent_resolver

    @classmethod
    def root(cls) -> "MaterialOverlay":
        overlay = Overlay.root()
        if not isinstance(overlay, cls):
            raise RuntimeError(f"Root overlay is not {cls.__name__}")
        return overlay

    @classmethod
    def of(cls, context: Widget, root: bool = False) -> "MaterialOverlay":
        if root:
            return cls.root()

        found = context.find_ancestor(cls)
        if found is None:
            raise RuntimeError(
                f"No {cls.__name__} found in the widget tree above {context.__class__.__name__}. "
                "Did you forget to initialize MaterialApp with MaterialOverlay?"
            )
        return found

    def dialog(
        self,
        dialog: Widget | Route | Any,
        *,
        dismiss_on_outside_tap: bool | None = None,
        timeout: float | None = None,
    ) -> OverlayHandle[Any]:
        if dismiss_on_outside_tap is None:
            dismiss_on_outside_tap = True

        route = self._normalize_dialog_to_route(
            dialog,
            dismiss_on_outside_tap=bool(dismiss_on_outside_tap),
        )

        return self.show_modal(
            route,
            dismiss_on_outside_tap=bool(dismiss_on_outside_tap),
            timeout=timeout,
        )

    def _normalize_dialog_to_route(
        self,
        dialog: Widget | Route | Any,
        *,
        dismiss_on_outside_tap: bool,
    ) -> Route:
        """Normalize dialog input to a Route.

        This is the single boundary adapter for `dialog(...)` input polymorphism.
        """
        resolved: Widget | Route
        if isinstance(dialog, (Widget, Route)):
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
        message: str | Snackbar | OverlayRoute,
        *,
        duration: float = 3.0,
    ) -> OverlayHandle[None]:
        if isinstance(message, OverlayRoute):
            route: Route = message
            return self.show_modeless(
                route,
                timeout=float(duration),
                position=OverlayPosition.alignment("bottom-center", offset=(0.0, -24.0)),
            )
        widget: Widget = message if isinstance(message, Snackbar) else Snackbar(str(message))
        return self.show_modeless(
            widget,
            timeout=float(duration),
            position=OverlayPosition.alignment("bottom-center", offset=(0.0, -24.0)),
            transition_spec=MaterialTransitions.snackbar(),
        )

    def loading(
        self,
        indicator: Widget | Route | Any | None = None,
    ) -> OverlayHandle[Any]:
        """Show a loading indicator overlay and return a handle for manual dismissal.

        Args:
            indicator: Widget, Route, or intent to display as the loading indicator.
                Defaults to the built-in :class:`LoadingIndicator`.

        Returns:
            An :class:`OverlayHandle` that can be closed via ``handle.close(None)``.
        """
        if indicator is None:
            resolved: Widget | Route = self._intent_resolver.resolve(LoadingIntent())
        elif isinstance(indicator, (Widget, Route)):
            resolved = indicator
        else:
            resolved = self._intent_resolver.resolve(indicator)
        return self.show_modal(
            resolved,
            dismiss_on_outside_tap=False,
            timeout=None,
            position=OverlayPosition.alignment("center"),
        )

    def while_loading(
        self,
        indicator: Widget | Route | Any | None = None,
    ) -> WhileLoading:
        """Return a context manager that shows a loading indicator for the duration of a block.

        Use this form when the loading state is scoped to a ``with`` or ``async with`` block::

            with MaterialOverlay.of(self).while_loading():
                do_work()

            async with MaterialOverlay.of(self).while_loading():
                await fetch_data()

        Internally delegates show/close to :meth:`loading`.

        Args:
            indicator: Widget, Route, or intent to display as the loading indicator.
                Defaults to the built-in :class:`LoadingIndicator`.

        Returns:
            A :class:`LoadingScope` context manager that shows the indicator on entry and closes it on exit.
        """
        return WhileLoading(self, indicator)

    def side_sheet(
        self,
        sheet: SideSheet,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal side sheet.

        The sheet's position, corner radii, and transition direction are derived
        from ``sheet.side``.  Visual styling (background, size, corner radius) is
        fully owned by the :class:`SideSheet` widget.

        Args:
            sheet: SideSheet widget that defines content, headline, and styling.
            dismiss_on_outside_tap: Whether tapping the scrim dismisses the sheet.
                Defaults to ``True``.
        """
        alignment = "top-right" if sheet.side == "right" else "top-left"

        route = OverlayRoute(
            builder=lambda: sheet,
            transition_spec=MaterialTransitions.side_sheet(side=sheet.side),
            barrier_dismissible=bool(dismiss_on_outside_tap),
        )

        return self.show_modal(
            route,
            dismiss_on_outside_tap=bool(dismiss_on_outside_tap),
            position=OverlayPosition.alignment(alignment),
        )

    def bottom_sheet(
        self,
        sheet: BottomSheet,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal bottom sheet sliding up from the bottom edge.

        Visual styling (background, size, corner radius) is fully owned by the
        :class:`BottomSheet` widget.

        Args:
            sheet: BottomSheet widget that defines content, headline, and styling.
            dismiss_on_outside_tap: Whether tapping the scrim dismisses the sheet.
                Defaults to ``True``.
        """
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
