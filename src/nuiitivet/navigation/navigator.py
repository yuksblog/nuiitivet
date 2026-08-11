from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import inspect
import logging
from typing import Any, Callable, Literal, Mapping, TypeVar

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.callbacks import spawn_task
from nuiitivet.widgeting.context_lookup import find_app, find_provider, raise_if_premature_lookup
from nuiitivet.widgeting.widget import ComposableWidget, Widget

from .layer_composer import NavigationLayerComposer, NavigationLayerCompositionContext
from .route import Route
from .stack_runtime import RouteStackRuntime
from .transition_engine import TransitionEngine, TransitionHandle
from .transition_spec import EmptyTransitionSpec, TransitionPhase

_logger = logging.getLogger(__name__)

# Transition phase → spec attribute name. The exit definition is stored under
# ``exit_`` (``exit`` is a builtin), so a bare ``getattr(phase.value)`` would
# miss it and fall back to the engine default motion.
_TRANSITION_PHASE_ATTR: dict[TransitionPhase, str] = {
    TransitionPhase.ENTER: "enter",
    TransitionPhase.EXIT: "exit_",
}

# Lets ``of()`` keep the concrete subclass type, so that
# ``MaterialNavigator.of(...)`` is a ``MaterialNavigator`` and not a ``Navigator``.
NavigatorT = TypeVar("NavigatorT", bound="Navigator")


@dataclass(slots=True)
class _NavTransition:
    kind: Literal["push", "pop"]
    from_route: Route
    to_route: Route
    from_widget: Widget
    to_widget: Widget
    progress: float


@dataclass(slots=True)
class _PushDescriptor:
    """A restorable record of one declaratively pushed route (#378).

    Captures the intent *value* pushed via :meth:`Navigator.push` together with
    its type's fully-qualified name. The qualname — not the class identity — is
    what a hot reload matches against, because reloading redefines the intent
    class so the live ``type(intent)`` no longer equals the freshly registered
    route-table key (§8 of ``docs/design/HOT_RELOAD.md``).
    """

    intent: Any
    type_qualname: str


def _type_qualname(tp: type[Any]) -> str:
    """Fully-qualified name of ``tp`` (``module.QualName``), stable across reload."""
    return f"{tp.__module__}.{tp.__qualname__}"


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

    Initialization forms:
        - ``Navigator(screen)``: start with a single screen (``Route`` or ``Widget``).
        - ``Navigator.routes([...])``: pre-populated stack (e.g. deep linking).
        - ``Navigator.intents(initial_route=..., routes={...})``: Intent-based routing.

    Features:
        - push/pop
        - of(context) / of(context, root=True)
        - optional fade-in on push
    """

    def __init__(
        self,
        screen: Route | Widget | None = None,
        *,
        layer_composer: NavigationLayerComposer | None = None,
    ) -> None:
        """Initialize a Navigator with a single initial screen.

        Args:
            screen: The initial screen as a ``Route`` or ``Widget``. If ``None``,
                the navigator starts with an empty stack (use :meth:`routes` or
                :meth:`intents` factories for alternative initialization).
            layer_composer: Optional custom layer composer.
        """
        super().__init__()
        self._intent_routes: Mapping[type[Any], Callable[[Any], Route | Widget]] = {}
        self._transition: _NavTransition | None = None
        self._transition_handle: TransitionHandle | None = None
        self._transition_engine = TransitionEngine()
        self._pending_pop_requests: int = 0
        self._exiting_route: Route | None = None
        self._layer_composer: NavigationLayerComposer = layer_composer or _DefaultNavigationLayerComposer()
        # Ordered restore descriptors for routes added via ``push`` (not the
        # initial construction stack, which a hot reload rebuilds from the
        # factory). One entry per pushed route: a ``_PushDescriptor`` for a
        # declarative (intent) push, or ``None`` for an opaque, non-restorable
        # push (a raw ``Route``/``Widget`` instance). See :meth:`snapshot_stack`.
        self._restore_log: list[_PushDescriptor | None] = []

        initial_routes: list[Route] = []
        if screen is not None:
            initial_routes.append(self._to_initial_route(screen))
        self._stack = RouteStackRuntime(initial_routes=initial_routes)

    def _to_initial_route(self, value: Route | Widget) -> Route:
        """Convert a ``Route`` or ``Widget`` into a ``Route`` for initial stack construction."""
        if isinstance(value, Route):
            return value
        if isinstance(value, Widget):
            return self._route_from_widget(value)
        raise TypeError(f"Navigator initial screen must be a Route or Widget, got {type(value).__name__}")

    @classmethod
    def routes(
        cls,
        screens: Sequence[Route | Widget],
        *,
        layer_composer: NavigationLayerComposer | None = None,
    ) -> Navigator:
        """Create a Navigator with a pre-populated stack.

        Use this when the navigator should start with multiple screens already
        on the stack (e.g. deep linking, state restoration).

        Args:
            screens: Sequence of ``Route`` or ``Widget`` instances. The last item
                becomes the top of the stack.
            layer_composer: Optional custom layer composer.
        """
        if not screens:
            raise ValueError("Navigator.routes(...) requires at least one screen")
        instance = cls(layer_composer=layer_composer)
        initial_routes = [instance._to_initial_route(s) for s in screens]
        instance._stack = RouteStackRuntime(initial_routes=initial_routes)
        return instance

    @classmethod
    def intents(
        cls,
        *,
        initial_route: Any,
        routes: Mapping[type[Any], Callable[[Any], Route | Widget]],
        layer_composer: NavigationLayerComposer | None = None,
    ) -> Navigator:
        """Create a Navigator configured for Intent-based routing.

        Args:
            initial_route: The initial Intent instance used to resolve the first route.
            routes: Mapping of Intent types to route builder functions. Each
                builder returns a ``Route`` or ``Widget``.
            layer_composer: Optional custom layer composer.
        """
        instance = cls(layer_composer=layer_composer)
        instance._intent_routes = dict(routes)
        initial = instance._resolve_intent_to_route(initial_route)
        instance._stack = RouteStackRuntime(initial_routes=[initial])
        return instance

    @classmethod
    def of(cls: type[NavigatorT], context: Widget, root: bool = False) -> NavigatorT:
        """Return the ``Navigator`` that navigation from ``context`` should drive.

        The nearest ancestor wins, so a nested navigator keeps its own history.
        With no ancestor the answer is the App's own navigator, which makes this
        the single entry point for both the nested and the top-level case.

        Args:
            context: A widget in the subtree from which to resolve.
            root: Skip the ancestor search and return the App's navigator, to
                drive a whole-window transition from inside a nested navigator.

        Raises:
            RuntimeError: If called before ``context`` is mounted (typically from
                ``__init__``), or if no navigator can be resolved at all.
        """
        if not root:
            navigator = find_provider(context, cls)
            if navigator is not None:
                return navigator

        app = find_app(context)
        app_navigator = app._navigator if app is not None else None
        if app_navigator is None:
            raise_if_premature_lookup(f"{cls.__name__}.of", context)
            raise RuntimeError(
                f"No {cls.__name__} found for {context.__class__.__name__}: it has no "
                f"{cls.__name__} ancestor and is not attached to an App."
            )
        if not isinstance(app_navigator, cls):
            raise RuntimeError(
                f"The App's navigator is a {type(app_navigator).__name__}, not a {cls.__name__}. "
                f"Pass a {cls.__name__} as the App's content, or nest one in the subtree."
            )
        return app_navigator

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
        return Route(builder=lambda: widget)

    def _resolve_intent_to_route(self, intent: Any) -> Route:
        """Resolve an intent and normalize the result to a Route."""
        factory = self._intent_routes.get(type(intent))
        if factory is None:
            raise RuntimeError(f"No route is registered for intent: {type(intent).__name__}")
        resolved = factory(intent)
        if isinstance(resolved, Route):
            return resolved
        return self._route_from_widget(resolved)

    def _descriptor_for_push(self, route_or_widget_or_intent: Route | Widget | Any) -> _PushDescriptor | None:
        """Restore descriptor for a ``push`` input, or ``None`` if non-restorable.

        A ``Route``/``Widget`` instance is opaque — it was built from code that a
        reload replaces, with no factory to rebuild it against — so it is recorded
        as ``None``. An intent is declarative: it is captured by value plus its
        type's qualified name so the stack can be replayed after reload (#378).
        """
        if isinstance(route_or_widget_or_intent, (Route, Widget)):
            return None
        intent = route_or_widget_or_intent
        return _PushDescriptor(intent=intent, type_qualname=_type_qualname(type(intent)))

    def _resolve_descriptor_to_route(self, descriptor: _PushDescriptor) -> Route | None:
        """Rebuild a route from a restore descriptor against the current route table.

        Matches by the intent's qualified name rather than class identity so a
        descriptor captured before a reload resolves against the intent classes
        registered on the freshly built navigator. Returns ``None`` when no route
        is registered for that qualified name (route table changed under the
        stack), which the caller treats as a restore stopping point.
        """
        factory = None
        for intent_type, builder in self._intent_routes.items():
            if _type_qualname(intent_type) == descriptor.type_qualname:
                factory = builder
                break
        if factory is None:
            return None
        resolved = factory(descriptor.intent)
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

    def _on_transition_progress(self, value: float) -> None:
        # ``progress`` is a plain attribute, not a widget-bound observable, so
        # mutating it never requests a frame. Repaint every tween step so the
        # transition fades continuously instead of only at its endpoints.
        transition = self._transition
        if transition is None:
            return
        transition.progress = float(value)
        self.invalidate()

    def _get_motion(self, route: Route, phase: TransitionPhase) -> Any | None:
        # Phase → spec attribute. The exit definition lives under ``exit_``
        # (trailing underscore), so ``phase.value`` ("exit") would miss. Mirror
        # the mapping in ``material/transition_visual_spec.py``.
        attr = _TRANSITION_PHASE_ATTR.get(phase)
        if attr is None:
            return None
        try:
            definition = getattr(route.transition_spec, attr, None)
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
        self._restore_log.append(self._descriptor_for_push(route_or_widget_or_intent))

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
                apply=self._on_transition_progress,
                on_complete=self._finish_transition,
                motion=self._get_motion(route, TransitionPhase.ENTER),
            )
        else:
            self._transition = None

        self.mark_needs_layout()
        self.invalidate()

    def snapshot_stack(self) -> list[_PushDescriptor | None]:
        """Capture the restorable descriptors of routes pushed onto this navigator.

        Returns an ordered list, one entry per route added via :meth:`push`
        (bottom to top): a :class:`_PushDescriptor` for a declarative (intent)
        push, or ``None`` for an opaque, non-restorable push. Routes from the
        initial construction stack are excluded — a hot reload rebuilds those
        from the factory. Pair with :meth:`restore_stack` across a reload (#378).
        """
        return list(self._restore_log)

    def restore_stack(self, descriptors: Sequence[_PushDescriptor | None]) -> int:
        """Replay pushed routes from descriptors onto the freshly built navigator.

        Each restorable descriptor is resolved against the current route table
        (by intent qualified name) and pushed without animation, rebuilding the
        stack the author had before a reload. Replay stops at the first entry
        that cannot be restored — an opaque (``None``) push or an intent whose
        route is no longer registered — leaving the remainder collapsed, the
        documented degradation analogous to unmatched ``Observable`` paths.

        Args:
            descriptors: The list returned by :meth:`snapshot_stack` before the
                reload rebuilt the tree.

        Returns:
            The number of routes restored (pushed) onto the stack.
        """
        restored = 0
        for descriptor in descriptors:
            if descriptor is None:
                break
            route = self._resolve_descriptor_to_route(descriptor)
            if route is None:
                break
            self._restore_log.append(descriptor)
            self._stack.push(route)
            self._stack.mark_active(route)
            self._route_widget(route)
            restored += 1
        if restored:
            self.mark_needs_layout()
            self.invalidate()
        return restored

    def pop(self) -> None:
        """Request a back navigation. The pop itself runs as a task."""
        spawn_task(self.request_back(), owner_name=f"{type(self).__name__}.pop")

    async def request_back(self) -> bool:
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

        did_pop = await self._pop_once(skip_animation=False)
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

    async def _drain_pending_pops(self) -> None:
        while self._pending_pop_requests > 0 and self.can_pop():
            self._pending_pop_requests -= 1
            skip_animation = self._pending_pop_requests > 0
            did = await self._pop_once(skip_animation=skip_animation)
            if not did:
                self._pending_pop_requests = 0
                return

            # If we started an animated pop, wait for completion.
            if self._transition is not None and self._transition_handle is not None and self._transition.kind == "pop":
                return

        if not self.can_pop():
            self._pending_pop_requests = 0

    async def _pop_once(self, *, skip_animation: bool) -> bool:
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
                result = back_handler()
                if inspect.isawaitable(result):
                    result = await result
                if not bool(result):
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
                apply=self._on_transition_progress,
                on_complete=self._finish_pop,
                motion=self._get_motion(outgoing, TransitionPhase.EXIT),
            )
            self.mark_needs_layout()
            self.invalidate()
            return True

        self._stack.mark_exiting(outgoing)
        self._exiting_route = outgoing
        self._finish_pop_once()
        await self._drain_pending_pops()
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
        # Keep the restore log aligned with the committed stack. A pop can dip
        # below the pushed routes into the initial construction stack (which is
        # not logged); guard so those pops leave the empty log untouched.
        if self._restore_log:
            self._restore_log.pop()
        try:
            self.remove_child(widget)
        except Exception:
            exception_once(_logger, "navigator_remove_child_exc", "Failed to remove popped route widget")
        self.mark_needs_layout()
        self.invalidate()

    def _finish_pop(self) -> None:
        self._finish_pop_once()
        spawn_task(
            self._drain_pending_pops(),
            owner_name=f"{type(self).__name__}._drain_pending_pops",
        )

    def focus_traversal_children(self) -> list[Widget]:
        """Return only the top route, so Tab never reaches a covered one.

        Every route stays mounted — that is how a screen keeps its state while
        another one sits on top of it — and only the top one is painted. The Tab
        sequence has to stop at the same boundary.
        """
        routes = self._stack.routes
        if not routes:
            return []
        try:
            return [self._route_widget(routes[-1])]
        except Exception:
            exception_once(_logger, "navigator_focus_traversal_children_exc", "Top route widget build failed")
            return []

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
