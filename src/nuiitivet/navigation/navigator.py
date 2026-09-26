from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import inspect
import logging
from typing import Any, Callable, Literal, Mapping, Tuple, TypeVar, Union

from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.callbacks import spawn_task
from nuiitivet.widgeting.context_lookup import find_provider, find_window, raise_if_premature_lookup
from nuiitivet.widgeting.widget import ComposableWidget, Widget

from nuiitivet.transition.engine import TransitionEngine, TransitionHandle
from nuiitivet.transition.spec import (
    EmptyTransitionSpec,
    TransitionPhase,
    TransitionSpec,
    Transitions,
    resolve_phase_motion,
)
from nuiitivet.transition.stack import StackRuntime

from .layer_composer import NavigationLayerComposer, NavigationLayerCompositionContext
from .route import Route

_logger = logging.getLogger(__name__)

# Keeps ``MaterialNavigator.of(...)`` typed as ``MaterialNavigator``.
NavigatorT = TypeVar("NavigatorT", bound="Navigator")

# A screen, optionally with the transition it moves with.
ScreenLike = Union[Widget, Tuple[Widget, TransitionSpec]]


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
    """An intent pushed onto the stack, kept so a hot reload can replay it.

    A reload redefines the intent class, so the replay matches by qualified
    name, not by class identity.
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
    """A stack of screens; the top one is shown.

    Each screen moves with its own transition, given when it enters the stack.

    From a list of screens: :meth:`routes`. From intents and a routing table:
    :meth:`intents`.
    """

    def __init__(
        self,
        screen: Widget | None = None,
        *,
        transition: TransitionSpec | None = None,
        layer_composer: NavigationLayerComposer | None = None,
        key: str | None = None,
    ) -> None:
        """Initialize a Navigator with a single initial screen.

        Args:
            screen: The initial screen. ``None`` starts with an empty stack.
            transition: The transition ``screen`` moves with. Defaults to none.
            layer_composer: Optional custom layer composer.
            key: Stable widget identity for dev-bridge targeting and hot reload.
        """
        super().__init__(key=key)
        self._intent_routes: Mapping[type[Any], Callable[[Any], ScreenLike]] = {}
        self._transition: _NavTransition | None = None
        self._transition_handle: TransitionHandle | None = None
        self._transition_engine = TransitionEngine()
        self._pending_pop_requests: int = 0
        # Counted synchronously in ``pop()``; ``_pending_pop_requests`` stays 0 until the task runs.
        self._back_requests_in_flight: int = 0
        self._exiting_route: Route | None = None
        self._layer_composer: NavigationLayerComposer = layer_composer or _DefaultNavigationLayerComposer()
        # One entry per ``push``: a descriptor for an intent, ``None`` for a widget.
        self._restore_log: list[_PushDescriptor | None] = []

        initial_routes: list[Route] = []
        if screen is not None:
            initial_routes.append(self._to_route(screen, transition))
        self._stack: StackRuntime[Route] = StackRuntime(initial=initial_routes)

    @classmethod
    def routes(
        cls,
        screens: Sequence[ScreenLike],
        *,
        layer_composer: NavigationLayerComposer | None = None,
    ) -> Navigator:
        """Create a Navigator that starts with several screens on its stack.

        Use this for deep linking or restoring state.

        Args:
            screens: Screens bottom to top; the last one is shown. Each is a
                widget or a ``(widget, transition)`` pair.
            layer_composer: Optional custom layer composer.
        """
        if not screens:
            raise ValueError("Navigator.routes(...) requires at least one screen")
        instance = cls(layer_composer=layer_composer)
        instance._stack = StackRuntime(initial=[instance._to_route(s) for s in screens])
        return instance

    @classmethod
    def intents(
        cls,
        *,
        initial: Any,
        routes: Mapping[type[Any], Callable[[Any], ScreenLike]],
        layer_composer: NavigationLayerComposer | None = None,
    ) -> Navigator:
        """Create a Navigator that resolves intents through a routing table.

        Args:
            initial: The intent that resolves the first screen.
            routes: Mapping of intent types to factories. Each factory returns
                a widget or a ``(widget, transition)`` pair.
            layer_composer: Optional custom layer composer.
        """
        instance = cls(layer_composer=layer_composer)
        instance._intent_routes = dict(routes)
        instance._stack = StackRuntime(initial=[instance._resolve_intent_to_route(initial)])
        return instance

    @classmethod
    def of(cls: type[NavigatorT], context: Widget, root: bool = False) -> NavigatorT:
        """Return the ``Navigator`` that navigation from ``context`` should drive.

        The nearest ancestor wins, so a nested navigator keeps its own history.
        With no ancestor, the App's navigator.

        Args:
            context: A widget in the subtree from which to resolve.
            root: Return the App's navigator, skipping ancestors. Use it for a
                full-window push from inside a nested navigator.

        Raises:
            RuntimeError: If ``context`` is not mounted yet (as in ``__init__``),
                or no navigator exists.
        """
        if not root:
            navigator = find_provider(context, cls)
            if navigator is not None:
                return navigator

        window = find_window(context)
        window_navigator = window._navigator if window is not None else None
        if window_navigator is None:
            raise_if_premature_lookup(f"{cls.__name__}.of", context)
            raise RuntimeError(
                f"No {cls.__name__} found for {context.__class__.__name__}: it has no "
                f"{cls.__name__} ancestor and is not attached to a Window."
            )
        if not isinstance(window_navigator, cls):
            raise RuntimeError(
                f"The Window's navigator is a {type(window_navigator).__name__}, not a {cls.__name__}. "
                f"Pass one as the Window's content=, or nest one in the subtree."
            )
        return window_navigator

    def can_pop(self) -> bool:
        return self._stack.can_pop(min_elements=1)

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
        widget = route.widget
        if widget not in self.children_snapshot():
            self.add_child(widget)
        return widget

    def _default_transition(self) -> TransitionSpec:
        """Return the transition a screen gets when none is given."""
        return Transitions.empty()

    def _to_route(self, screen: ScreenLike, transition: TransitionSpec | None = None) -> Route:
        """Wrap a screen, or a ``(widget, transition)`` pair, into a stack element."""
        widget: Any = screen
        if isinstance(screen, tuple):
            widget, transition = screen
        if not isinstance(widget, Widget):
            raise TypeError(f"A Navigator screen must be a Widget, got {type(widget).__name__}")
        return Route(widget=widget, transition=self._default_transition() if transition is None else transition)

    def _resolve_intent_to_route(self, intent: Any) -> Route:
        factory = self._intent_routes.get(type(intent))
        if factory is None:
            raise RuntimeError(f"No route is registered for intent: {type(intent).__name__}")
        return self._to_route(factory(intent))

    def _descriptor_for_push(self, screen: Widget | Any) -> _PushDescriptor | None:
        """Return the restore record for a ``push`` input; ``None`` for a widget, which has no factory."""
        if isinstance(screen, Widget):
            return None
        return _PushDescriptor(intent=screen, type_qualname=_type_qualname(type(screen)))

    def _resolve_descriptor_to_route(self, descriptor: _PushDescriptor) -> Route | None:
        """Rebuild a route from a descriptor; ``None`` when its intent is no longer registered."""
        factory = None
        for intent_type, builder in self._intent_routes.items():
            if _type_qualname(intent_type) == descriptor.type_qualname:
                factory = builder
                break
        if factory is None:
            return None
        return self._to_route(factory(descriptor.intent))

    def _normalize_to_route(self, screen: Widget | Any, transition: TransitionSpec | None) -> Route:
        """Turn ``push`` input into a stack element."""
        if isinstance(screen, Widget):
            return self._to_route(screen, transition)
        if transition is not None:
            raise TypeError("transition= applies to a widget; an intent's factory gives its own transition")
        return self._resolve_intent_to_route(screen)

    def _is_animated_transition(self, route: Route) -> bool:
        return not isinstance(route.transition, EmptyTransitionSpec)

    def _on_transition_progress(self, value: float) -> None:
        # ``progress`` is not observable, so each step repaints explicitly.
        transition = self._transition
        if transition is None:
            return
        transition.progress = float(value)
        self.invalidate()

    def _get_motion(self, route: Route, phase: TransitionPhase, *, back: bool = False) -> Any | None:
        return resolve_phase_motion(route.transition, phase, back=back)

    def push(self, screen: Widget | Any, *, transition: TransitionSpec | None = None) -> None:
        """Push a new screen onto the navigation stack.

        Args:
            screen: A widget, or an intent resolved through the navigator's routes.
            transition: The transition the widget moves with, on push and later
                on pop. Defaults to none; ``MaterialNavigator`` defaults to
                the Material page transition.

        Raises:
            TypeError: If ``transition`` is given with an intent.
        """
        self._cancel_transition()

        previous_route = self._top_route()
        previous_widget = None if previous_route is None else self._route_widget(previous_route)

        route = self._normalize_to_route(screen, transition)
        self._restore_log.append(self._descriptor_for_push(screen))

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

    @property
    def stack(self) -> tuple[Widget, ...]:
        """The screens on the stack, bottom to top.

        A popping screen stays until its exit transition ends. To wait for a
        pop, wait for this to shrink::

            navigator.pop()
            await app.wait_for(lambda: len(navigator.stack) == 1)

        Reading this mounts nothing.
        """
        return tuple(route.widget for route in self._stack.elements)

    @property
    def in_transition(self) -> bool:
        """Whether a navigation is in flight, animated or not.

        True from the call to :meth:`pop` until the stack settles, including
        before the pop's task starts. Prefer waiting on :attr:`stack` when the
        depth changes.
        """
        return self._transition is not None or self._back_requests_in_flight > 0 or self._pending_pop_requests > 0

    def snapshot_stack(self) -> list[_PushDescriptor | None]:
        """Return the restore log for :meth:`restore_stack`, not the route stack.

        One entry per :meth:`push`, bottom to top: a descriptor for an intent,
        ``None`` for a widget. The initial screens are left out; a hot reload
        rebuilds them from the factory.
        """
        return list(self._restore_log)

    def restore_stack(self, descriptors: Sequence[_PushDescriptor | None]) -> int:
        """Replay a restore log onto a freshly built navigator, without animation.

        Replay stops at a widget entry or an intent no longer registered; the
        screens above it are lost.

        Args:
            descriptors: What :meth:`snapshot_stack` returned before the reload.

        Returns:
            The number of screens restored.
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
        # Counted before the task starts, so ``in_transition`` covers the gap.
        self._back_requests_in_flight += 1
        scheduled = False
        try:
            task = spawn_task(self._tracked_request_back(), owner_name=f"{type(self).__name__}.pop")
            scheduled = task is not None
        finally:
            # A coroutine closed before it starts runs no ``finally``, so release here.
            if not scheduled:
                self._back_requests_in_flight -= 1

    async def _tracked_request_back(self) -> bool:
        """Run a back request whose in-flight count was taken by the caller."""
        try:
            return await self._request_back()
        finally:
            self._back_requests_in_flight -= 1

    async def request_back(self) -> bool:
        """Request one back action, as from Esc or a back button.

        During a pop transition, the request is queued and the running pop
        finishes at once. Queued pops run without animation, except the last.

        Returns:
            ``False`` if the stack cannot pop.
        """
        self._back_requests_in_flight += 1
        return await self._tracked_request_back()

    async def _request_back(self) -> bool:
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

        # A pop refused by the screen still counts as handled.
        await self._pop_once(skip_animation=False)
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

            # An animated pop drains the rest when it finishes.
            if self._transition is not None and self._transition_handle is not None and self._transition.kind == "pop":
                return

        if not self.can_pop():
            self._pending_pop_requests = 0

    async def _pop_once(self, *, skip_animation: bool) -> bool:
        if not self.can_pop():
            return False

        self._cancel_transition()

        routes = self._stack.elements
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
                motion=self._get_motion(outgoing, TransitionPhase.EXIT, back=True),
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

        widget = route.widget
        self._stack.complete_exit(route)
        # Initial screens are not logged, so popping one leaves the log alone.
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
        """Return only the top screen, so Tab never reaches a covered one.

        Covered screens stay mounted to keep their state.
        """
        routes = self._stack.elements
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

        # Lay out every mounted screen so hit_test coordinate translation works.
        children = self.children_snapshot()
        for route in self._stack.elements:
            widget = route.widget
            if widget not in children:
                continue
            try:
                widget.layout(width, height)
                widget.set_layout_rect(0, 0, width, height)
            except Exception:
                exception_once(_logger, "navigator_layout_route_widget_exc", "Route widget layout failed")

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)

        routes = self._stack.elements
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
                    from_transition_spec=transition.from_route.transition,
                    to_transition_spec=transition.to_route.transition,
                )
                self._layer_composer.paint_transition(context)
                return

        # Unknown transition kind: paint top.
        top_widget = self._route_widget(routes[-1])
        self._layer_composer.paint_static(canvas=canvas, widget=top_widget, x=x, y=y, width=width, height=height)

    def hit_test(self, x: int, y: int):
        transition = self._transition
        if transition is None:
            routes = self._stack.elements
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


def _transition_phase_progress(transition: _NavTransition) -> tuple[TransitionPhase, TransitionPhase, float] | None:
    # Only the lower bound is pinned: an overshooting motion runs past 1.0.
    if transition.kind == "push":
        p = max(0.0, transition.progress)
        return (TransitionPhase.EXIT, TransitionPhase.ENTER, p)
    if transition.kind == "pop":
        p = max(0.0, 1.0 - transition.progress)
        return (TransitionPhase.EXIT, TransitionPhase.ENTER, p)
    return None
