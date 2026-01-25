"""Overlay widget for displaying transient layers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.container import Container
from nuiitivet.layout.alignment import normalize_alignment
from nuiitivet.modifiers.background import background
from nuiitivet.modifiers.clickable import clickable
from nuiitivet.observable import runtime
from nuiitivet.navigation import PageRoute, Route
from nuiitivet.common.logging_once import exception_once
from .overlay_entry import OverlayEntry
from .overlay_handle import OverlayHandle
from .overlay_position import OverlayPosition
from .result import OverlayDismissReason, OverlayResult


logger = logging.getLogger(__name__)


class _ModalNavigator(ComposableWidget):
    """Private navigator for overlay layers.

    This is intentionally separate from `navigation.Navigator`:
    - It can stack multiple routes as layers.
    - It avoids affecting the app's navigation stack.
    """

    def __init__(self, *, base_route: Route) -> None:
        super().__init__(width="100%", height="100%")
        self._base_route = base_route
        self._routes: list[Route] = [base_route]

    def can_pop(self) -> bool:
        return len(self._routes) > 1

    def push(self, route: Route) -> None:
        self._routes.append(route)
        self.rebuild()

    def remove_route(self, route: Route) -> None:
        if route is self._base_route:
            return
        if route not in self._routes:
            return
        self._routes.remove(route)
        try:
            route.dispose()
        except Exception:
            exception_once(
                logger,
                f"overlay_modal_route_dispose_exc:{type(route).__name__}",
                "Overlay modal route dispose raised (route=%s)",
                type(route).__name__,
            )
        self.rebuild()

    def pop(self) -> None:
        if not self.can_pop():
            return
        route = self._routes[-1]
        self.remove_route(route)

    def build(self) -> Widget:
        if not self.can_pop():
            return Container()

        layers: list[Widget] = []
        for route in self._routes[1:]:
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

    def hit_test(self, x: int, y: int):
        """Hit test that passes through if no overlay layer is hit."""
        hit = super().hit_test(x, y)
        if hit is self:
            return None
        if self.built_child and hit is self.built_child:
            return None
        return hit


class _OverlayEntryRoute(Route):
    """Route wrapper for OverlayEntry.

    OverlayEntry owns widget unmounting. This route must not unmount to avoid
    double-dispose when the entry is removed.
    """

    def __init__(self, entry: OverlayEntry, *, transition: str = "none") -> None:
        super().__init__(builder=entry.build_widget, transition=transition)

    def dispose(self) -> None:
        self._widget = None


class Overlay(ComposableWidget):
    """Manages overlay entries displayed on top of content.

    The Overlay widget maintains a stack of OverlayEntry objects and renders them
    using a Stack widget. Entries are displayed in insertion order (newer on top).

    Example:
        # Create an overlay
        overlay = Overlay()

        # Show a dialog
        def build_dialog():
            return AlertDialog(...)

        entry = OverlayEntry(builder=build_dialog)
        overlay.insert_entry(entry)

        # Remove the dialog
        overlay.remove_entry(entry)
    """

    _root_overlay: Optional["Overlay"] = None  # Class variable for root overlay

    def __init__(self) -> None:
        super().__init__(width="100%", height="100%")

        # Overlay entries are implemented as routes on a private modal navigator.
        # A base route keeps the navigator mounted even when empty.
        self._base_route: Route = PageRoute(builder=lambda: Container(), transition="none")
        self._modal_navigator: _ModalNavigator = _ModalNavigator(base_route=self._base_route)
        self._entry_to_route: Dict[OverlayEntry, Route] = {}
        self._entry_to_future: Dict[OverlayEntry, asyncio.Future[OverlayResult[Any]]] = {}
        self._entry_to_pending_result: Dict[OverlayEntry, OverlayResult[Any]] = {}
        self._entry_to_timeout_cb: Dict[OverlayEntry, Callable[[float], None]] = {}

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

    def _dismiss_entry(self, entry: OverlayEntry, *, reason: OverlayDismissReason) -> None:
        self._complete_entry_future(entry, OverlayResult(value=None, reason=reason))
        self.remove_entry(entry)

    def show(
        self,
        content: Widget | Route,
        *,
        passthrough: bool = False,
        dismiss_on_outside_tap: bool = False,
        timeout: float | None = None,
        position: OverlayPosition | None = None,
    ) -> OverlayHandle[Any]:
        """Show a widget or route as an overlay entry.

        Notes:
            - `await handle` returns an OverlayResult.
            - Awaiting requires a running async runtime.
        """
        if passthrough and dismiss_on_outside_tap:
            raise ValueError("passthrough=True with dismiss_on_outside_tap=True is not supported")
        if timeout is not None and float(timeout) < 0:
            raise ValueError("timeout must be >= 0 or None")

        entry: OverlayEntry

        content_route: Route | None = None
        content_widget: Widget
        transition: str = "none"

        if isinstance(content, Route):
            content_route = content
            transition = getattr(content, "transition", "none")
            content_widget = content.build_widget()
        else:
            content_widget = content

        effective_position = position or OverlayPosition.alignment("center")
        positioned = _PositionedOverlayContent(
            content_widget,
            alignment=effective_position.alignment_key,
            offset=effective_position.offset,
        )

        def on_dispose() -> None:
            self._complete_entry_future(entry, OverlayResult(value=None, reason=OverlayDismissReason.DISPOSED))

            if content_route is not None:
                try:
                    content_route._widget = None  # type: ignore[attr-defined]
                except Exception:
                    exception_once(
                        logger,
                        f"overlay_show_release_cached_widget_exc:{type(content_route).__name__}",
                        "Overlay show release cached widget raised (route=%s)",
                        type(content_route).__name__,
                    )

        def build_layer() -> Widget:
            if passthrough:
                return positioned

            scrim_color = (0, 0, 0, 128)

            def on_barrier_click() -> None:
                if dismiss_on_outside_tap:
                    self._dismiss_entry(entry, reason=OverlayDismissReason.OUTSIDE_TAP)

            barrier = Container(width="100%", height="100%").modifier(
                background(scrim_color) | clickable(on_click=on_barrier_click if dismiss_on_outside_tap else None)
            )
            return Stack(children=[barrier, positioned], alignment="top-left", width="100%", height="100%")

        entry = OverlayEntry(builder=build_layer, on_dispose=on_dispose)
        modal_route = _OverlayEntryRoute(entry, transition=transition)
        self._insert_entry_with_route(entry, modal_route)
        self.rebuild()

        if timeout is not None:

            def on_timeout(_dt: float) -> None:
                self._dismiss_entry(entry, reason=OverlayDismissReason.TIMEOUT)

            self._entry_to_timeout_cb[entry] = on_timeout
            runtime.clock.schedule_once(on_timeout, float(timeout))

        return OverlayHandle(overlay=self, entry=entry)

    def hit_test(self, x: int, y: int):
        """Hit test that passes through if no entry is hit."""
        if not self.has_entries():
            return None

        hit = super().hit_test(x, y)
        if hit is self:
            return None
        if self.built_child and hit is self.built_child:
            return None
        return hit

    def build(self) -> Widget:
        return self._modal_navigator

    def insert_entry(self, entry: OverlayEntry) -> None:
        route = PageRoute(builder=entry.build_widget, transition="none")
        self._insert_entry_with_route(entry, route)
        self.rebuild()

    def _insert_entry_with_route(self, entry: OverlayEntry, route: Route) -> None:
        self._entry_to_route[entry] = route
        self._modal_navigator.push(route)

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

        self._remove_modal_route(route)
        entry.dispose()
        self.rebuild()

    def _remove_modal_route(self, route: Route) -> None:
        self._modal_navigator.remove_route(route)

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
        self.close(None)

    def close(self, value: Any = None) -> None:
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
    def root(cls) -> "Overlay":
        if cls._root_overlay is None:
            raise RuntimeError("No root overlay found. Did you forget to initialize the App with an Overlay?")
        return cls._root_overlay

    @classmethod
    def of(cls, context: Widget, root: bool = False) -> "Overlay":
        if root:
            return cls.root()

        overlay = context.find_ancestor(Overlay)
        if overlay is None:
            raise RuntimeError(
                f"No Overlay found in the widget tree above {context.__class__.__name__}. "
                "Did you forget to wrap your widget in an Overlay?"
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

        if hasattr(child, "width_sizing") and child.width_sizing.kind == "flex":
            target_w = int(width * (child.width_sizing.value / 100.0))
        if hasattr(child, "height_sizing") and child.height_sizing.kind == "flex":
            target_h = int(height * (child.height_sizing.value / 100.0))

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

    def hit_test(self, x: int, y: int):
        hit = super().hit_test(x, y)
        if hit is self:
            return None
        return hit
