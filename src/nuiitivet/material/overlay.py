"""Material-specific overlay helpers."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Literal, Mapping, Protocol, TypeVar

from nuiitivet.material.loading_indicator import LoadingIndicator
from nuiitivet.material.buttons import Button
from nuiitivet.material.styles.button_style import ButtonStyle
from nuiitivet.material.dialogs import BasicDialog
from nuiitivet.material.snackbar import Snackbar
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.intent_resolver import IntentResolver, MappingIntentResolver
from nuiitivet.overlay.overlay_handle import OverlayHandle, disposed_handle
from nuiitivet.overlay.overlay_position import OverlayPosition
from nuiitivet.overlay.proxy import OverlayProxy
from nuiitivet.modifiers.corner_radius import corner_radius
from nuiitivet.widgeting.widget import Widget
from .overlay_visual_state import MaterialOverlayLayerComposer
from .sheet import BottomSheet, SideSheet
from .transition_spec import (
    MaterialTransitions,
)

from .intents import BasicDialogIntent, LoadingIntent

if TYPE_CHECKING:
    from .protocols import MaterialOverlayProtocol

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
        intents: Mapping[type[Any], Callable[[Any], Widget]] | None = None,
        key: str | None = None,
    ) -> None:
        super().__init__(layer_composer=MaterialOverlayLayerComposer(), key=key)

        if intent_resolver is not None and intents is not None:
            raise ValueError("Specify only one of intent_resolver or intents")

        if intent_resolver is None:
            defaults: dict[type[Any], Callable[[Any], Widget]] = {
                BasicDialogIntent: lambda i: BasicDialog(
                    title=i.title,
                    message=i.message,
                    icon=i.icon,
                    actions=[
                        Button(
                            "OK",
                            # This resolver belongs to the overlay hosting the
                            # dialog, so close it directly rather than looking
                            # one up.
                            on_click=lambda: self.close(None),
                            width=80,
                            style=ButtonStyle.text(),
                        )
                    ],
                ),
                LoadingIntent: lambda _: LoadingIndicator(),
            }
            if intents:
                defaults.update(intents)
            intent_resolver = MappingIntentResolver(defaults)

        self._intent_resolver = intent_resolver

    @classmethod
    def proxy(cls, context: Widget, root: bool = False) -> MaterialOverlayProtocol:
        """Return a stand-in for the ``MaterialOverlay`` that :meth:`of` resolves.

        Unlike :meth:`of` it can be called in ``__init__``, to hand an overlay
        to a ViewModel. Each call on it resolves the overlay at that moment.
        Before ``context`` is mounted a call raises ``RuntimeError``. After it
        is unmounted a call shows nothing: ``dialog``, ``snackbar``,
        ``loading`` and the sheets return a handle already completed with
        ``OverlayDismissReason.DISPOSED``, and ``while_loading`` runs its
        block with no indicator. It holds ``context`` weakly.

        Args:
            context: The widget to resolve from at each call.
            root: Skip the ancestor search and use the window's overlay.

        Raises:
            RuntimeError: If called before ``super().__init__()``.
        """
        return MaterialOverlayProxy(f"{cls.__name__}.proxy", context, lambda widget: cls.of(widget, root=root))

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
                :class:`BasicDialogIntent`). For a transition other than the
                MD3 dialog one, call :meth:`show` directly.
            dismiss_on_outside_tap: Whether tapping the scrim dismisses the
                dialog. Defaults to ``True``.

        Returns:
            An :class:`OverlayHandle` for manual dismissal. A dialog shown from an
            intent stays open across a hot reload, and the handle follows it.
        """
        handle = self.show(
            self._resolve(dialog),
            backdrop=True,
            dismiss_on_outside_tap=dismiss_on_outside_tap,
            transition=MaterialTransitions.dialog(),
        )
        if not isinstance(dialog, Widget):
            replay = partial(MaterialOverlay.dialog, dismiss_on_outside_tap=dismiss_on_outside_tap)
            self._record_for_restore(handle, dialog, replay)
        return handle

    def _resolve(self, content: Widget | Any) -> Widget:
        if isinstance(content, Widget):
            return content
        return self._intent_resolver.resolve(content)

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
        return self.show(
            widget,
            passthrough=True,
            timeout=float(duration),
            position=OverlayPosition.aligned("bottom-center", offset=(0.0, -24.0)),
            transition=MaterialTransitions.snackbar(),
        )

    def loading(
        self,
        indicator: Widget | Any | None = None,
    ) -> OverlayHandle[Any]:
        """Show a loading indicator overlay and return a handle for manual dismissal.

        Args:
            indicator: Widget or intent to display as the loading indicator.
                Defaults to the built-in :class:`LoadingIndicator`, resolved
                through the :class:`LoadingIntent` (overridable via the
                overlay's ``intents``).

        Returns:
            An :class:`OverlayHandle` that can be closed via ``handle.close(None)``.
        """
        return self.show(
            self._resolve(LoadingIntent() if indicator is None else indicator),
            passthrough=True,
            timeout=None,
            position=OverlayPosition.aligned("center"),
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
        sheet: Widget | Any,
        *,
        side: Literal["right", "left"] = "right",
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal side sheet.

        ``side`` sets the edge the sheet slides in from, its alignment, and
        which corners are rounded. The rounding uses ``SideSheet.style``.

        Args:
            sheet: A widget containing a :class:`SideSheet`, possibly wrapped
                by modifiers, or an intent resolved by the overlay's intent
                resolver.
            side: Edge the sheet slides in from (``"right"`` or ``"left"``).
                Defaults to ``"right"``.
            dismiss_on_outside_tap: Whether tapping the scrim dismisses the sheet.
                Defaults to ``True``.

        Returns:
            An :class:`OverlayHandle` for manual dismissal. A sheet shown from an
            intent stays open across a hot reload, and the handle follows it.

        Raises:
            TypeError: If the widget, or the one an intent resolves to, contains
                no :class:`SideSheet`.
        """
        widget = self._resolve(sheet)
        inner = _find_descendant(widget, SideSheet)
        if inner is None:
            raise TypeError("side_sheet() requires a SideSheet widget (possibly wrapped by modifiers)")

        cr = float(inner.style.corner_radius)
        # Round only the inner (away-from-edge) corners: (tl, tr, br, bl).
        radius = (cr, 0.0, 0.0, cr) if side == "right" else (0.0, cr, cr, 0.0)
        alignment = "top-right" if side == "right" else "top-left"

        handle = self.show(
            widget.modifier(corner_radius(radius)),
            backdrop=True,
            dismiss_on_outside_tap=bool(dismiss_on_outside_tap),
            position=OverlayPosition.aligned(alignment),
            transition=MaterialTransitions.side_sheet(side=side),
        )
        if not isinstance(sheet, Widget):
            replay = partial(MaterialOverlay.side_sheet, side=side, dismiss_on_outside_tap=dismiss_on_outside_tap)
            self._record_for_restore(handle, sheet, replay)
        return handle

    def bottom_sheet(
        self,
        sheet: Widget | Any,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal bottom sheet sliding up from the bottom edge.

        The :class:`BottomSheet` widget owns the background, size and corner radius.

        Args:
            sheet: A widget containing a :class:`BottomSheet`, possibly wrapped
                by modifiers, or an intent resolved by the overlay's intent
                resolver.
            dismiss_on_outside_tap: Whether tapping the scrim dismisses the sheet.
                Defaults to ``True``.

        Returns:
            An :class:`OverlayHandle` for manual dismissal. A sheet shown from an
            intent stays open across a hot reload, and the handle follows it.

        Raises:
            TypeError: If the widget, or the one an intent resolves to, contains
                no :class:`BottomSheet`.
        """
        widget = self._resolve(sheet)
        if _find_descendant(widget, BottomSheet) is None:
            raise TypeError("bottom_sheet() requires a BottomSheet widget (possibly wrapped by modifiers)")
        handle = self.show(
            widget,
            backdrop=True,
            dismiss_on_outside_tap=bool(dismiss_on_outside_tap),
            position=OverlayPosition.aligned("bottom-center"),
            transition=MaterialTransitions.bottom_sheet(),
        )
        if not isinstance(sheet, Widget):
            replay = partial(MaterialOverlay.bottom_sheet, dismiss_on_outside_tap=dismiss_on_outside_tap)
            self._record_for_restore(handle, sheet, replay)
        return handle


class MaterialOverlayProxy(OverlayProxy[MaterialOverlay]):
    """Forwards :class:`~nuiitivet.material.protocols.MaterialOverlayProtocol` to the overlay of one widget.

    A call after the widget is unmounted shows nothing.
    """

    def dialog(
        self,
        dialog: Widget | Any,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal dialog from a widget or an intent."""
        overlay = self._provider()
        if overlay is None:
            return disposed_handle()
        return overlay.dialog(dialog, dismiss_on_outside_tap=dismiss_on_outside_tap)

    def snackbar(
        self,
        message: str | Snackbar,
        *,
        duration: float = 3.0,
    ) -> OverlayHandle[None]:
        """Display a brief, non-blocking snackbar."""
        overlay = self._provider()
        if overlay is None:
            return disposed_handle()
        return overlay.snackbar(message, duration=duration)

    def loading(
        self,
        indicator: Widget | Any | None = None,
    ) -> OverlayHandle[Any]:
        """Show a loading indicator and return a handle for manual dismissal."""
        overlay = self._provider()
        if overlay is None:
            return disposed_handle()
        return overlay.loading(indicator)

    def while_loading(
        self,
        indicator: Widget | Any | None = None,
    ) -> WhileLoading:
        """Return a (sync or async) context manager that shows a loading indicator."""
        # The overlay is resolved when the block is entered.
        return WhileLoading(self, indicator)

    def side_sheet(
        self,
        sheet: Widget | Any,
        *,
        side: Literal["right", "left"] = "right",
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal side sheet from a widget or an intent."""
        overlay = self._provider()
        if overlay is None:
            return disposed_handle()
        return overlay.side_sheet(sheet, side=side, dismiss_on_outside_tap=dismiss_on_outside_tap)

    def bottom_sheet(
        self,
        sheet: Widget | Any,
        *,
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        """Display a modal bottom sheet from a widget or an intent."""
        overlay = self._provider()
        if overlay is None:
            return disposed_handle()
        return overlay.bottom_sheet(sheet, dismiss_on_outside_tap=dismiss_on_outside_tap)
