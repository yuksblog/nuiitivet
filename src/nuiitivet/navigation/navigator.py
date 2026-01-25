from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import Any, Callable, ClassVar, Mapping

from nuiitivet.common.logging_once import exception_once
from nuiitivet.rendering.skia.color import make_opacity_paint
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.widget_animation import AnimationHandleLike

from .route import PageRoute, Route


_logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _NavTransition:
    kind: str  # "push" or "pop"
    from_widget: Widget
    to_widget: Widget
    progress: float
    duration_ms: int


class Navigator(ComposableWidget):
    """A minimal navigation stack.

    Phase 3 scope:
        - push/pop
        - root()/set_root()
        - of(context)
        - optional fade-in on push
    """

    _root: ClassVar[Navigator | None] = None

    def __init__(
        self,
        routes: Sequence[Route] | None = None,
        *,
        intent_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] | None = None,
    ) -> None:
        super().__init__()
        self._routes: list[Route] = list(routes or [])
        self._intent_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] = dict(intent_routes or {})
        self._transition: _NavTransition | None = None
        self._transition_handle: AnimationHandleLike | None = None
        self._pending_pop_requests: int = 0

    @classmethod
    def set_root(cls, navigator: Navigator) -> None:
        cls._root = navigator

    @classmethod
    def root(cls) -> Navigator:
        if cls._root is None:
            raise RuntimeError("Navigator root is not set")
        return cls._root

    @classmethod
    def of(cls, context: Widget) -> Navigator:
        navigator = context.find_ancestor(Navigator)
        if navigator is None:
            raise RuntimeError("Navigator not found in ancestors")
        return navigator

    def can_pop(self) -> bool:
        return len(self._routes) > 1

    def build(self) -> Widget:
        return self

    def _cancel_transition(self) -> None:
        handle = self._transition_handle
        self._transition_handle = None
        self._transition = None
        if handle is None:
            return
        cancel = getattr(handle, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                exception_once(
                    _logger,
                    "navigator_cancel_transition_exc",
                    "Failed to cancel transition animation handle",
                )

    def _top_route(self) -> Route | None:
        if not self._routes:
            return None
        return self._routes[-1]

    def _route_widget(self, route: Route) -> Widget:
        widget = route.build_widget()
        if widget not in self.children_snapshot():
            self.add_child(widget)
        return widget

    def _resolve_intent(self, intent: Any) -> Route | Widget:
        factory = self._intent_routes.get(type(intent))
        if factory is None:
            raise RuntimeError(f"No route is registered for intent: {type(intent).__name__}")
        return factory(intent)

    def _paint_with_opacity(self, canvas, widget: Widget, x: int, y: int, width: int, height: int, opacity: float):
        if canvas is None or opacity >= 1.0:
            widget.paint(canvas, x, y, width, height)
            return

        clamped = max(0.0, min(1.0, float(opacity)))
        layer_paint = make_opacity_paint(clamped)
        if layer_paint is None or not hasattr(canvas, "saveLayer"):
            widget.paint(canvas, x, y, width, height)
            return

        saved = False
        try:
            canvas.saveLayer(None, layer_paint)
            saved = True
            widget.paint(canvas, x, y, width, height)
        finally:
            if saved:
                try:
                    canvas.restore()
                except Exception:
                    exception_once(
                        _logger,
                        "navigator_canvas_restore_exc",
                        "Failed to restore canvas layer",
                    )

    def push(self, route_or_widget_or_intent: Route | Widget | Any) -> None:
        self._cancel_transition()

        previous_route = self._top_route()
        previous_widget = None if previous_route is None else self._route_widget(previous_route)

        if isinstance(route_or_widget_or_intent, Route):
            route = route_or_widget_or_intent
        elif isinstance(route_or_widget_or_intent, Widget):
            widget = route_or_widget_or_intent
            route = PageRoute(builder=lambda: widget)
        else:
            resolved = self._resolve_intent(route_or_widget_or_intent)
            if isinstance(resolved, Route):
                route = resolved
            else:
                widget = resolved
                route = PageRoute(builder=lambda: widget)

        self._routes.append(route)
        new_widget = self._route_widget(route)

        if previous_widget is not None and route.transition == "fade" and getattr(self, "_app", None) is not None:
            self._transition = _NavTransition(
                kind="push",
                from_widget=previous_widget,
                to_widget=new_widget,
                progress=0.0,
                duration_ms=600,
            )
            self._transition_handle = self.animate_value(
                start=0.0,
                target=1.0,
                duration=float(self._transition.duration_ms) / 1000.0,
                apply=lambda v: setattr(self._transition, "progress", float(v)) if self._transition else None,
                on_complete=self._finish_transition,
            )
        else:
            self._transition = None

        self.mark_needs_layout()
        self.invalidate()

    def pop(self) -> None:
        self.request_back()

    def request_back(self) -> bool:
        """Request a single back action.

        This API is designed for user back inputs (Esc/back button).
        If a pop transition is already running, the request is queued and the
        current transition is completed immediately.

        Queue consumption policy:
        - Intermediate queued pops are performed without animation.
        - The last queued pop (if any) uses the normal pop behavior.
        """

        if not self.can_pop():
            return False

        transition = self._transition
        handle = self._transition_handle

        if transition is not None and handle is not None and transition.kind == "pop":
            self._pending_pop_requests += 1
            self._force_finish_pop_transition()
            return True

        if transition is not None and handle is not None and transition.kind == "push":
            # Finish push quickly, then pop once.
            self._force_finish_push_transition()

        did_pop = self._pop_once(skip_animation=False)
        if not did_pop:
            # will_pop canceled; treat as handled.
            return True
        return True

    def _force_finish_push_transition(self) -> None:
        transition = self._transition
        handle = self._transition_handle
        if transition is None or handle is None or transition.kind != "push":
            return
        try:
            transition.progress = 1.0
        except Exception:
            exception_once(_logger, "navigator_force_finish_push_set_progress_exc", "Failed to set push progress")
        cancel = getattr(handle, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                exception_once(_logger, "navigator_force_finish_push_cancel_exc", "Failed to cancel push transition")
        self._finish_transition()

    def _force_finish_pop_transition(self) -> None:
        transition = self._transition
        handle = self._transition_handle
        if transition is None or handle is None or transition.kind != "pop":
            return
        try:
            transition.progress = 0.0
        except Exception:
            exception_once(_logger, "navigator_force_finish_pop_set_progress_exc", "Failed to set pop progress")
        cancel = getattr(handle, "cancel", None)
        if callable(cancel):
            try:
                cancel()
            except Exception:
                exception_once(_logger, "navigator_force_finish_pop_cancel_exc", "Failed to cancel pop transition")
        self._finish_pop()

    def _drain_pending_pops(self) -> None:
        while self._pending_pop_requests > 0 and self.can_pop():
            self._pending_pop_requests -= 1
            skip_animation = self._pending_pop_requests > 0
            did = self._pop_once(skip_animation=skip_animation)
            if not did:
                self._pending_pop_requests = 0
                return

            # If we started an animated pop, wait for completion.
            if self._transition is not None and self._transition_handle is not None and self._transition.kind == "pop":
                return

        if not self.can_pop():
            self._pending_pop_requests = 0

    def _pop_once(self, *, skip_animation: bool) -> bool:
        if not self.can_pop():
            return False

        self._cancel_transition()

        outgoing = self._routes[-1]
        incoming = self._routes[-2]
        outgoing_widget = self._route_widget(outgoing)
        incoming_widget = self._route_widget(incoming)

        back_handler = getattr(outgoing_widget, "handle_back_event", None)
        if callable(back_handler):
            try:
                if not bool(back_handler()):
                    self._pending_pop_requests = 0
                    return False
            except Exception:
                # Fail open to avoid trapping navigation.
                exception_once(_logger, "navigator_back_handler_exc", "Route handle_back_event raised")

        app = getattr(self, "_app", None)
        if not skip_animation and outgoing.transition == "fade" and app is not None:
            self._transition = _NavTransition(
                kind="pop",
                from_widget=outgoing_widget,
                to_widget=incoming_widget,
                progress=1.0,
                duration_ms=600,
            )
            self._transition_handle = self.animate_value(
                start=1.0,
                target=0.0,
                duration=float(self._transition.duration_ms) / 1000.0,
                apply=lambda v: setattr(self._transition, "progress", float(v)) if self._transition else None,
                on_complete=self._finish_pop,
            )
            self.mark_needs_layout()
            self.invalidate()
            return True

        self._finish_pop_once()
        self._drain_pending_pops()
        return True

    def _finish_transition(self) -> None:
        self._transition_handle = None
        self._transition = None
        self.invalidate()

    def _finish_pop_once(self) -> None:
        self._transition_handle = None
        self._transition = None
        if not self.can_pop():
            self.invalidate()
            return

        route = self._routes.pop()
        widget = route.build_widget()
        route.dispose()
        try:
            self.remove_child(widget)
        except Exception:
            exception_once(_logger, "navigator_remove_child_exc", "Failed to remove popped route widget")
        self.mark_needs_layout()
        self.invalidate()

    def _finish_pop(self) -> None:
        self._finish_pop_once()
        self._drain_pending_pops()

    def layout(self, width: int, height: int) -> None:
        self.clear_needs_layout()
        self.set_layout_rect(0, 0, width, height)

        # Layout all cached route widgets so hit_test coordinate translation works.
        for route in self._routes:
            widget = route.build_widget() if route._widget is not None else None
            if widget is None:
                continue
            try:
                widget.layout(width, height)
                widget.set_layout_rect(0, 0, width, height)
            except Exception:
                exception_once(_logger, "navigator_layout_route_widget_exc", "Route widget layout failed")

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)

        if not self._routes:
            return

        transition = self._transition
        if transition is None:
            top_widget = self._route_widget(self._routes[-1])
            top_widget.paint(canvas, x, y, width, height)
            return

        if transition.kind == "push":
            # Cross-fade: fade out old while fading in new.
            self._paint_with_opacity(
                canvas,
                transition.from_widget,
                x,
                y,
                width,
                height,
                opacity=1.0 - transition.progress,
            )
            self._paint_with_opacity(
                canvas,
                transition.to_widget,
                x,
                y,
                width,
                height,
                opacity=transition.progress,
            )
            return

        if transition.kind == "pop":
            # Cross-fade: fade out outgoing while fading in incoming.
            self._paint_with_opacity(
                canvas,
                transition.to_widget,
                x,
                y,
                width,
                height,
                opacity=1.0 - transition.progress,
            )
            self._paint_with_opacity(
                canvas,
                transition.from_widget,
                x,
                y,
                width,
                height,
                opacity=transition.progress,
            )
            return

        # Unknown transition kind: paint top.
        top_widget = self._route_widget(self._routes[-1])
        top_widget.paint(canvas, x, y, width, height)

    def hit_test(self, x: int, y: int):
        transition = self._transition
        if transition is None:
            if not self._routes:
                return None
            return self._route_widget(self._routes[-1]).hit_test(x, y)

        # During transitions, prefer the visually top-most widget.
        if transition.kind == "push":
            hit = transition.to_widget.hit_test(x, y)
            if hit:
                return hit
            return transition.from_widget.hit_test(x, y)

        if transition.kind == "pop":
            hit = transition.from_widget.hit_test(x, y)
            if hit:
                return hit
            return transition.to_widget.hit_test(x, y)

        return super().hit_test(x, y)
