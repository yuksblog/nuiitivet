"""modeless()/light_dismiss() modifiers – anchored transient overlays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, Tuple

from nuiitivet.layout.alignment import AlignmentLike
from nuiitivet.layout.measure import preferred_size as _measure_preferred_size
from nuiitivet.observable import runtime
from nuiitivet.overlay.overlay_position import AnchoredOverlayPosition
from nuiitivet.rendering.sizing import SizingLike
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget

if TYPE_CHECKING:
    from typing import Any

    from nuiitivet.navigation.transition_spec import TransitionSpec
    from nuiitivet.observable.value import Observable
    from nuiitivet.overlay.overlay_handle import OverlayHandle


class PopupBox(Widget):
    """Wraps an anchor widget and shows a transient popup overlay anchored to it.

    The overlay is rendered by :meth:`Overlay.show_modeless` or
    :meth:`Overlay.show_light_dismiss` (above the widget tree) so it
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
        alignment: AlignmentLike = "bottom-left",
        anchor: AlignmentLike = "top-left",
        offset: Tuple[float, float] = (0.0, 0.0),
        transition_spec: Optional["TransitionSpec"] = None,
        light_dismiss: bool = False,
        width: SizingLike = None,
        height: SizingLike = None,
    ) -> None:
        """Initialize a popup wrapper around an anchor widget.

        Args:
            child: Anchor widget that determines popup attachment point.
            content: Widget rendered inside the popup overlay.
            is_open: Optional external observable controlling open/close state.
            alignment: Reference point on the anchor widget.
            anchor: Reference point on popup content aligned to ``alignment``.
            offset: Additional ``(dx, dy)`` offset in pixels.
            transition_spec: Optional transition passed to ``Overlay.show_modeless``.
            light_dismiss: Whether to close on outside tap using
                ``Overlay.show_light_dismiss``.
            width: Width sizing for this wrapper.
            height: Height sizing for this wrapper.
        """
        super().__init__(width=width, height=height)
        self._content = content
        self._alignment = alignment
        self._anchor = anchor
        self._offset = offset
        self._transition_spec = transition_spec
        self._light_dismiss = bool(light_dismiss)

        # Handle returned by Overlay.show_*(); None when the overlay is closed.
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

        position = AnchoredOverlayPosition.anchored(
            self._rect_provider,
            alignment=self._alignment,
            anchor=self._anchor,
            offset=self._offset,
        )
        try:
            overlay = Overlay.root()
        except RuntimeError:
            return False

        if self._light_dismiss:
            self._handle = overlay.show_light_dismiss(
                self._content,
                position=position,
                transition_spec=self._transition_spec,
            )
        else:
            self._handle = overlay.show_modeless(
                self._content,
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
                    self._is_open.value = False

        self._handle_monitor_callback = _monitor
        runtime.clock.schedule_interval(_monitor, 1.0 / 60.0)

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
    # Rect provider for AnchoredOverlayPosition
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
    alignment: AlignmentLike = "bottom-left"
    anchor: AlignmentLike = "top-left"
    offset: Tuple[float, float] = (0.0, 0.0)
    transition_spec: Optional["TransitionSpec"] = None
    light_dismiss: bool = False

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
            alignment=self.alignment,
            anchor=self.anchor,
            offset=self.offset,
            transition_spec=self.transition_spec,
            light_dismiss=self.light_dismiss,
            width=widget.width_sizing,
            height=widget.height_sizing,
        )


def modeless(
    content: Widget,
    *,
    is_open: Optional["Observable[bool]"] = None,
    alignment: AlignmentLike = "bottom-left",
    anchor: AlignmentLike = "top-left",
    offset: Tuple[float, float] = (0.0, 0.0),
    transition_spec: Optional["TransitionSpec"] = None,
) -> PopupModifier:
    """Return a modeless overlay modifier anchored to the modified widget.

    The overlay is rendered above the widget tree via :meth:`Overlay.show_modeless`, so
    it avoids clipping and sits at the top of the Z-order.

    Args:
        content: Widget to display as the popup overlay.
        is_open: ``Observable[bool]`` to control open/close state.
            When ``None``, an internal observable is created and exposed via
            :attr:`PopupBox.is_open`. Callers are responsible for toggling it.
        alignment: Reference point on the **anchor widget** (default
            ``"bottom-left"``).
        anchor: Reference point on the **content widget** to align to (default
            ``"top-left"``).
        offset: Additional ``(dx, dy)`` offset in screen pixels.
        transition_spec: Passed directly to :meth:`Overlay.show_modeless` for
            enter/exit animation.

    Returns:
        A :class:`PopupModifier` suitable for :meth:`Widget.modifier`.

    Example::

        # External state control (recommended)
        is_open: Observable[bool] = Observable(False)
        icon_button.modifier(modeless(Menu(...), is_open=is_open))

        # Explicit positioning with animation
        icon_button.modifier(
            modeless(
                Menu(...),
                alignment="bottom-left",
                anchor="top-left",
                offset=(0.0, 4.0),
                transition_spec=MaterialTransitions.menu(),
            )
        )
    """
    return PopupModifier(
        content=content,
        is_open=is_open,
        alignment=alignment,
        anchor=anchor,
        offset=offset,
        transition_spec=transition_spec,
    )


def light_dismiss(
    content: Widget,
    *,
    is_open: Optional["Observable[bool]"] = None,
    alignment: AlignmentLike = "bottom-left",
    anchor: AlignmentLike = "top-left",
    offset: Tuple[float, float] = (0.0, 0.0),
    transition_spec: Optional["TransitionSpec"] = None,
) -> PopupModifier:
    """Return a light-dismiss overlay modifier anchored to the modified widget."""
    return PopupModifier(
        content=content,
        is_open=is_open,
        alignment=alignment,
        anchor=anchor,
        offset=offset,
        transition_spec=transition_spec,
        light_dismiss=True,
    )
