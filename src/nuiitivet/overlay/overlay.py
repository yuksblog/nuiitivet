"""Overlay widget for displaying transient layers."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, TypeVar

from nuiitivet.widgeting.callbacks import spawn_task
from nuiitivet.widgeting.context_lookup import find_provider, find_window, raise_if_premature_lookup
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.container import Container
from nuiitivet.widgeting.hit_participation import HitParticipationBox
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import ensure_interaction_region
from nuiitivet.observable import Observable
from nuiitivet.observable import runtime
from nuiitivet.transition.engine import TransitionEngine
from nuiitivet.transition.spec import (
    EmptyTransitionSpec,
    TransitionPhase,
    TransitionSpec,
    Transitions,
    resolve_phase_motion,
)
from nuiitivet.transition.stack import StackRuntime
from nuiitivet.transition.state import TransitionState
from nuiitivet.common.logging_once import exception_once
from .overlay_aware import OverlayAware
from .overlay_entry import OverlayEntry
from .overlay_handle import OverlayHandle
from .overlay_position import OverlayPosition
from .result import OverlayDismissReason, OverlayResult
from .layer_composer import OverlayLayerComposer, OverlayLayerCompositionContext, OverlayLayerPaint

logger = logging.getLogger(__name__)

# Lets ``MaterialOverlay.of(...)`` return a ``MaterialOverlay``, not an ``Overlay``.
OverlayT = TypeVar("OverlayT", bound="Overlay")


def _find_overlay_aware(widget: Widget) -> OverlayAware[Any] | None:
    """Return the first OverlayAware widget in the subtree, looking through modifier wrappers."""
    if isinstance(widget, OverlayAware):
        return widget
    for child in widget.children:
        if isinstance(child, Widget):
            found = _find_overlay_aware(child)
            if found is not None:
                return found
    return None


class _LayerStack(ComposableWidget):
    """Private stack of overlay layers, newest painted on top."""

    def __init__(self) -> None:
        super().__init__(width="wt", height="wt")
        self._stack: StackRuntime[_OverlayLayer] = StackRuntime()
        self._pending_dispose: dict[int, Callable[[], None]] = {}
        # Synced one layer at a time: a rebuild per push would remount every live entry.
        self._layers = Stack(children=[], alignment="center", width="wt", height="wt")
        self._widget_by_layer: dict[int, Widget] = {}

    @property
    def layers(self) -> list[_OverlayLayer]:
        return self._stack.elements

    def can_pop(self) -> bool:
        return self._stack.can_pop(min_elements=0)

    def push(self, layer: _OverlayLayer) -> None:
        self._stack.push(layer)
        if self._should_animate(layer):
            layer.start_enter(
                on_update=lambda: self.invalidate(),
                on_complete=lambda: self._mark_active(layer),
            )
        else:
            self._stack.mark_active(layer)
        self._add_layer_widget(layer)

    def remove(self, layer: _OverlayLayer, *, on_disposed: Callable[[], None] | None = None) -> None:
        if layer not in self._stack.elements:
            if on_disposed is not None:
                on_disposed()
            return
        if not self._stack.mark_exiting(layer):
            if on_disposed is not None:
                on_disposed()
            return
        if on_disposed is not None:
            self._pending_dispose[id(layer)] = on_disposed

        if self._should_animate(layer):
            layer.start_exit(
                on_update=lambda: self.invalidate(),
                on_complete=lambda: self._finalize_exit(layer),
            )
            return

        self._finalize_exit(layer)

    def _finalize_exit(self, layer: _OverlayLayer) -> None:
        try:
            self._stack.complete_exit(layer)
        except Exception:
            exception_once(logger, "overlay_layer_dispose_exc", "Overlay layer dispose raised")
        callback = self._pending_dispose.pop(id(layer), None)
        if callback is not None:
            try:
                callback()
            except Exception:
                exception_once(logger, "overlay_layer_on_disposed_exc", "Overlay layer on_disposed raised")
        self._remove_layer_widget(layer)

    def pop(self) -> None:
        if not self.can_pop():
            return
        layer = self._stack.begin_pop()
        if layer is None:
            return
        self.remove(layer)

    def _mark_active(self, layer: _OverlayLayer) -> None:
        self._stack.mark_active(layer)
        self.invalidate()

    def _should_animate(self, layer: _OverlayLayer) -> bool:
        if isinstance(layer.transition_spec, EmptyTransitionSpec):
            return False
        return getattr(self, "_app", None) is not None

    def _add_layer_widget(self, layer: _OverlayLayer) -> None:
        try:
            widget = layer.build_widget()
        except Exception:
            exception_once(logger, "overlay_layer_build_widget_exc", "Overlay layer build_widget raised")
            return
        self._widget_by_layer[id(layer)] = widget
        self._layers.add_child(widget)

    def _remove_layer_widget(self, layer: _OverlayLayer) -> None:
        widget = self._widget_by_layer.pop(id(layer), None)
        if widget is not None:
            self._layers.remove_child(widget)

    def build(self) -> Widget:
        return self._layers

    # No hit_test override: a miss on every layer passes through under the auto default.


class _OverlayLayer:
    """One overlay entry on the layer stack, with its transition.

    The entry owns unmounting; the layer never unmounts, or the widget would be disposed twice.
    """

    def __init__(
        self,
        entry: OverlayEntry,
        *,
        transition: TransitionSpec | None = None,
    ) -> None:
        # The entry itself, not its builder: open_entries names each layer's entry from this stack.
        self.entry: OverlayEntry = entry
        self.transition_spec: TransitionSpec = transition or Transitions.empty()
        self.transition_state: TransitionState = TransitionState.create(self.transition_spec)
        self._transition_engine = TransitionEngine()
        self._widget: Widget | None = None
        # The keyboard half of show(passthrough=...), read by occluding_content_widget().
        self._passthrough: bool = True

    def build_widget(self) -> Widget:
        if self._widget is not None and getattr(self._widget, "_unmounted", False):
            self._widget = None
        if self._widget is None:
            self._widget = self.entry.build_widget()
        return self._widget

    @property
    def _content_widget(self) -> Widget | None:
        """The entry's content, stored on the entry so the layer and the entry never disagree."""
        return self.entry._content

    @_content_widget.setter
    def _content_widget(self, widget: Widget | None) -> None:
        self.entry._content = widget

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
        return resolve_phase_motion(self.transition_spec, phase)

    def _apply_progress(self, value: float, *, on_update: Callable[[], None]) -> None:
        # Only the lower bound is pinned: spatial motions overshoot 1.0 and settle.
        self.transition_progress_obs.value = max(0.0, float(value))
        on_update()

    def _finish_enter(self, *, on_update: Callable[[], None], on_complete: Callable[[], None]) -> None:
        self.transition_phase_obs.value = TransitionPhase.ACTIVE
        self.transition_progress_obs.value = 1.0
        on_update()
        on_complete()

    def dispose(self) -> None:
        self._transition_engine.dispose()
        self._widget = None


class _PassthroughRectBox(Widget):
    """Wraps the blocking layer and exempts one rect from it.

    A hit inside the rect is neither blocked nor an outside tap; it falls
    through to the content behind. The rect is in window coordinates and is
    re-read on every hit, so it can follow a moving anchor.
    """

    def __init__(
        self,
        child: Widget,
        *,
        rect_provider: Callable[[], tuple[float, float, float, float] | None],
    ) -> None:
        super().__init__(
            width=child.width_sizing,
            height=child.height_sizing,
            max_children=1,
            overflow_policy="replace_last",
        )
        self._rect_provider = rect_provider
        self.add_child(child)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        child = self.children[0]
        if isinstance(child, Widget):
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)

    def hit_test(self, x: int, y: int):
        rect: tuple[float, float, float, float] | None = None
        try:
            rect = self._rect_provider()
        except Exception:
            exception_once(logger, "overlay_passthrough_rect_provider_exc", "passthrough_rect provider raised")
        if rect is not None:
            gx, gy = 0.0, 0.0
            own = self.global_visual_rect
            if own is not None:
                gx, gy = own[0], own[1]
            rx, ry, rw, rh = rect
            if rx <= gx + x < rx + rw and ry <= gy + y < ry + rh:
                return None
        return super().hit_test(x, y)


class _DefaultOverlayLayerComposer:
    """Fallback composer: a neutral backdrop and the positioned content, nothing else."""

    # Private: a design system brings its own composer and colour.
    _BACKDROP_COLOR = (0, 0, 0, 128)

    def compose(self, context: OverlayLayerCompositionContext) -> OverlayLayerPaint:
        return OverlayLayerPaint(
            content=context.position_content(context.content),
            backdrop=(
                Box(width="wt", height="wt", background_color=self._BACKDROP_COLOR)
                if context.backdrop
                else None
            ),
        )


class Overlay(ComposableWidget):
    """Layers shown on top of the window content, newest on top.

    Show a layer with :meth:`show`; it returns a handle that closes the layer
    and can be awaited for its result.
    """

    def __init__(self, *, layer_composer: OverlayLayerComposer | None = None, key: str | None = None) -> None:
        super().__init__(width="wt", height="wt", key=key)

        self._layer_stack: _LayerStack = _LayerStack()
        self._entry_to_layer: Dict[OverlayEntry, _OverlayLayer] = {}
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
        layer = self._entry_to_layer.get(entry)
        if layer is None:
            return None
        return layer._content_widget

    def _top_entry(self) -> OverlayEntry | None:
        """The topmost entry still open, or ``None`` while the top is exiting."""
        layers = self._layer_stack.layers
        if not layers:
            return None
        top = layers[-1]
        return top.entry if self._entry_to_layer.get(top.entry) is top else None

    def occluding_content_widget(self) -> Widget | None:
        """Return the content of the topmost entry shown with ``passthrough=False``.

        ``None`` means nothing blocks, and the content behind the overlay is
        still reachable from the keyboard.
        """
        for layer in reversed(self._layer_stack.layers):
            if layer._passthrough:
                continue
            return layer._content_widget or layer._widget
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
        """Evaluate will_pop synchronously; ``None`` means the handler is async and must be awaited."""
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
            # The caller re-invokes and awaits; close this one to avoid a "never awaited" warning.
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
        """Dismiss an entry unless its content's will_pop handler refuses.

        With an async handler and no running event loop, the entry is dismissed at once.
        """
        content = self._entry_content_widget(entry)
        sync = self._will_pop_proceed_sync(content)
        if sync is True:
            self._dismiss_entry_with_value(entry, value=value, reason=reason)
            return
        if sync is False:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._dismiss_entry_with_value(entry, value=value, reason=reason)
            return

        async def _go() -> None:
            if await self._consult_will_pop(content):
                self._dismiss_entry_with_value(entry, value=value, reason=reason)

        # spawn_task, so a test harness can wait for the dismissal.
        spawn_task(_go(), owner_name=f"{type(self).__name__}.dismiss")

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

    def show(
        self,
        content: Widget,
        *,
        passthrough: bool = False,
        dismiss_on_outside_tap: bool = False,
        passthrough_rect: Callable[[], tuple[float, float, float, float] | None] | None = None,
        backdrop: bool = False,
        timeout: float | None = None,
        position: OverlayPosition | None = None,
        transition: TransitionSpec | None = None,
    ) -> OverlayHandle[Any]:
        """Show content as an overlay entry.

        Args:
            content: Widget to present.
            passthrough: Whether input reaches the content behind this entry.
                ``False`` (the default) installs a full-screen blocking layer and
                occludes everything below, for both pointer and keyboard.
            dismiss_on_outside_tap: Whether tapping outside the content dismisses
                the entry. Requires ``passthrough=False``.
            passthrough_rect: Returns a window-coordinate rect the blocking layer
                leaves alone. A tap inside it reaches the content behind and does
                not dismiss. Read on every hit, so it can follow a moving anchor.
            backdrop: Whether a backdrop is painted behind the content. Visual
                only; ``passthrough`` decides input.
            timeout: Seconds after which the entry auto-dismisses, or ``None``.
            position: Where to place the content. Defaults to centered.
            transition: Enter/exit animation for the entry. Defaults to
                none: the entry appears and disappears at once.

        Returns:
            An :class:`OverlayHandle` for the shown entry.

        Raises:
            ValueError: If ``timeout`` is negative, or if ``passthrough=True`` is
                combined with ``dismiss_on_outside_tap=True``.

        Notes:
            - `await handle` returns an OverlayResult.
            - Awaiting requires a running async runtime.
        """
        if timeout is not None and float(timeout) < 0:
            raise ValueError("timeout must be >= 0 or None")
        if passthrough and dismiss_on_outside_tap:
            raise ValueError(
                "passthrough=True cannot be combined with dismiss_on_outside_tap=True: "
                "a layer that lets a tap through cannot also observe it. "
                "Observing without consuming would need pass-behind (multi-target) "
                "dispatch, which the overlay does not do."
            )

        entry: OverlayEntry

        content_widget = content

        effective_position = position or OverlayPosition.aligned("center")

        def position_content(content: Widget) -> Widget:
            return effective_position.make_position_content(content)

        def on_dispose() -> None:
            self._complete_entry_future(entry, OverlayResult(value=None, reason=OverlayDismissReason.DISPOSED))

        def build_layer(layer: _OverlayLayer) -> Widget:
            context = OverlayLayerCompositionContext(
                content=content_widget,
                transition_state=layer.transition_state,
                backdrop=backdrop,
                position_content=position_content,
            )
            paint = self._layer_composer.compose(context)

            layers: list[Widget] = []

            if paint.backdrop is not None:
                # A painted backdrop is a hit target; unwrapped, it would swallow the outside tap.
                layers.append(HitParticipationBox(paint.backdrop, descend_children=False, self_opaque=False))

            if not passthrough:

                def on_outside_tap() -> None:
                    self._request_dismiss_entry(entry, reason=OverlayDismissReason.OUTSIDE_TAP)

                # Invisible, yet catches every hit that reaches it.
                blocker: Widget = HitParticipationBox(
                    Container(width="wt", height="wt"), descend_children=True, self_opaque=True
                )
                if dismiss_on_outside_tap:
                    # The region wraps the box: pointer bubbling walks parents only.
                    region = ensure_interaction_region(blocker)
                    region.enable_click(on_click=on_outside_tap, any_button=True)
                    blocker = region
                if passthrough_rect is not None:
                    blocker = _PassthroughRectBox(blocker, rect_provider=passthrough_rect)
                layers.append(blocker)

            # Last, because children are hit-tested in reverse: the content before the blocker.
            layers.append(paint.content)

            if len(layers) == 1:
                return layers[0]
            return Stack(children=layers, alignment="top-left", width="wt", height="wt")

        layer_holder: dict[str, _OverlayLayer] = {}
        widget_holder: dict[str, Widget] = {}

        def build_entry_widget() -> Widget:
            layer = layer_holder.get("layer")
            if layer is None:
                return Container()
            widget = widget_holder.get("widget")
            if widget is None:
                widget = build_layer(layer)
                widget_holder["widget"] = widget
            return widget

        entry = OverlayEntry(builder=build_entry_widget, on_dispose=on_dispose)
        layer = _OverlayLayer(entry, transition=transition)
        layer_holder["layer"] = layer
        layer._content_widget = content_widget
        layer._passthrough = passthrough

        # Before insertion, so OverlayAware content has its handle by first build.
        handle: OverlayHandle[Any] = OverlayHandle(overlay=self, entry=entry)
        aware = _find_overlay_aware(content_widget)
        if aware is not None:
            aware._set_overlay_handle(handle)

        self._insert_entry_layer(entry, layer)

        if timeout is not None:

            def on_timeout(_dt: float) -> None:
                self._dismiss_entry(entry, reason=OverlayDismissReason.TIMEOUT)

            self._entry_to_timeout_cb[entry] = on_timeout
            runtime.clock.schedule_once(on_timeout, float(timeout))

        return handle

    def hit_test(self, x: int, y: int):
        """Hit test that passes through wherever no entry is hit."""
        if not self.has_entries():
            return None
        return super().hit_test(x, y)

    def is_visually_empty(self) -> bool:
        """Whether the overlay draws nothing right now.

        With no entries it still spans the window, so its rect cannot tell empty from opaque.
        """
        return not self.has_entries()

    def build(self) -> Widget:
        return self._layer_stack

    def insert_entry(self, entry: OverlayEntry) -> None:
        self._insert_entry_layer(entry, _OverlayLayer(entry))

    def _insert_entry_layer(self, entry: OverlayEntry, layer: _OverlayLayer) -> None:
        self._entry_to_layer[entry] = layer
        self._layer_stack.push(layer)

    def remove_entry(self, entry: OverlayEntry) -> None:
        layer = self._entry_to_layer.pop(entry, None)
        if layer is None:
            return

        self._complete_entry_future(entry, OverlayResult(value=None, reason=OverlayDismissReason.DISPOSED))
        self._cancel_timeout_if_any(entry)

        future = self._entry_to_future.pop(entry, None)
        if future is not None and future.done() and entry not in self._entry_to_pending_result:
            try:
                self._entry_to_pending_result[entry] = future.result()
            except Exception:
                self._entry_to_pending_result[entry] = OverlayResult(value=None, reason=OverlayDismissReason.DISPOSED)

        self._layer_stack.remove(layer, on_disposed=entry.dispose)

    @property
    def open_entries(self) -> tuple[OverlayEntry, ...]:
        """The open entries, bottom to top.

        An entry stays open until its exit animation finishes, not until it is
        dismissed. To wait one out, wait for this to shrink::

            overlay.close()
            await app.wait_for(lambda: not overlay.open_entries)

        Reading this never builds a widget.
        """
        return tuple(layer.entry for layer in self._layer_stack.layers)

    def has_entries(self) -> bool:
        """Whether any entry is open. See :attr:`open_entries` for when one is."""
        return bool(self.open_entries)

    def clear(self) -> None:
        for entry in list(self._entry_to_layer.keys()):
            self.remove_entry(entry)
        self.invalidate()

    def close_topmost(self) -> None:
        self.request_close_topmost()

    def close(self, value: Any = None, target: Widget | None = None) -> None:
        if target is not None:
            layer_widget_to_entry = {
                layer._widget: entry for entry, layer in self._entry_to_layer.items() if layer._widget is not None
            }

            current: Widget | None = target  # type: ignore
            visited = set()

            while current is not None:
                if id(current) in visited:
                    break
                visited.add(id(current))

                if current in layer_widget_to_entry:
                    entry = layer_widget_to_entry[current]
                    self._complete_entry_future(entry, OverlayResult(value=value, reason=OverlayDismissReason.CLOSED))
                    self.remove_entry(entry)
                    return

                current = getattr(current, "parent", None)

            logger.warning(
                "Overlay.close called with widget target=%r, but no active overlay entry contains it.", target
            )
            return

        layers = self._layer_stack.layers
        if not layers:
            return

        top_layer = layers[-1]
        for entry, layer in reversed(list(self._entry_to_layer.items())):
            if layer is top_layer:
                self._complete_entry_future(entry, OverlayResult(value=value, reason=OverlayDismissReason.CLOSED))
                self.remove_entry(entry)
                return

        try:
            self._layer_stack.pop()
        except Exception:
            exception_once(logger, "overlay_close_fallback_pop_exc", "Overlay close fallback pop raised")

    @classmethod
    def of(cls: type[OverlayT], context: Widget, root: bool = False) -> OverlayT:
        """Return the ``Overlay`` that should host a layer shown from ``context``.

        The answer is the overlay of the window ``context`` belongs to. The
        ancestor search runs first, as the hook for a nested scope; the window is
        the only scope today.

        Args:
            context: A widget in the subtree from which to resolve.
            root: Skip the ancestor search and return the window's overlay.

        Raises:
            RuntimeError: If called before ``context`` is mounted (typically from
                ``__init__``), or if no overlay can be resolved at all.
        """
        if not root:
            overlay = find_provider(context, cls)
            if overlay is not None:
                return overlay

        window = find_window(context)
        window_overlay = window._overlay if window is not None else None
        if window_overlay is None:
            raise_if_premature_lookup(f"{cls.__name__}.of", context)
            raise RuntimeError(
                f"No {cls.__name__} found for {context.__class__.__name__}: it has no "
                f"{cls.__name__} ancestor and is not attached to a Window."
            )
        if not isinstance(window_overlay, cls):
            raise RuntimeError(
                f"The Window's overlay is a {type(window_overlay).__name__}, not a {cls.__name__}. "
                f"Pass overlay={cls.__name__} to the Window."
            )
        return window_overlay
