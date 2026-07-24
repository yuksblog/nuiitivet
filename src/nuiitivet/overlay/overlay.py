"""Overlay widget for displaying transient layers."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, Optional, TypeVar

from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.container import Container
from nuiitivet.layout.alignment import normalize_alignment
from nuiitivet.modifiers.background import background
from nuiitivet.modifiers.clickable import clickable
from nuiitivet.observable import Observable
from nuiitivet.observable import runtime
from nuiitivet.navigation import Route
from nuiitivet.navigation.stack_runtime import RouteStackRuntime
from nuiitivet.navigation.transition_engine import TransitionEngine
from nuiitivet.navigation.transition_spec import EmptyTransitionSpec, TransitionPhase, TransitionSpec, Transitions
from nuiitivet.common.logging_once import exception_once
from .overlay_aware import OverlayAware
from .overlay_entry import OverlayEntry
from .overlay_handle import OverlayHandle
from .overlay_position import AnchoredOverlayPosition, OverlayPosition
from .result import OverlayDismissReason, OverlayResult
from .layer_composer import OverlayLayerComposer, OverlayLayerCompositionContext
from .transition_state import OverlayTransitionState

logger = logging.getLogger(__name__)

# Lets ``root()``/``of()`` keep the concrete subclass type, so that
# ``MaterialOverlay.root()`` is a ``MaterialOverlay`` and not an ``Overlay``.
OverlayT = TypeVar("OverlayT", bound="Overlay")


def _find_overlay_aware(widget: Widget) -> OverlayAware[Any] | None:
    """Walk the widget subtree to find the first OverlayAware widget.

    Wrappers added by modifiers (e.g. WillPopScope) sit above the user widget,
    so the search needs to descend into their children.
    """
    if isinstance(widget, OverlayAware):
        return widget
    for child in widget.children:
        if isinstance(child, Widget):
            found = _find_overlay_aware(child)
            if found is not None:
                return found
    return None


class _ModalNavigator(ComposableWidget):
    """Private navigator for overlay layers.

    This is intentionally separate from `navigation.Navigator`:
    - It can stack multiple routes as layers.
    - It avoids affecting the app's navigation stack.
    """

    def __init__(self, *, base_route: Route) -> None:
        super().__init__(width="100%", height="100%")
        self._base_route = base_route
        self._stack = RouteStackRuntime(initial_routes=[base_route], pinned_routes=[base_route])
        self._pending_dispose: dict[int, Callable[[], None]] = {}

    @property
    def _routes(self) -> list[Route]:
        return self._stack.routes

    def can_pop(self) -> bool:
        return self._stack.can_pop(min_routes=1)

    def push(self, route: _OverlayEntryRoute) -> None:
        self._stack.push(route)
        if self._should_animate_route(route):
            route.start_enter(
                on_update=lambda: self.invalidate(),
                on_complete=lambda: self._mark_active(route),
            )
        else:
            self._stack.mark_active(route)
        self.rebuild()

    def remove_route(self, route: _OverlayEntryRoute, *, on_disposed: Callable[[], None] | None = None) -> None:
        if route is self._base_route:
            return
        if route not in self._stack.routes:
            if on_disposed is not None:
                on_disposed()
            return
        if not self._stack.mark_exiting(route):
            if on_disposed is not None:
                on_disposed()
            return
        if on_disposed is not None:
            self._pending_dispose[id(route)] = on_disposed

        if self._should_animate_route(route):
            route.start_exit(
                on_update=lambda: self.invalidate(),
                on_complete=lambda: self._finalize_route_exit(route),
            )
            return

        self._finalize_route_exit(route)

    def _finalize_route_exit(self, route: _OverlayEntryRoute) -> None:
        try:
            self._stack.complete_exit(route)
        except Exception:
            exception_once(
                logger,
                f"overlay_modal_route_dispose_exc:{type(route).__name__}",
                "Overlay modal route dispose raised (route=%s)",
                type(route).__name__,
            )
        callback = self._pending_dispose.pop(id(route), None)
        if callback is not None:
            try:
                callback()
            except Exception:
                exception_once(
                    logger,
                    f"overlay_modal_route_on_disposed_exc:{type(route).__name__}",
                    "Overlay modal route on_disposed raised (route=%s)",
                    type(route).__name__,
                )
        self.rebuild()

    def pop(self) -> None:
        if not self.can_pop():
            return
        route = self._stack.begin_pop()
        if route is None:
            return
        if not isinstance(route, _OverlayEntryRoute):
            self._finalize_route_exit(self._coerce_route(route))
            return
        self.remove_route(route)

    def _coerce_route(self, route: Route) -> _OverlayEntryRoute:
        if isinstance(route, _OverlayEntryRoute):
            return route
        raise RuntimeError(f"Overlay modal runtime requires _OverlayEntryRoute, got: {type(route).__name__}")

    def _mark_active(self, route: Route) -> None:
        self._stack.mark_active(route)
        self.invalidate()

    def _should_animate_route(self, route: Route) -> bool:
        if isinstance(route.transition_spec, EmptyTransitionSpec):
            return False
        return getattr(self, "_app", None) is not None

    def build(self) -> Widget:
        if not self.can_pop():
            return Container()

        layers: list[Widget] = []
        for route in self._stack.routes[1:]:
            try:
                layers.append(route.build_widget())
            except Exception:
                exception_once(
                    logger,
                    f"overlay_modal_route_build_widget_exc:{type(route).__name__}",
                    "Overlay modal route build_widget raised (route=%s)",
                    type(route).__name__,
                )
                continue
        if not layers:
            return Container()
        return Stack(children=layers, alignment="center", width="100%", height="100%")

    # No hit_test override needed: the navigator and its transparent Stack/Container
    # wrapper both defer under the ``auto`` default, so input passes through
    # whenever no actual overlay layer is hit (issue #448).


class _OverlayEntryRoute(Route):
    """Route wrapper for OverlayEntry.

    OverlayEntry owns widget unmounting. This route must not unmount to avoid
    double-dispose when the entry is removed.
    """

    def __init__(
        self,
        entry: OverlayEntry,
        *,
        transition_spec: TransitionSpec | None = None,
        barrier_color: tuple[int, int, int, int] = (0, 0, 0, 128),
        barrier_dismissible: bool = True,
    ) -> None:
        super().__init__(builder=entry.build_widget, transition_spec=transition_spec or Transitions.empty())
        self.barrier_color = barrier_color
        self.barrier_dismissible = bool(barrier_dismissible)
        self.transition_state: OverlayTransitionState = OverlayTransitionState.create(self.transition_spec)
        self._transition_engine = TransitionEngine()
        self._content_widget: Widget | None = None
        # Whether input reaches the content behind this entry. Modeless entries
        # (toasts, banners) pass through; modal and light-dismiss entries do not,
        # and so occlude everything below them.
        self._passthrough: bool = True

    @property
    def transition_phase_obs(self) -> Observable[TransitionPhase]:
        return self.transition_state.phase_obs

    @property
    def transition_progress_obs(self) -> Observable[float]:
        return self.transition_state.progress_obs

    def start_enter(self, *, on_update: Callable[[], None], on_complete: Callable[[], None]) -> None:
        self.transition_phase_obs.value = TransitionPhase.ENTER
        self.transition_progress_obs.value = 0.0

        motion = self._get_motion(TransitionPhase.ENTER)

        self._transition_engine.start(
            start=0.0,
            target=1.0,
            apply=lambda v: self._apply_progress(v, on_update=on_update),
            on_complete=lambda: self._finish_enter(on_update=on_update, on_complete=on_complete),
            motion=motion,
        )

    def start_exit(self, *, on_update: Callable[[], None], on_complete: Callable[[], None]) -> None:
        self.transition_phase_obs.value = TransitionPhase.EXIT
        self.transition_progress_obs.value = 0.0

        motion = self._get_motion(TransitionPhase.EXIT)

        self._transition_engine.start(
            start=0.0,
            target=1.0,
            apply=lambda v: self._apply_progress(v, on_update=on_update),
            on_complete=on_complete,
            motion=motion,
        )

    def _get_motion(self, phase: TransitionPhase) -> Any | None:
        try:
            definition = getattr(self.transition_spec, phase.value, None)
            if definition is None:
                return None
            return getattr(definition, "motion", None)
        except Exception:
            return None

    def _apply_progress(self, value: float, *, on_update: Callable[[], None]) -> None:
        clamped = max(0.0, min(1.0, float(value)))
        self.transition_progress_obs.value = clamped
        on_update()

    def _finish_enter(self, *, on_update: Callable[[], None], on_complete: Callable[[], None]) -> None:
        self.transition_phase_obs.value = TransitionPhase.ACTIVE
        self.transition_progress_obs.value = 1.0
        on_update()
        on_complete()

    def dispose(self) -> None:
        self._transition_engine.dispose()
        self._widget = None


class _DefaultOverlayLayerComposer:
    """Fallback core composer with minimal, design-agnostic rendering."""

    def compose(self, context: OverlayLayerCompositionContext) -> Widget:
        positioned_content = context.position_content(context.content)

        if context.passthrough:
            return positioned_content

        barrier = Container(width="100%", height="100%").modifier(
            background(context.barrier_color)
            | clickable(on_click=context.on_barrier_click if context.barrier_dismissible else None)
        )
        return Stack(children=[barrier, positioned_content], alignment="top-left", width="100%", height="100%")


class Overlay(ComposableWidget):
    """Manages overlay entries displayed on top of content.

    The Overlay widget maintains a stack of OverlayEntry objects and renders them
    using a Stack widget. Entries are displayed in insertion order (newer on top).

    Example:
        # Create an overlay
        overlay = Overlay()

        # Show a dialog
        def build_dialog():
            return BasicDialog(...)

        entry = OverlayEntry(builder=build_dialog)
        overlay.insert_entry(entry)

        # Remove the dialog
        overlay.remove_entry(entry)
    """

    _root_overlay: Optional["Overlay"] = None  # Class variable for root overlay

    def __init__(self, *, layer_composer: OverlayLayerComposer | None = None) -> None:
        super().__init__(width="100%", height="100%")

        # Overlay entries are implemented as routes on a private modal navigator.
        # A base route keeps the navigator mounted even when empty.
        self._base_route: Route = Route(builder=lambda: Container(), transition_spec=Transitions.empty())
        self._modal_navigator: _ModalNavigator = _ModalNavigator(base_route=self._base_route)
        self._entry_to_route: Dict[OverlayEntry, _OverlayEntryRoute] = {}
        self._entry_to_future: Dict[OverlayEntry, asyncio.Future[OverlayResult[Any]]] = {}
        self._entry_to_pending_result: Dict[OverlayEntry, OverlayResult[Any]] = {}
        self._entry_to_timeout_cb: Dict[OverlayEntry, Callable[[float], None]] = {}
        self._layer_composer: OverlayLayerComposer = layer_composer or _DefaultOverlayLayerComposer()

    def _get_future_for_entry(self, entry: OverlayEntry) -> asyncio.Future[OverlayResult[Any]] | None:
        return self._entry_to_future.get(entry)

    def _get_pending_result_for_entry(self, entry: OverlayEntry) -> OverlayResult[Any] | None:
        return self._entry_to_pending_result.get(entry)

    def _pop_pending_result_for_entry(self, entry: OverlayEntry) -> OverlayResult[Any] | None:
        return self._entry_to_pending_result.pop(entry, None)

    def _future_for_entry(self, entry: OverlayEntry) -> asyncio.Future[OverlayResult[Any]]:
        existing = self._entry_to_future.get(entry)
        if existing is not None:
            return existing

        pending = self._pop_pending_result_for_entry(entry)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as exc:
            raise RuntimeError(
                "Async runtime is not running. "
                "Awaiting Overlay handles requires the framework async runtime to be active."
            ) from exc

        future: asyncio.Future[OverlayResult[Any]] = loop.create_future()
        self._entry_to_future[entry] = future

        if pending is not None and not future.done():
            try:
                future.set_result(pending)
            except Exception:
                exception_once(logger, "overlay_future_set_result_pending_exc", "Overlay future.set_result raised")

        return future

    def _cancel_timeout_if_any(self, entry: OverlayEntry) -> None:
        cb = self._entry_to_timeout_cb.pop(entry, None)
        if cb is None:
            return
        try:
            runtime.clock.unschedule(cb)
        except Exception:
            exception_once(logger, "overlay_timeout_unschedule_exc", "Overlay timeout unschedule raised")

    def _complete_entry_future(self, entry: OverlayEntry, result: OverlayResult[Any]) -> None:
        if entry in self._entry_to_pending_result:
            return

        future = self._entry_to_future.get(entry)
        if future is None:
            self._entry_to_pending_result[entry] = result
            self._cancel_timeout_if_any(entry)
            return
        if future.done():
            return
        try:
            future.set_result(result)
            self._cancel_timeout_if_any(entry)
        except Exception:
            exception_once(logger, "overlay_future_set_result_exc", "Overlay future.set_result raised")

    def _close_entry(self, entry: OverlayEntry, value: Any = None) -> None:
        self._complete_entry_future(entry, OverlayResult(value=value, reason=OverlayDismissReason.CLOSED))
        self.remove_entry(entry)

    def _entry_content_widget(self, entry: OverlayEntry) -> Widget | None:
        route = self._entry_to_route.get(entry)
        if route is None:
            return None
        return getattr(route, "_content_widget", None)

    def _top_entry(self) -> OverlayEntry | None:
        routes = getattr(self._modal_navigator, "_routes", None)
        if not isinstance(routes, list) or len(routes) <= 1:
            return None
        top = routes[-1]
        if top is self._base_route:
            return None
        for entry, route in reversed(list(self._entry_to_route.items())):
            if route is top:
                return entry
        return None

    def occluding_content_widget(self) -> Widget | None:
        """Return the content of the topmost entry that blocks input, if any.

        A modal or light-dismiss entry swallows interaction with everything below
        it; a modeless entry (toast, banner) passes input through. Callers that
        must know "can the user still act on the content behind the overlay"
        — keyboard-shortcut dispatch, for one — ask this. ``None`` means nothing
        is blocking and the content below is still reachable.
        """
        routes = getattr(self._modal_navigator, "_routes", None)
        if not isinstance(routes, list):
            return None
        for route in reversed(routes):
            if route is self._base_route:
                break
            if getattr(route, "_passthrough", True):
                continue
            return getattr(route, "_content_widget", None) or getattr(route, "_widget", None)
        return None

    async def _consult_will_pop(self, widget: Widget | None) -> bool:
        """Return True if dismiss should proceed; False if intercepted."""
        if widget is None:
            return True
        handler = getattr(widget, "handle_back_event", None)
        if not callable(handler):
            return True
        try:
            result = handler()
            if inspect.isawaitable(result):
                result = await result
            return bool(result)
        except Exception:
            exception_once(logger, "overlay_consult_will_pop_exc", "handle_back_event raised")
            return True

    def _will_pop_proceed_sync(self, widget: Widget | None) -> bool | None:
        """Try to evaluate will_pop synchronously.

        Returns True/False if determined synchronously, or None if the handler
        is async and must be awaited.
        """
        if widget is None:
            return True
        handler = getattr(widget, "handle_back_event", None)
        if not callable(handler):
            return True
        try:
            result = handler()
        except Exception:
            exception_once(logger, "overlay_consult_will_pop_sync_exc", "handle_back_event raised")
            return True
        if inspect.isawaitable(result):
            # Caller must re-invoke and await; close this throwaway coroutine
            # so Python does not emit a "never awaited" warning.
            close = getattr(result, "close", None)
            if callable(close):
                close()
            return None
        return bool(result)

    def request_close_topmost(self) -> None:
        """Request dismissal of the topmost entry through the will_pop pipeline."""
        entry = self._top_entry()
        if entry is None:
            return
        self._request_dismiss_entry(entry, value=None, reason=OverlayDismissReason.CLOSED)

    async def async_request_close_topmost(self) -> bool:
        """Async variant: returns True if a dismiss was handled (closed or intercepted)."""
        entry = self._top_entry()
        if entry is None:
            return False
        content = self._entry_content_widget(entry)
        if not await self._consult_will_pop(content):
            return True
        self._dismiss_entry(entry, reason=OverlayDismissReason.CLOSED)
        return True

    def _request_dismiss_entry(
        self,
        entry: OverlayEntry,
        *,
        value: Any = None,
        reason: OverlayDismissReason,
    ) -> None:
        """Dismiss an entry after consulting handle_back_event on its content widget.

        Sync path when the handler is synchronous; otherwise schedule an async task
        and fall back to immediate dismissal if no event loop is running.
        """
        content = self._entry_content_widget(entry)
        sync = self._will_pop_proceed_sync(content)
        if sync is True:
            self._dismiss_entry_with_value(entry, value=value, reason=reason)
            return
        if sync is False:
            return
        # Async handler: schedule resolution.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop; cannot await will_pop. Fall back to immediate dismiss.
            self._dismiss_entry_with_value(entry, value=value, reason=reason)
            return

        async def _go() -> None:
            if await self._consult_will_pop(content):
                self._dismiss_entry_with_value(entry, value=value, reason=reason)

        loop.create_task(_go())

    def _dismiss_entry_with_value(
        self,
        entry: OverlayEntry,
        *,
        value: Any,
        reason: OverlayDismissReason,
    ) -> None:
        self._complete_entry_future(entry, OverlayResult(value=value, reason=reason))
        self.remove_entry(entry)

    def _dismiss_entry(self, entry: OverlayEntry, *, reason: OverlayDismissReason) -> None:
        self._complete_entry_future(entry, OverlayResult(value=None, reason=reason))
        self.remove_entry(entry)

    def _normalize_to_route(self, content: Widget | Route) -> Route:
        """Normalize overlay content to a Route.

        This is the single boundary adapter for `show(...)` input polymorphism.
        Internal overlay runtime should operate on `Route` only.
        """
        if isinstance(content, Route):
            return content

        widget = content
        return Route(builder=lambda: widget, transition_spec=Transitions.empty())

    def _to_overlay_entry_route(
        self,
        *,
        entry: OverlayEntry,
        route: Route,
        barrier_color: tuple[int, int, int, int] = (0, 0, 0, 128),
        barrier_dismissible: bool = True,
    ) -> _OverlayEntryRoute:
        """Wrap a content route into the modal runtime route adapter."""
        resolved_barrier_color = getattr(route, "barrier_color", barrier_color)
        resolved_barrier_dismissible = getattr(route, "barrier_dismissible", barrier_dismissible)
        return _OverlayEntryRoute(
            entry,
            transition_spec=route.transition_spec,
            barrier_color=resolved_barrier_color,
            barrier_dismissible=bool(resolved_barrier_dismissible),
        )

    def show_modal(
        self,
        content: Widget | Route,
        *,
        dismiss_on_outside_tap: bool = False,
        barrier_color: tuple[int, int, int, int] = (0, 0, 0, 128),
        timeout: float | None = None,
        position: OverlayPosition | AnchoredOverlayPosition | None = None,
        transition_spec: TransitionSpec | None = None,
    ) -> OverlayHandle[Any]:
        """Show modal content as an overlay entry.

        Notes:
            - `await handle` returns an OverlayResult.
            - Awaiting requires a running async runtime.
        """
        return self._show_internal(
            content,
            passthrough=False,
            dismiss_on_outside_tap=dismiss_on_outside_tap,
            barrier_color=barrier_color,
            timeout=timeout,
            position=position,
            transition_spec=transition_spec,
            use_route_barrier=True,
        )

    def show_modeless(
        self,
        content: Widget | Route,
        *,
        timeout: float | None = None,
        position: OverlayPosition | AnchoredOverlayPosition | None = None,
        transition_spec: TransitionSpec | None = None,
    ) -> OverlayHandle[Any]:
        """Show modeless content as an overlay entry.

        Notes:
            - `await handle` returns an OverlayResult.
            - Awaiting requires a running async runtime.
        """
        return self._show_internal(
            content,
            passthrough=True,
            dismiss_on_outside_tap=False,
            barrier_color=(0, 0, 0, 0),
            timeout=timeout,
            position=position,
            transition_spec=transition_spec,
            use_route_barrier=False,
        )

    def show_light_dismiss(
        self,
        content: Widget | Route,
        *,
        timeout: float | None = None,
        position: OverlayPosition | AnchoredOverlayPosition | None = None,
        transition_spec: TransitionSpec | None = None,
    ) -> OverlayHandle[Any]:
        """Show content with light-dismiss behavior.

        Light-dismiss uses an invisible full-screen hit layer that closes the
        overlay when tapping outside the content. Outside taps are consumed.

        Notes:
            - `await handle` returns an OverlayResult.
            - Awaiting requires a running async runtime.
        """
        return self._show_internal(
            content,
            passthrough=False,
            dismiss_on_outside_tap=True,
            barrier_color=(0, 0, 0, 0),
            timeout=timeout,
            position=position,
            transition_spec=transition_spec,
            use_route_barrier=False,
        )

    def _show_internal(
        self,
        content: Widget | Route,
        *,
        passthrough: bool,
        dismiss_on_outside_tap: bool,
        barrier_color: tuple[int, int, int, int],
        timeout: float | None,
        position: OverlayPosition | AnchoredOverlayPosition | None,
        transition_spec: TransitionSpec | None,
        use_route_barrier: bool,
    ) -> OverlayHandle[Any]:
        if timeout is not None and float(timeout) < 0:
            raise ValueError("timeout must be >= 0 or None")

        entry: OverlayEntry

        content_route = self._normalize_to_route(content)

        if transition_spec is not None:
            match getattr(content_route, "transition_spec", None):
                case _:
                    content_route.transition_spec = transition_spec

        content_widget = content_route.build_widget()
        resolved_barrier_color = barrier_color
        barrier_dismissible = bool(dismiss_on_outside_tap)
        if use_route_barrier:
            resolved_barrier_color = getattr(content_route, "barrier_color", resolved_barrier_color)
            route_barrier_dismissible = getattr(content_route, "barrier_dismissible", None)
            if route_barrier_dismissible is not None and dismiss_on_outside_tap is False:
                barrier_dismissible = bool(route_barrier_dismissible)

        effective_position = position or OverlayPosition.alignment("center")

        def position_content(content: Widget) -> Widget:
            if isinstance(effective_position, AnchoredOverlayPosition):
                return effective_position.make_position_content(content)
            return _PositionedOverlayContent(
                content,
                alignment=effective_position.alignment_key,
                offset=effective_position.offset,
            )

        def on_dispose() -> None:
            self._complete_entry_future(entry, OverlayResult(value=None, reason=OverlayDismissReason.DISPOSED))
            try:
                content_route._widget = None  # type: ignore[attr-defined]
            except Exception:
                exception_once(
                    logger,
                    f"overlay_show_release_cached_widget_exc:{type(content_route).__name__}",
                    "Overlay show release cached widget raised (route=%s)",
                    type(content_route).__name__,
                )

        def build_layer(route: _OverlayEntryRoute) -> Widget:
            def on_barrier_click() -> None:
                if barrier_dismissible:
                    self._request_dismiss_entry(entry, reason=OverlayDismissReason.OUTSIDE_TAP)

            context = OverlayLayerCompositionContext(
                content=content_widget,
                transition_state=route.transition_state,
                passthrough=passthrough,
                barrier_color=resolved_barrier_color,
                barrier_dismissible=barrier_dismissible,
                on_barrier_click=on_barrier_click,
                position_content=position_content,
            )
            return self._layer_composer.compose(context)

        route_holder: dict[str, _OverlayEntryRoute] = {}
        layer_holder: dict[str, Widget] = {}

        def build_entry_widget() -> Widget:
            route = route_holder.get("route")
            if route is None:
                return Container()
            layer = layer_holder.get("layer")
            if layer is None:
                layer = build_layer(route)
                layer_holder["layer"] = layer
            return layer

        entry = OverlayEntry(builder=build_entry_widget, on_dispose=on_dispose)
        modal_route = self._to_overlay_entry_route(
            entry=entry,
            route=content_route,
            barrier_color=resolved_barrier_color,
            barrier_dismissible=barrier_dismissible,
        )
        route_holder["route"] = modal_route
        modal_route._content_widget = content_widget
        modal_route._passthrough = passthrough

        # Construct the handle first so OverlayAware widgets receive it
        # before the entry is inserted (i.e. before first build / mount).
        handle: OverlayHandle[Any] = OverlayHandle(overlay=self, entry=entry)
        aware = _find_overlay_aware(content_widget)
        if aware is not None:
            aware._set_overlay_handle(handle)

        self._insert_entry_with_route(entry, modal_route)

        self.rebuild()

        if timeout is not None:

            def on_timeout(_dt: float) -> None:
                self._dismiss_entry(entry, reason=OverlayDismissReason.TIMEOUT)

            self._entry_to_timeout_cb[entry] = on_timeout
            runtime.clock.schedule_once(on_timeout, float(timeout))

        return handle

    def hit_test(self, x: int, y: int):
        """Hit test that passes through if no entry is hit.

        With no entries the overlay is fully transparent and short-circuits.
        Otherwise it delegates to the composed subtree, which passes input
        through under the ``auto`` default whenever no overlay layer is hit.
        """
        if not self.has_entries():
            return None
        return super().hit_test(x, y)

    def build(self) -> Widget:
        return self._modal_navigator

    def insert_entry(self, entry: OverlayEntry) -> None:
        route = Route(builder=entry.build_widget, transition_spec=Transitions.empty())
        self._insert_entry_with_route(entry, route)
        self.rebuild()

    def _insert_entry_with_route(self, entry: OverlayEntry, route: Route) -> None:
        modal_route = (
            route if isinstance(route, _OverlayEntryRoute) else self._to_overlay_entry_route(entry=entry, route=route)
        )
        self._entry_to_route[entry] = modal_route
        self._modal_navigator.push(modal_route)

    def remove_entry(self, entry: OverlayEntry) -> None:
        route = self._entry_to_route.pop(entry, None)
        if route is None:
            return

        self._complete_entry_future(entry, OverlayResult(value=None, reason=OverlayDismissReason.DISPOSED))
        self._cancel_timeout_if_any(entry)

        future = self._entry_to_future.pop(entry, None)
        if future is not None and future.done() and entry not in self._entry_to_pending_result:
            try:
                self._entry_to_pending_result[entry] = future.result()
            except Exception:
                self._entry_to_pending_result[entry] = OverlayResult(value=None, reason=OverlayDismissReason.DISPOSED)

        self._remove_modal_route(route, on_disposed=entry.dispose)
        self.rebuild()

    def _remove_modal_route(self, route: _OverlayEntryRoute, *, on_disposed: Callable[[], None] | None = None) -> None:
        self._modal_navigator.remove_route(route, on_disposed=on_disposed)

    def has_entries(self) -> bool:
        try:
            return any(entry.is_visible for entry in self._entry_to_route)
        except Exception:
            exception_once(logger, "overlay_has_entries_exc", "Overlay.has_entries raised")
            return False

    def clear(self) -> None:
        for entry in list(self._entry_to_route.keys()):
            self.remove_entry(entry)
        self.invalidate()

    def close_topmost(self) -> None:
        self.request_close_topmost()

    def close(self, value: Any = None, target: Widget | Route | None = None) -> None:
        if target is not None:
            # 1. If target is a Route, look for exact match
            if isinstance(target, Route):
                for entry, route in list(self._entry_to_route.items()):
                    if route is target:
                        self._complete_entry_future(
                            entry, OverlayResult(value=value, reason=OverlayDismissReason.CLOSED)
                        )
                        self.remove_entry(entry)
                        return
                logger.warning("Overlay.close called with route target=%r, but it was not found.", target)
                return

            # 2. If target is a Widget, find the entry that contains it
            # Map route widgets to their entries for quick lookup
            route_widget_to_entry = {
                route._widget: entry
                for entry, route in self._entry_to_route.items()
                if getattr(route, "_widget", None) is not None
            }

            # Walk up the widget tree from target to find the owning route widget
            current: Widget | None = target  # type: ignore
            visited = set()

            while current is not None:
                if id(current) in visited:
                    break
                visited.add(id(current))

                if current in route_widget_to_entry:
                    entry = route_widget_to_entry[current]
                    self._complete_entry_future(entry, OverlayResult(value=value, reason=OverlayDismissReason.CLOSED))
                    self.remove_entry(entry)
                    return

                current = getattr(current, "parent", None)

            logger.warning(
                "Overlay.close called with widget target=%r, but no active overlay entry contains it.", target
            )
            return

        routes = getattr(self._modal_navigator, "_routes", None)
        if not isinstance(routes, list) or len(routes) <= 1:
            return

        top_route = routes[-1]
        if top_route is self._base_route:
            return

        for entry, route in reversed(list(self._entry_to_route.items())):
            if route is top_route:
                self._complete_entry_future(entry, OverlayResult(value=value, reason=OverlayDismissReason.CLOSED))
                self.remove_entry(entry)
                return

        try:
            self._modal_navigator.pop()
        except Exception:
            exception_once(logger, "overlay_close_fallback_pop_exc", "Overlay close fallback pop raised")

    @classmethod
    def set_root(cls, overlay: "Overlay") -> None:
        cls._root_overlay = overlay

    @classmethod
    def root(cls: type[OverlayT]) -> OverlayT:
        overlay = cls._root_overlay
        if overlay is None:
            raise RuntimeError(f"No root overlay found. Did you forget to initialize the App with an {cls.__name__}?")
        if not isinstance(overlay, cls):
            raise RuntimeError(f"Root overlay is not a {cls.__name__} instance")
        return overlay

    @classmethod
    def of(cls: type[OverlayT], context: Widget, root: bool = False) -> OverlayT:
        if root:
            return cls.root()

        overlay = context.find_ancestor(cls)
        if overlay is None:
            raise RuntimeError(
                f"No {cls.__name__} found in the widget tree above {context.__class__.__name__}. "
                f"Did you forget to wrap your widget in an {cls.__name__}?"
            )
        return overlay


class _PositionedOverlayContent(Widget):
    def __init__(self, child: Widget, *, alignment: str, offset: tuple[float, float]) -> None:
        super().__init__(width="100%", height="100%")
        self._child = child
        self._alignment = str(alignment)
        dx, dy = offset
        self._offset = (float(dx), float(dy))
        self.add_child(child)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> tuple[int, int]:
        # This widget expands; preferred size is irrelevant.
        return (0, 0)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)

        child = self._child
        cw, ch = child.preferred_size(max_width=width, max_height=height)
        target_w = int(cw)
        target_h = int(ch)

        # Flex is a weight, not a fraction of the parent. The overlay content is
        # the sole claimant on both axes, so a flex child fills the available
        # extent (see docs/design/SIZE_POLICY.md).
        if hasattr(child, "width_sizing") and child.width_sizing.kind == "flex":
            target_w = width
        if hasattr(child, "height_sizing") and child.height_sizing.kind == "flex":
            target_h = height

        ax, ay = normalize_alignment(self._alignment, default=("center", "center"))

        def get_pos(align: str, parent_size: int, child_size: int) -> int:
            if align == "center":
                return (parent_size - child_size) // 2
            if align == "end":
                return parent_size - child_size
            return 0

        dx, dy = self._offset
        x = int(get_pos(ax, width, target_w) + dx)
        y = int(get_pos(ay, height, target_h) + dy)

        child.layout(target_w, target_h)
        child.set_layout_rect(x, y, target_w, target_h)

    def paint(self, canvas, x: int, y: int, width: int, height: int):
        child = self._child
        rect = child.layout_rect
        if rect is None:
            return
        cx, cy, cw, ch = rect
        child.paint(canvas, int(x) + int(cx), int(y) + int(cy), int(cw), int(ch))

        setter = getattr(child, "set_last_rect", None)
        if callable(setter):
            setter(int(x) + int(cx), int(y) + int(cy), int(cw), int(ch))

    # No hit_test override needed: a transparent full-screen positioning wrapper
    # defers to its child under the ``auto`` default and never catches on self.
