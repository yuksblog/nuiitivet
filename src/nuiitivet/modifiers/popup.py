"""popup() modifier – anchored transient overlays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, Tuple

from nuiitivet.layout.alignment import AlignmentLike
from nuiitivet.layout.measure import preferred_size as _measure_preferred_size
from nuiitivet.observable import runtime
from nuiitivet.overlay.overlay_position import OverlayPosition
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from typing import Any

    from nuiitivet.navigation.transition_spec import TransitionSpec
    from nuiitivet.observable.value import Observable
    from nuiitivet.overlay.overlay_handle import OverlayHandle


def _resolve_dismiss_on_outside_tap(passthrough: bool, dismiss_on_outside_tap: bool | None) -> bool:
    """Resolve the dismissal axis against the passthrough axis.

    ``None`` means "whatever pairs naturally with *passthrough*", which keeps
    both legal combinations spellable with a single flag. The fourth cell —
    passing the tap through *and* observing it — needs multi-target dispatch and
    is rejected here rather than silently ignored.
    """
    if dismiss_on_outside_tap is None:
        return not passthrough
    resolved = bool(dismiss_on_outside_tap)
    if passthrough and resolved:
        raise ValueError(
            "passthrough=True cannot be combined with dismiss_on_outside_tap=True: "
            "a popup that lets a tap through cannot also observe it. "
            "See issue #508 (pass-behind / multi-target dispatch)."
        )
    return resolved


class PopupBox(Widget):
    """Wraps an anchor widget and shows a transient popup overlay anchored to it.

    The overlay is rendered by :meth:`Overlay.show` (above the widget tree) so it
    avoids clipping and sits at the top of the Z-order.

    Open/close behaviour is driven exclusively through *is_open*. When ``None``
    is passed, an internal :class:`~nuiitivet.observable.value.Observable` is
    created; callers can toggle it via :attr:`is_open`. The observable is also
    set to ``False`` when the overlay is dismissed externally.
    """

    def __init__(
        self,
        child: Widget,
        content: Widget,
        *,
        is_open: Optional["Observable[bool]"] = None,
        passthrough: bool = False,
        dismiss_on_outside_tap: bool | None = None,
        target_anchor: AlignmentLike = "bottom-left",
        content_anchor: AlignmentLike = "top-left",
        offset: Tuple[float, float] = (0.0, 0.0),
        transition_spec: Optional["TransitionSpec"] = None,
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        """Initialize a popup wrapper around an anchor widget.

        Args:
            child: Anchor widget that determines popup attachment point.
            content: Widget rendered inside the popup overlay.
            is_open: Optional external observable controlling open/close state.
            passthrough: Whether input reaches the content behind the popup.
            dismiss_on_outside_tap: Whether an outside tap closes the popup.
                ``None`` resolves to ``not passthrough``.
            target_anchor: Reference point on the anchor widget.
            content_anchor: Reference point on the popup content.
            offset: Additional ``(dx, dy)`` offset in pixels.
            transition_spec: Optional transition passed to ``Overlay.show``.
            width: Width sizing for this wrapper.
            height: Height sizing for this wrapper.
        """
        super().__init__(width=width, height=height)
        self._content = content
        self._target_anchor = target_anchor
        self._content_anchor = content_anchor
        self._offset = offset
        self._transition_spec = transition_spec
        self._passthrough = bool(passthrough)
        self._dismiss_on_outside_tap = _resolve_dismiss_on_outside_tap(self._passthrough, dismiss_on_outside_tap)

        # Handle returned by Overlay.show(); None when the overlay is closed.
        self._handle: Optional["OverlayHandle[Any]"] = None
        self._open_retry_callback: Optional[Callable[[float], None]] = None
        self._handle_monitor_callback: Optional[Callable[[float], None]] = None

        # Single observable drives all open/close state.
        from nuiitivet.observable.value import Observable as _Observable

        self._is_open: "Observable[bool]" = is_open if is_open is not None else _Observable(False)

        self._child = child
        self.add_child(child)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> "Observable[bool]":
        """Observable that controls the open/close state of the popup."""
        return self._is_open

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Subscribe to *is_open* and drive overlay open/close reactively."""
        super().on_mount()
        self.observe(self._is_open, self._on_is_open_changed)

    def on_unmount(self) -> None:
        """Release scheduled callbacks and close overlay during unmount."""
        self._cancel_open_retry()
        self._cancel_handle_monitor()
        self._do_close()
        super().on_unmount()

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------

    def _on_is_open_changed(self, value: bool) -> None:
        if value:
            self._do_open()
        else:
            self._do_close()

    def _do_open(self) -> None:
        """Open the popup overlay or schedule retry until layout rect is ready."""
        if self._handle is not None:
            # Already open.
            return
        opened = self._try_open_now()
        if not opened:
            self._schedule_open_retry()

    def _try_open_now(self) -> bool:
        if self._rect_provider() is None:
            return False
        if self._handle is not None:
            return True

        from nuiitivet.overlay.overlay import Overlay

        position = OverlayPosition.anchored(
            self._rect_provider,
            target_anchor=self._target_anchor,
            content_anchor=self._content_anchor,
            offset=self._offset,
        )
        try:
            overlay = Overlay.of(self, root=True)
        except RuntimeError:
            return False

        self._handle = overlay.show(
            self._content,
            passthrough=self._passthrough,
            dismiss_on_outside_tap=self._dismiss_on_outside_tap,
            position=position,
            transition_spec=self._transition_spec,
        )
        self._cancel_open_retry()
        self._ensure_handle_monitor()
        return True

    def _schedule_open_retry(self) -> None:
        if self._open_retry_callback is not None:
            return

        def _retry(_dt: float) -> None:
            self._open_retry_callback = None
            if getattr(self, "_app", None) is None:
                return
            if not self._is_open.value:
                return
            if self._handle is not None:
                return
            if not self._try_open_now():
                self._schedule_open_retry()

        self._open_retry_callback = _retry
        runtime.clock.schedule_once(_retry, 0.0)

    def _cancel_open_retry(self) -> None:
        callback = self._open_retry_callback
        if callback is None:
            return
        self._open_retry_callback = None
        runtime.clock.unschedule(callback)

    def _ensure_handle_monitor(self) -> None:
        if self._handle_monitor_callback is not None:
            return

        def _monitor(_dt: float) -> None:
            if getattr(self, "_app", None) is None:
                self._cancel_handle_monitor()
                return
            handle = self._handle
            if handle is None:
                self._cancel_handle_monitor()
                return
            if handle.done():
                self._handle = None
                self._cancel_handle_monitor()
                if self._is_open.value:
                    self._on_closed_externally()
                    self._is_open.value = False

        self._handle_monitor_callback = _monitor
        runtime.clock.schedule_interval(_monitor, 1.0 / 60.0)

    def _on_closed_externally(self) -> None:
        """Hook called when the overlay is closed by an external actor.

        Called while ``is_open`` is still ``True``, immediately before it is
        set to ``False`` by the handle monitor.  Subclasses may override to
        react to externally-initiated closes (e.g. ESC, light-dismiss tap).
        The default implementation is a no-op.
        """

    def _cancel_handle_monitor(self) -> None:
        callback = self._handle_monitor_callback
        if callback is None:
            return
        self._handle_monitor_callback = None
        runtime.clock.unschedule(callback)

    def _do_close(self) -> None:
        """Close the popup overlay if it is open."""
        self._cancel_open_retry()
        self._cancel_handle_monitor()
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    # ------------------------------------------------------------------
    # Rect provider for OverlayPosition.anchored()
    # ------------------------------------------------------------------

    def _rect_provider(self) -> Optional[Tuple[int, int, int, int]]:
        """Return the current global layout rect derived from layout state."""
        return self.global_layout_rect

    # ------------------------------------------------------------------
    # Widget overrides
    # ------------------------------------------------------------------

    def preferred_size(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Preferred size follows the child (anchor widget)."""
        return _measure_preferred_size(self._child, max_width=max_width, max_height=max_height)

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        self._child.layout(width, height)
        self._child.set_layout_rect(0, 0, width, height)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.set_last_rect(x, y, width, height)

        # Paint the child (anchor widget).
        rect = self._child.layout_rect
        if rect is not None:
            cx, cy, cw, ch = rect
            self._child.paint(canvas, x + cx, y + cy, cw, ch)

    def hit_test(self, x: int, y: int):
        hit = self._child.hit_test(x, y)
        if hit is not None:
            return hit
        return super().hit_test(x, y)


@dataclass(slots=True)
class PopupModifier(ModifierElement):
    """Modifier that attaches an anchored transient popup overlay to a widget."""

    content: Widget
    is_open: Optional["Observable[bool]"] = None
    passthrough: bool = False
    dismiss_on_outside_tap: bool | None = None
    target_anchor: AlignmentLike = "bottom-left"
    content_anchor: AlignmentLike = "top-left"
    offset: Tuple[float, float] = (0.0, 0.0)
    transition_spec: Optional["TransitionSpec"] = None

    def apply(self, widget: Widget) -> Widget:
        """Wrap *widget* in a :class:`PopupBox`.

        Args:
            widget: The anchor widget to attach the popup to.

        Returns:
            A :class:`PopupBox` wrapping the anchor widget.
        """
        return PopupBox(
            widget,
            self.content,
            is_open=self.is_open,
            passthrough=self.passthrough,
            dismiss_on_outside_tap=self.dismiss_on_outside_tap,
            target_anchor=self.target_anchor,
            content_anchor=self.content_anchor,
            offset=self.offset,
            transition_spec=self.transition_spec,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )


def popup(
    content: Widget,
    *,
    is_open: Optional["Observable[bool]"] = None,
    passthrough: bool = False,
    dismiss_on_outside_tap: bool | None = None,
    target_anchor: AlignmentLike = "bottom-left",
    content_anchor: AlignmentLike = "top-left",
    offset: Tuple[float, float] = (0.0, 0.0),
    transition_spec: Optional["TransitionSpec"] = None,
) -> PopupModifier:
    """Return an anchored popup overlay modifier for the modified widget.

    The overlay is rendered above the widget tree via :meth:`Overlay.show`, so it
    avoids clipping and sits at the top of the Z-order.

    Behaviour is described by the same two input axes the core uses, not by a
    scenario name:

    ==================================================== =========================
    Call                                                 Result
    ==================================================== =========================
    ``popup(x)``                                         block + dismiss (menu)
    ``popup(x, passthrough=True)``                       pass through, no dismiss
    ==================================================== =========================

    Args:
        content: Widget to display as the popup overlay.
        is_open: ``Observable[bool]`` to control open/close state.
            When ``None``, an internal observable is created and exposed via
            :attr:`PopupBox.is_open`. Callers are responsible for toggling it.
        passthrough: Whether input reaches the content behind the popup.
            ``False`` (the default) blocks it, as a menu does; ``True`` lets it
            through, as a toast or tooltip does.
        dismiss_on_outside_tap: Whether an outside tap closes the popup.
            ``None`` (the default) resolves to ``not passthrough``, so each of
            the two legal combinations is spellable with a single flag.
        target_anchor: Reference point on the anchor widget (default
            ``"bottom-left"``).
        content_anchor: Reference point on the content widget (default
            ``"top-left"``).
        offset: Additional ``(dx, dy)`` offset in screen pixels.
        transition_spec: Passed directly to :meth:`Overlay.show` for enter/exit
            animation.

    Returns:
        A :class:`PopupModifier` suitable for :meth:`Widget.modifier`.

    Raises:
        ValueError: When the popup is opened with ``passthrough=True`` and an
            explicit ``dismiss_on_outside_tap=True`` — see issue #508.

    Example::

        # External state control (recommended)
        is_open: Observable[bool] = Observable(False)
        icon_button.modifier(popup(Menu(...), is_open=is_open))

        # Explicit positioning with animation
        icon_button.modifier(
            popup(
                Menu(...),
                target_anchor="bottom-left",
                content_anchor="top-left",
                offset=(0.0, 4.0),
                transition_spec=MaterialTransitions.menu(),
            )
        )
    """
    # Validate at declaration time rather than waiting for the first open.
    _resolve_dismiss_on_outside_tap(bool(passthrough), dismiss_on_outside_tap)
    return PopupModifier(
        content=content,
        is_open=is_open,
        passthrough=passthrough,
        dismiss_on_outside_tap=dismiss_on_outside_tap,
        target_anchor=target_anchor,
        content_anchor=content_anchor,
        offset=offset,
        transition_spec=transition_spec,
    )
