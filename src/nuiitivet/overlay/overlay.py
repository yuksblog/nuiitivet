"""Overlay widget for displaying transient layers."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, TypeVar

from nuiitivet.widgeting.callbacks import spawn_task
from nuiitivet.widgeting.context_lookup import find_provider, find_window, raise_if_premature_lookup
from nuiitivet.widgeting.modifier import Modifier, ModifierElement
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.layout.stack import Stack
from nuiitivet.layout.container import Container
from nuiitivet.modifiers.background import background
from nuiitivet.modifiers.block_pointer import block_pointer
from nuiitivet.modifiers.clickable import clickable
from nuiitivet.modifiers.passthrough_pointer import passthrough_pointer
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

# Lets ``of()`` keep the concrete subclass type, so that
# ``MaterialOverlay.of(...)`` is a ``MaterialOverlay`` and not an ``Overlay``.
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


class _LayerStack(ComposableWidget):
    """Private stack of overlay layers.

    Separate from ``Navigator`` on purpose: layers pile up on top of each other
    rather than replacing one another, and the app's navigation stack never
    sees them.
    """

    def __init__(self) -> None:
        super().__init__(width="wt", height="wt")
        self._stack: StackRuntime[_OverlayLayer] = StackRuntime()
        self._pending_dispose: dict[int, Callable[[], None]] = {}
        # One Stack for the life of the overlay, synced one layer at a time: a
        # rebuild per push or exit would remount every live entry.
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

    # No hit_test override needed: this widget and its transparent Stack both
    # defer under the ``auto`` default, so input passes through whenever no
    # actual overlay layer is hit.


class _OverlayLayer:
    """One overlay entry on the layer stack, with its transition.

    OverlayEntry owns widget unmounting. The layer must not unmount to avoid
    double-dispose when the entry is removed.
    """

    def __init__(
        self,
        entry: OverlayEntry,
        *,
        transition_spec: TransitionSpec | None = None,
    ) -> None:
        # The layer keeps the entry, not just its builder: the layer stack is
        # what ``Overlay.open_entries`` reports (it is the book that survives an
        # exit animation), so the stack has to be able to name the entry each
        # layer belongs to.
        self.entry: OverlayEntry = entry
        self.transition_spec: TransitionSpec = transition_spec or Transitions.empty()
        self.transition_state: TransitionState = TransitionState.create(self.transition_spec)
        self._transition_engine = TransitionEngine()
        self._widget: Widget | None = None
        # Whether input reaches the content behind this entry. Pass-through
        # entries (toasts, banners, tooltips) do not occlude; blocking entries
        # do. Set by ``Overlay.show``.
        #
        # This is deliberately *not* a barrier setting: the pointer half of
        # ``passthrough`` is applied in ``show`` (the blocking layer), while the
        # keyboard half is read straight off this layer by
        # ``occluding_content_widget()``, which drives the modal focus trap and
        # FOREGROUND shortcut scoping.
        self._passthrough: bool = True

    def build_widget(self) -> Widget:
        if self._widget is not None and getattr(self._widget, "_unmounted", False):
            self._widget = None
        if self._widget is None:
            self._widget = self.entry.build_widget()
        return self._widget

    @property
    def _content_widget(self) -> Widget | None:
        """The entry's content, stored once on the entry rather than twice.

        The layer is the object the input and focus paths hold, the entry is the
        object ``open_entries`` hands out, and both want the same widget. One
        storage location, read from either side.
        """
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
        # Values above 1.0 are kept: expressive spatial motions overshoot their
        # target and settle, and the visual resolver extrapolates spatial
        # patterns through that settle. Only the lower bound is pinned.
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

    A hit inside the rect is declined outright — neither blocked nor counted
    as an outside tap — so the pointer walk falls through to whatever the
    entry covers there. The rect comes from a provider because it can move
    every frame (an anchor animating its margin).

    The provider's rect is in window coordinates (a painted rect), so the
    local point is translated by this box's own painted origin before the
    comparison. An entry's layers span the window at the origin, making the
    translation a no-op in practice — it is kept for correctness, with the
    unpainted case (origin unknown) treated as the origin.
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
    """Fallback core composer with minimal, design-agnostic rendering.

    Painting only. Stacking, input blocking and outside-tap dismissal are
    applied by :meth:`Overlay.show` around whatever this returns.
    """

    # Neutral fallback backdrop. Private on purpose: a design system supplies its
    # own composer, so this colour never crosses the composition boundary.
    _BACKDROP_COLOR = (0, 0, 0, 128)

    def compose(self, context: OverlayLayerCompositionContext) -> OverlayLayerPaint:
        return OverlayLayerPaint(
            content=context.position_content(context.content),
            backdrop=(
                Container(width="wt", height="wt").modifier(background(self._BACKDROP_COLOR))
                if context.backdrop
                else None
            ),
        )


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
        """Return the content of the topmost entry that blocks input, if any.

        A ``passthrough=False`` entry swallows interaction with everything below
        it; a pass-through entry (toast, banner, tooltip) does not. Callers that
        must know "can the user still act on the content behind the overlay"
        — keyboard-shortcut dispatch, for one — ask this. ``None`` means nothing
        is blocking and the content below is still reachable.

        This is the keyboard half of ``passthrough``; the pointer half is the
        blocking layer built in :meth:`show`.
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
            asyncio.get_running_loop()
        except RuntimeError:
            # No event loop; cannot await will_pop. Fall back to immediate dismiss.
            self._dismiss_entry_with_value(entry, value=value, reason=reason)
            return

        async def _go() -> None:
            if await self._consult_will_pop(content):
                self._dismiss_entry_with_value(entry, value=value, reason=reason)

        # Through spawn_task, not loop.create_task, so a test harness can wait
        # for the dismissal. The no-loop case is handled above rather than by
        # spawn_task: dropping the dismissal is the wrong degradation here, and
        # falling back to an immediate one is what this method already promises.
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
        transition_spec: TransitionSpec | None = None,
    ) -> OverlayHandle[Any]:
        """Show content as an overlay entry.

        The presentation is described by three orthogonal axes rather than by a
        scenario name. Two of them are about input and are enforced here, in the
        core; only ``backdrop`` is about appearance and crosses into the design
        system's layer composer.

        Args:
            content: Widget to present.
            passthrough: Whether input reaches the content behind this entry.
                ``False`` (the default) installs a full-screen blocking layer and
                occludes everything below, for both pointer and keyboard.
            dismiss_on_outside_tap: Whether tapping outside the content dismisses
                the entry. Requires ``passthrough=False``.
            passthrough_rect: A window-coordinate rect the blocking layer leaves
                alone: a tap inside it is neither blocked nor an outside tap —
                it falls through to the content behind, which also keeps it from
                dismissing the entry. A provider rather than a rect so it can
                track a moving anchor. Inert with ``passthrough=True``, where
                nothing is blocked to begin with.
            backdrop: Whether the layer composer paints a backdrop behind the
                content. Purely visual — input blocking is ``passthrough``'s job.
            timeout: Seconds after which the entry auto-dismisses, or ``None``.
            position: Where to place the content. Defaults to centered.
            transition_spec: Enter/exit animation for the entry. Defaults to
                none: the entry appears and disappears at once.

        Returns:
            An :class:`OverlayHandle` for the shown entry.

        Raises:
            ValueError: If ``timeout`` is negative, or if ``passthrough=True`` is
                combined with ``dismiss_on_outside_tap=True`` — observing a tap
                without consuming it needs multi-target dispatch.

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
                # A backdrop is decoration. Left alone it would catch pointer
                # events, because a painted surface is a hit target in this
                # framework ("painted = clickable", Box._hit_self_opaque) — and
                # it would then swallow the very outside tap the blocking layer
                # below exists to receive. Whether a layer participates in input
                # is the core's call, so the core makes it click-through rather
                # than leaving every composer to remember.
                layers.append(paint.backdrop.modifier(passthrough_pointer()))

            if not passthrough:

                def on_outside_tap() -> None:
                    self._request_dismiss_entry(entry, reason=OverlayDismissReason.OUTSIDE_TAP)

                # Input blocking lives here, not in the composer: a composer
                # paints. ``block_pointer()`` is (descend_children=True,
                # self_opaque=True) — let the content's own hits through, catch
                # everything else. Because the S axis decouples hit-catching from
                # painted-ness, this layer is hittable while being fully
                # invisible; no transparent background() trick is needed.
                blocker_modifier: Modifier | ModifierElement = block_pointer()
                if dismiss_on_outside_tap:
                    # ORDER IS LOAD-BEARING: block_pointer() must come *before*
                    # clickable() in the chain. Modifier.apply runs left to right,
                    # so the leftmost element ends up innermost. clickable() does
                    # not wrap — it returns ensure_interaction_region(widget) — so
                    # it has to sit *outside* the HitParticipationBox: the box is
                    # the hit target and pointer bubbling walks parents only, so
                    # the region must be an ancestor of it. Reversed, the region
                    # would be the box's child and would never see the event.
                    #
                    # any_button=True: an outside tap dismisses whichever button
                    # produced it, not just the primary one.
                    blocker_modifier = blocker_modifier | clickable(on_click=on_outside_tap, any_button=True)
                blocker: Widget = Container(width="wt", height="wt").modifier(blocker_modifier)
                if passthrough_rect is not None:
                    blocker = _PassthroughRectBox(blocker, rect_provider=passthrough_rect)
                layers.append(blocker)

            # ORDER IS LOAD-BEARING: the content must be *last* in children.
            # _hit_test_children walks reversed(children), so the content is
            # tested first and the blocker only catches what the content
            # declined. Reversed, the blocker would swallow every hit including
            # those meant for the overlay content itself.
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
        layer = _OverlayLayer(entry, transition_spec=transition_spec)
        layer_holder["layer"] = layer
        layer._content_widget = content_widget
        layer._passthrough = passthrough

        # Construct the handle first so OverlayAware widgets receive it
        # before the entry is inserted (i.e. before first build / mount).
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
        """Hit test that passes through if no entry is hit.

        With no entries the overlay is fully transparent and short-circuits.
        Otherwise it delegates to the composed subtree, which passes input
        through under the ``auto`` default whenever no overlay layer is hit.
        """
        if not self.has_entries():
            return None
        return super().hit_test(x, y)

    def is_visually_empty(self) -> bool:
        """Whether the overlay is drawing nothing right now.

        The declarative counterpart to :meth:`hit_test`'s short-circuit: with no
        entries the overlay is fully transparent, but its scaffolding stays
        mounted at full window size. ``hit_test`` answers that for input; this
        answers it for anything reading the tree geometrically, which cannot tell
        an empty layer from an opaque one by its rect.
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

        An entry is open from the moment it is shown until its exit animation
        has finalized -- **not** until it is dismissed. Those differ by the width
        of the animation, during which the layer is still mounted, still laid out
        and still painted, so reporting it as closed would be a lie a caller acts
        on. To wait one out, wait for this to shrink::

            overlay.close()
            await app.wait_for(lambda: not overlay.open_entries)

        Reading this never builds a widget. Asking what is open must not change
        what is on screen, so the answer comes from the layer stack and the
        entries on it, never from ``build_widget()``.
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
            # Map layer widgets to their entries for quick lookup
            layer_widget_to_entry = {
                layer._widget: entry for entry, layer in self._entry_to_layer.items() if layer._widget is not None
            }

            # Walk up the widget tree from target to find the owning layer widget
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

        The nearest ancestor ``Overlay`` wins, so an intentionally nested one
        captures the layers shown from inside it. With no such ancestor the
        answer is the App's own overlay — which is *not* reachable by an ancestor
        walk, because the App composes it as a sibling layer of the ``Navigator``
        rather than as a wrapper around the content.

        Args:
            context: A widget in the subtree from which to resolve.
            root: Skip the ancestor search and return the App's overlay, to show
                a layer above everything from inside a nested overlay.

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
                f"Pass overlay_factory={cls.__name__} to the Window (or App), or wrap the subtree in one."
            )
        return window_overlay
