from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import Any, Callable, ClassVar, Literal, Mapping

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.widget_animation import AnimationHandleLike

from .layer_composer import NavigationLayerComposer, NavigationLayerCompositionContext
from .route import PageRoute, Route
from .stack_runtime import RouteStackRuntime
from .transition_engine import TransitionEngine
from .transition_spec import EmptyTransitionSpec, TransitionPhase


_logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _NavTransition:
    kind: Literal["push", "pop"]
    from_route: Route
    to_route: Route
    from_widget: Widget
    to_widget: Widget
    progress: float


class _DefaultNavigationLayerComposer:
    """Fallback core composer with minimal, design-agnostic rendering."""

    def paint_static(self, *, canvas, widget: Widget, x: int, y: int, width: int, height: int) -> None:
        widget.paint(canvas, x, y, width, height)

    def paint_transition(self, context: NavigationLayerCompositionContext) -> None:
        if context.kind == "push":
            context.from_widget.paint(context.canvas, context.x, context.y, context.width, context.height)
            context.to_widget.paint(context.canvas, context.x, context.y, context.width, context.height)
            return

        if context.kind == "pop":
            context.to_widget.paint(context.canvas, context.x, context.y, context.width, context.height)
            context.from_widget.paint(context.canvas, context.x, context.y, context.width, context.height)
            return

        context.to_widget.paint(context.canvas, context.x, context.y, context.width, context.height)


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
        layer_composer: NavigationLayerComposer | None = None,
    ) -> None:
        super().__init__()
        self._stack = RouteStackRuntime(initial_routes=list(routes or []))
        self._intent_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] = dict(intent_routes or {})
        self._transition: _NavTransition | None = None
        self._transition_handle: AnimationHandleLike | None = None
        self._transition_engine = TransitionEngine()
        self._pending_pop_requests: int = 0
        self._exiting_route: Route | None = None
        self._layer_composer: NavigationLayerComposer = layer_composer or _DefaultNavigationLayerComposer()

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
        return self._stack.can_pop(min_routes=1)

    def build(self) -> Widget:
        return self

    def _cancel_transition(self) -> None:
        handle = self._transition_handle
        self._transition_handle = None
        self._transition = None
        exiting = self._exiting_route
        self._exiting_route = None
        if exiting is not None:
            self._stack.mark_active(exiting)
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
        return self._stack.top()

    def _route_widget(self, route: Route) -> Widget:
        widget = route.build_widget()
        if widget not in self.children_snapshot():
            self.add_child(widget)
        return widget

    def _route_from_widget(self, widget: Widget) -> Route:
        """Wrap a widget into a page route for navigator runtime."""
        return PageRoute(builder=lambda: widget)

    def _resolve_intent_to_route(self, intent: Any) -> Route:
        """Resolve an intent and normalize the result to a Route."""
        factory = self._intent_routes.get(type(intent))
        if factory is None:
            raise RuntimeError(f"No route is registered for intent: {type(intent).__name__}")
        resolved = factory(intent)
        if isinstance(resolved, Route):
            return resolved
        return self._route_from_widget(resolved)

    def _normalize_to_route(self, route_or_widget_or_intent: Route | Widget | Any) -> Route:
        """Normalize external push input to a Route.

        This is the single boundary adapter for `push(...)` input polymorphism.
        Internal navigator runtime must only operate on `Route`.
        """
        if isinstance(route_or_widget_or_intent, Route):
            return route_or_widget_or_intent

        if isinstance(route_or_widget_or_intent, Widget):
            return self._route_from_widget(route_or_widget_or_intent)

        return self._resolve_intent_to_route(route_or_widget_or_intent)

    def _is_animated_transition(self, route: Route) -> bool:
        return not isinstance(route.transition_spec, EmptyTransitionSpec)

    def _get_motion(self, route: Route, phase: TransitionPhase) -> Any | None:
        try:
            definition = getattr(route.transition_spec, phase.value, None)
            if definition is None:
                return None
            return getattr(definition, "motion", None)
        except Exception:
            return None

    def push(self, route_or_widget_or_intent: Route | Widget | Any) -> None:
        self._cancel_transition()

        previous_route = self._top_route()
        previous_widget = None if previous_route is None else self._route_widget(previous_route)

        route = self._normalize_to_route(route_or_widget_or_intent)

        self._stack.push(route)
        self._stack.mark_active(route)
        new_widget = self._route_widget(route)

        if (
            previous_widget is not None
            and self._is_animated_transition(route)
            and getattr(self, "_app", None) is not None
        ):
            assert previous_route is not None
            self._transition = _NavTransition(
                kind="push",
                from_route=previous_route,
                to_route=route,
                from_widget=previous_widget,
                to_widget=new_widget,
                progress=0.0,
            )
            self._transition_handle = self._transition_engine.start(
                start=0.0,
                target=1.0,
                apply=lambda v: setattr(self._transition, "progress", float(v)) if self._transition else None,
                on_complete=self._finish_transition,
                motion=self._get_motion(route, TransitionPhase.ENTER),
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

        routes = self._stack.routes
        outgoing = routes[-1]
        incoming = routes[-2]
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
        if not skip_animation and self._is_animated_transition(outgoing) and app is not None:
            self._stack.mark_exiting(outgoing)
            self._exiting_route = outgoing
            self._transition = _NavTransition(
                kind="pop",
                from_route=outgoing,
                to_route=incoming,
                from_widget=outgoing_widget,
                to_widget=incoming_widget,
                progress=1.0,
            )
            self._transition_handle = self._transition_engine.start(
                start=1.0,
                target=0.0,
                apply=lambda v: setattr(self._transition, "progress", float(v)) if self._transition else None,
                on_complete=self._finish_pop,
                motion=self._get_motion(outgoing, TransitionPhase.EXIT),
            )
            self.mark_needs_layout()
            self.invalidate()
            return True

        self._stack.mark_exiting(outgoing)
        self._exiting_route = outgoing
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
        route = self._exiting_route
        self._exiting_route = None
        if route is None:
            route = self._stack.begin_pop()

        if route is None:
            self.invalidate()
            return

        widget = route.build_widget()
        self._stack.complete_exit(route)
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
        for route in self._stack.routes:
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

        routes = self._stack.routes
        if not routes:
            return

        transition = self._transition
        if transition is None:
            top_widget = self._route_widget(routes[-1])
            self._layer_composer.paint_static(canvas=canvas, widget=top_widget, x=x, y=y, width=width, height=height)
            return

        if transition.kind in ("push", "pop"):
            phase_progress = _transition_phase_progress(transition)
            if phase_progress is not None:
                from_phase, to_phase, p = phase_progress
                context = NavigationLayerCompositionContext(
                    canvas=canvas,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    kind=transition.kind,
                    from_widget=transition.from_widget,
                    to_widget=transition.to_widget,
                    from_phase=from_phase,
                    to_phase=to_phase,
                    progress=p,
                    from_transition_spec=transition.from_route.transition_spec,
                    to_transition_spec=transition.to_route.transition_spec,
                )
                self._layer_composer.paint_transition(context)
                return

        # Unknown transition kind: paint top.
        top_widget = self._route_widget(routes[-1])
        self._layer_composer.paint_static(canvas=canvas, widget=top_widget, x=x, y=y, width=width, height=height)

    def hit_test(self, x: int, y: int):
        transition = self._transition
        if transition is None:
            routes = self._stack.routes
            if not routes:
                return None
            return self._route_widget(routes[-1]).hit_test(x, y)

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

    def on_unmount(self) -> None:
        self._transition_engine.dispose()
        super().on_unmount()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _transition_phase_progress(transition: _NavTransition) -> tuple[TransitionPhase, TransitionPhase, float] | None:
    if transition.kind == "push":
        p = _clamp01(transition.progress)
        return (TransitionPhase.EXIT, TransitionPhase.ENTER, p)
    if transition.kind == "pop":
        p = _clamp01(1.0 - transition.progress)
        return (TransitionPhase.EXIT, TransitionPhase.ENTER, p)
    return None
