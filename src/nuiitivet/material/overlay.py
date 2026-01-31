"""Material-specific overlay helpers."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Any, Callable, Literal, Mapping

from nuiitivet.material import Text
from nuiitivet.material.loading_indicator import LoadingIndicator
from nuiitivet.material.buttons import TextButton
from nuiitivet.material.dialogs import AlertDialog
from nuiitivet.material.snackbar import Snackbar
from nuiitivet.navigation.route import Route
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.intent_resolver import IntentResolver
from nuiitivet.overlay.overlay_handle import OverlayHandle
from nuiitivet.overlay.overlay_position import OverlayPosition
from nuiitivet.widgeting.widget import Widget

from .intents import AlertDialogIntent, LoadingIntent


class _MappingIntentResolver(IntentResolver):
    def __init__(self, factories: Mapping[type[Any], Callable[[Any], Widget | Route]]) -> None:
        self._factories = dict(factories)

    def resolve(self, intent: Any) -> Widget | Route:
        factory = self._factories.get(type(intent))
        if factory is None:
            raise RuntimeError(f"No overlay intent is registered: {type(intent).__name__}")
        return factory(intent)


class MaterialOverlay(Overlay):
    """Overlay subclass that provides Material-specific helpers."""

    def __init__(
        self,
        *,
        intent_resolver: IntentResolver | None = None,
        intents: Mapping[type[Any], Callable[[Any], Widget | Route]] | None = None,
    ) -> None:
        super().__init__()

        if intent_resolver is not None and intents is not None:
            raise ValueError("Specify only one of intent_resolver or intents")

        if intent_resolver is None:
            defaults: dict[type[Any], Callable[[Any], Widget | Route]] = {
                AlertDialogIntent: lambda i: AlertDialog(
                    title=i.title,
                    message=i.message,
                    icon=i.icon,
                    actions=[TextButton("OK", on_click=lambda: Overlay.root().close(None), width=80)],
                ),
                LoadingIntent: lambda _: LoadingIndicator(),
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
        position: OverlayPosition | None = None,
    ) -> OverlayHandle[Any]:
        if isinstance(dialog, (Widget, Route)):
            resolved: Widget | Route = dialog
        else:
            resolved = self._intent_resolver.resolve(dialog)

        if dismiss_on_outside_tap is None:
            dismiss_on_outside_tap = True

        return self.show(
            resolved,
            passthrough=False,
            dismiss_on_outside_tap=bool(dismiss_on_outside_tap),
            timeout=timeout,
            position=position,
        )

    def snackbar(
        self,
        message: str,
        *,
        duration: float = 3.0,
    ) -> OverlayHandle[None]:
        return self.show(
            Snackbar(str(message)),
            passthrough=True,
            dismiss_on_outside_tap=False,
            timeout=float(duration),
            position=OverlayPosition.alignment("bottom-center", offset=(0.0, -24.0)),
        )

    class _LoadingContext(AbstractContextManager[None], AbstractAsyncContextManager[None]):
        def __init__(self, overlay: "MaterialOverlay", indicator: Widget | Route) -> None:
            self._overlay = overlay
            self._indicator = indicator
            self._handle: OverlayHandle[Any] | None = None

        def __enter__(self) -> None:
            self._handle = self._overlay.show(
                self._indicator,
                passthrough=False,
                dismiss_on_outside_tap=False,
                timeout=None,
                position=OverlayPosition.alignment("center"),
            )
            return None

        def __exit__(self, exc_type, exc, tb) -> Literal[False]:
            handle = self._handle
            self._handle = None
            if handle is not None:
                handle.close(None)
            return False

        async def __aenter__(self) -> None:
            return self.__enter__()

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return self.__exit__(exc_type, exc, tb)

    def loading(
        self,
        indicator: Widget | Route | Any | None = None,
    ) -> "MaterialOverlay._LoadingContext":
        if indicator is None:
            resolved: Widget | Route = self._intent_resolver.resolve(LoadingIntent())
        elif isinstance(indicator, (Widget, Route)):
            resolved = indicator
        else:
            resolved = self._intent_resolver.resolve(indicator)
        return MaterialOverlay._LoadingContext(self, resolved)
