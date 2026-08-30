from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from enum import Enum
import logging
from collections.abc import Awaitable
from typing import Any, Callable, Optional, Sequence, Tuple, Union, cast

from ..input.codes import is_primary_button
from ..input.events import FileDropEvent
from ..input.pointer import PointerEvent, PointerEventType
from ..input.shortcut import Shortcut, ShortcutBinding, ShortcutScope
from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.callbacks import invoke_event_handler, VoidCallback, BoolCallback

# PointerEvent-specific callback aliases (defined here to avoid circular imports).
PointerEventCallback = Union[
    Callable[[PointerEvent], None],
    Callable[[PointerEvent], Awaitable[None]],
]
DragUpdateCallback = Union[
    Callable[[PointerEvent, float, float], None],
    Callable[[PointerEvent, float, float], Awaitable[None]],
]
FileDropCallback = Union[
    Callable[[FileDropEvent], None],
    Callable[[FileDropEvent], Awaitable[None]],
]


class FocusSource(str, Enum):
    """Indicates how a :class:`FocusNode` acquired focus.

    Attributes:
        KEYBOARD: Focus acquired via keyboard navigation (Tab / Shift-Tab).
        POINTER: Focus acquired via a pointer interaction (click-to-focus).
    """

    KEYBOARD = "keyboard"
    POINTER = "pointer"


#: Focus-change callback: receives ``(focused: bool, source: FocusSource)``.
FocusChangeCallback = Union[
    Callable[[bool, FocusSource], None],
    Callable[[bool, FocusSource], Awaitable[None]],
]

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class InteractionState:
    """Shared interaction flags consumed by interactive widgets."""

    hovered: bool = False
    pressed: bool = False
    focused: bool = False
    disabled: bool = False
    dragging: bool = False
    scrolling: bool = False  # TODO スクロールだけは別にするか検討
    selected: bool = False
    checked: bool = False
    toggled_on: bool = False
    pointer_position: Optional[Tuple[float, float]] = None
    press_position: Optional[Tuple[float, float]] = None


class InteractionNode:
    """Base class for interaction logic nodes attached to a Widget (usually InteractionRegion)."""

    def __init__(self) -> None:
        self._owner: Optional["Widget"] = None

    def attach(self, owner: "Widget") -> None:
        self._owner = owner

    def detach(self) -> None:
        self._owner = None

    @property
    def owner(self) -> Optional["Widget"]:
        return self._owner

    @property
    def region(self) -> Optional["InteractionHostMixin"]:
        # Helper to cast owner to InteractionHostMixin if applicable
        if isinstance(self._owner, InteractionHostMixin):
            return self._owner
        return None

    @property
    def state(self) -> InteractionState:
        if isinstance(self._owner, InteractionHostMixin):
            return self._owner.state
        # Fallback: subclasses might override or use explicit state
        return InteractionState()

    def handle_pointer_event(self, event: PointerEvent, bounds: Optional[Sequence[float]] = None) -> bool:
        """Handle a pointer event. Return True if consumed."""
        return False

    def handle_modifier_keys_change(
        self, event: PointerEvent, bounds: Optional[Sequence[float]] = None
    ) -> bool:
        """Handle a modifier-key mask change synthesized at the pointer position.

        Delivered by the :class:`Application` whenever the held modifier-key mask
        changes while a pointer is inside or captured. Returns True if consumed.
        """
        return False

    def handle_file_drop(self, event: FileDropEvent, bounds: Optional[Sequence[float]] = None) -> bool:
        """Handle OS files dropped on the owner. Return True if consumed."""
        return False


class PointerInputNode(InteractionNode):
    """Handles pointer events (hover, click, press) and updates InteractionState."""

    def __init__(
        self,
        owner: Optional[Widget] = None,
        state: Optional[InteractionState] = None,
        hit_test: Optional[Callable[[float, float], bool]] = None,
    ) -> None:
        super().__init__()
        if owner:
            self.attach(owner)
        self._explicit_state = state
        self._hit_test = hit_test
        self._hover_callbacks: list[BoolCallback] = []
        self._click_callbacks: list[VoidCallback] = []
        self._press_callbacks: list[PointerEventCallback] = []
        self._release_callbacks: list[PointerEventCallback] = []
        self._hover_enabled = False
        self._click_enabled = False
        self._any_button = False
        self._active_pointer_id: Optional[int] = None
        self._active_button: Optional[int] = None

    @property
    def state(self) -> InteractionState:
        if self._explicit_state:
            return self._explicit_state
        return super().state

    def enable_hover(self, *, on_change: Optional[BoolCallback] = None) -> None:
        self._hover_enabled = True
        if on_change is not None:
            self._hover_callbacks.append(on_change)

    def enable_click(
        self,
        *,
        on_click: Optional[VoidCallback] = None,
        on_press: Optional[PointerEventCallback] = None,
        on_release: Optional[PointerEventCallback] = None,
        any_button: bool = False,
    ) -> None:
        """Enable click handling on this node.

        Args:
            on_click: Invoked on a completed click inside the bounds.
            on_press: Invoked on press.
            on_release: Invoked on release.
            any_button: When ``True``, secondary and middle buttons activate the
                click too. Meant for dismissal surfaces (an overlay's outside-tap
                layer), not for ordinary controls, which stay primary-only.
        """
        self._click_enabled = True
        self._any_button = bool(any_button)
        # Treat enable_click as a setter.
        # Repeated calls (common in recomposition/modifiers) must not accumulate
        # callbacks, otherwise one click triggers N handlers and can freeze UI.
        if on_click is not None:
            self._click_callbacks = [on_click]
        if on_press is not None:
            self._press_callbacks = [on_press]
        if on_release is not None:
            self._release_callbacks = [on_release]

    def add_hover_listener(self, callback: BoolCallback) -> None:
        """Add a hover listener without replacing existing ones."""
        self._hover_enabled = True
        if callback not in self._hover_callbacks:
            self._hover_callbacks.append(callback)

    def remove_hover_listener(self, callback: BoolCallback) -> None:
        """Remove a previously added hover listener. No-op if not found."""
        try:
            self._hover_callbacks.remove(callback)
        except ValueError:
            pass

    def add_press_listener(self, callback: PointerEventCallback) -> None:
        """Additively register a press listener without replacing existing ones."""
        self._click_enabled = True
        if callback not in self._press_callbacks:
            self._press_callbacks.append(callback)

    def remove_press_listener(self, callback: PointerEventCallback) -> None:
        """Remove a previously added press listener. No-op if not found."""
        try:
            self._press_callbacks.remove(callback)
        except ValueError:
            pass

    def add_release_listener(self, callback: PointerEventCallback) -> None:
        """Additively register a release listener without replacing existing ones."""
        self._click_enabled = True
        if callback not in self._release_callbacks:
            self._release_callbacks.append(callback)

    def remove_release_listener(self, callback: PointerEventCallback) -> None:
        """Remove a previously added release listener. No-op if not found."""
        try:
            self._release_callbacks.remove(callback)
        except ValueError:
            pass

    def _invoke_callback(self, cb: Callable[..., Any], *args: Any, error_key: str, error_msg: str) -> None:
        owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
        invoke_event_handler(cb, *args, error_key=error_key, error_msg=error_msg, owner_name=owner_name)

    def handle_pointer_event(self, event: PointerEvent, bounds: Optional[Sequence[float]] = None) -> bool:
        if self.state.disabled:
            handled = self._clear_state_if_needed()
            return handled

        consumed = False
        if self._hover_enabled:
            consumed = self._handle_hover_event(event, bounds) or consumed
        if self._click_enabled:
            consumed = self._handle_click_event(event, bounds) or consumed
        return consumed

    def _handle_hover_event(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        if event.type == PointerEventType.ENTER:
            self._set_hovered(True, event)
            return True
        if event.type == PointerEventType.LEAVE:
            self._set_hovered(False, event)
            return True
        if event.type in (PointerEventType.HOVER, PointerEventType.MOVE):
            inside = self._point_inside(bounds, event.x, event.y)
            self._set_hovered(inside, event)
            return inside
        return False

    def _handle_click_event(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        if event.type == PointerEventType.PRESS:
            return self._handle_press(event, bounds)
        if event.type == PointerEventType.RELEASE:
            return self._handle_release(event, bounds)
        if event.type == PointerEventType.CANCEL:
            return self._handle_cancel(event)
        return False

    def _handle_press(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        # Only a primary (left / synthetic) button activates a click. Secondary
        # buttons (right / middle) must not press, focus, or capture — unless the
        # node opted into any_button (dismissal surfaces; see issue #506).
        if not self._any_button and not is_primary_button(event.button):
            return False

        inside = True if bounds is None else self._point_inside(bounds, event.x, event.y)
        if not inside:
            return False

        # Click-to-Focus logic
        if self.region:
            self.region.request_focus_from_pointer()

        self._active_pointer_id = event.id
        self._active_button = event.button
        self.state.press_position = (event.x, event.y)
        self._set_pressed(True)
        try:
            if self.owner:
                self.owner.capture_pointer(event, passive=False)
        except Exception:
            owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
            exception_once(
                logger,
                f"pointer_input_capture_pointer_exc:{owner_name}",
                "capture_pointer raised (owner=%s)",
                owner_name,
            )

        for cb in list(self._press_callbacks):
            self._invoke_callback(cb, event, error_key="press_callback", error_msg="Press callback raised")
        return True

    def _handle_release(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        if self._active_pointer_id != event.id:
            return False
        # Ignore a release from a different button than the one that opened the
        # press (all buttons share one pointer id today). A synthetic release
        # (button is None) always matches.
        if event.button is not None and event.button != self._active_button:
            return False
        inside = True if bounds is None else self._point_inside(bounds, event.x, event.y)
        self._set_pressed(False)
        try:
            if self.owner:
                self.owner.release_pointer(event.id)
        except Exception:
            owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
            exception_once(
                logger,
                f"pointer_input_release_pointer_exc:{owner_name}",
                "release_pointer raised (owner=%s)",
                owner_name,
            )
        self._active_pointer_id = None
        self._active_button = None

        for cb in list(self._release_callbacks):
            self._invoke_callback(cb, event, error_key="release_callback", error_msg="Release callback raised")

        if inside:
            self._emit_click()
        return True

    def _handle_cancel(self, event: PointerEvent) -> bool:
        if self._active_pointer_id != event.id:
            return False
        self._set_pressed(False)
        self._active_pointer_id = None
        self._active_button = None
        return True

    def _emit_click(self) -> None:
        for cb in list(self._click_callbacks):
            self._invoke_callback(cb, error_key="click_callback", error_msg="Click callback raised")

    def _set_hovered(self, value: bool, event: PointerEvent) -> bool:
        if self.state.hovered == value:
            if value:
                self.state.pointer_position = (event.x, event.y)
            else:
                self.state.pointer_position = None
            return value
        self.state.hovered = value
        self.state.pointer_position = (event.x, event.y) if value else None
        if self.owner:
            self.owner.invalidate()
        for cb in list(self._hover_callbacks):
            self._invoke_callback(cb, value, error_key="hover_callback", error_msg="Hover callback raised")
        return True

    def _set_pressed(self, value: bool) -> None:
        if self.state.pressed == value:
            return
        self.state.pressed = value
        if self.owner:
            self.owner.invalidate()

    def _clear_state_if_needed(self) -> bool:
        cleared = False
        if self.state.hovered:
            self.state.hovered = False
            self.state.pointer_position = None
            cleared = True
        if self.state.pressed:
            self.state.pressed = False
            cleared = True
        if cleared and self.owner:
            self.owner.invalidate()
        return cleared

    def _point_inside(self, bounds: Optional[Sequence[float]], x: float, y: float) -> bool:
        if self._hit_test:
            return self._hit_test(x, y)
        rect = bounds
        if rect is None and self.owner:
            # Prefer last_rect (paint-time screen coords, accounts for scroll offsets)
            # over global_layout_rect (layout-time coords, ignores scroll).
            rect = getattr(self.owner, "last_rect", None) or getattr(self.owner, "global_layout_rect", None)
        if rect is None:
            return False
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh


class PointerListenerNode(InteractionNode):
    """Raw pointer-stream node backing the ``pointer_input()`` modifier.

    Where :class:`PointerInputNode` collapses press+release into an
    argument-less click and reduces hover to a ``bool``, this node surfaces the
    individual pointer events — press, move, release, enter, leave, scroll —
    each delivering the full :class:`PointerEvent` with widget-local
    coordinates (``local_x`` / ``local_y``) populated. It optionally captures the
    pointer on press so a stroke that runs off the widget keeps delivering move
    and release, and it delivers ``on_modifier_keys_change`` while the pointer is
    inside or captured.

    It is a *separate* node from the default :class:`PointerInputNode`, so it
    composes with ``clickable`` / ``hoverable`` on the same widget without either
    clobbering the other.
    """

    def __init__(
        self,
        *,
        on_press: Optional[PointerEventCallback] = None,
        on_move: Optional[PointerEventCallback] = None,
        on_release: Optional[PointerEventCallback] = None,
        on_enter: Optional[PointerEventCallback] = None,
        on_leave: Optional[PointerEventCallback] = None,
        on_scroll: Optional[PointerEventCallback] = None,
        on_modifier_keys_change: Optional[PointerEventCallback] = None,
        buttons: Optional[Sequence[int]] = None,
        capture: bool = True,
        hit_test: Optional[Callable[[float, float], bool]] = None,
    ) -> None:
        super().__init__()
        self._hit_test = hit_test
        self._active_pointer_id: Optional[int] = None
        self._active_button: Optional[int] = None
        self._inside = False
        self.configure(
            on_press=on_press,
            on_move=on_move,
            on_release=on_release,
            on_enter=on_enter,
            on_leave=on_leave,
            on_scroll=on_scroll,
            on_modifier_keys_change=on_modifier_keys_change,
            buttons=buttons,
            capture=capture,
        )

    def configure(
        self,
        *,
        on_press: Optional[PointerEventCallback] = None,
        on_move: Optional[PointerEventCallback] = None,
        on_release: Optional[PointerEventCallback] = None,
        on_enter: Optional[PointerEventCallback] = None,
        on_leave: Optional[PointerEventCallback] = None,
        on_scroll: Optional[PointerEventCallback] = None,
        on_modifier_keys_change: Optional[PointerEventCallback] = None,
        buttons: Optional[Sequence[int]] = None,
        capture: bool = True,
    ) -> None:
        """Replace the callbacks and options (setter semantics).

        Recomposition re-applies the modifier; replacing rather than appending
        keeps a single handler per event instead of accumulating N copies.
        """
        self._on_press = on_press
        self._on_move = on_move
        self._on_release = on_release
        self._on_enter = on_enter
        self._on_leave = on_leave
        self._on_scroll = on_scroll
        self._on_modifier_keys_change = on_modifier_keys_change
        self._buttons: Optional[frozenset[int]] = frozenset(buttons) if buttons is not None else None
        self._capture = capture

    def _invoke_callback(self, cb: Callable[..., Any], *args: Any, error_key: str, error_msg: str) -> None:
        owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
        invoke_event_handler(cb, *args, error_key=error_key, error_msg=error_msg, owner_name=owner_name)

    def _button_allowed(self, button: Optional[int]) -> bool:
        # A synthetic event (button is None) is never filtered out; explicit
        # button codes are checked against the filter when one is set.
        if self._buttons is None or button is None:
            return True
        return button in self._buttons

    def _resolve_rect(self, bounds: Optional[Sequence[float]]) -> Optional[Sequence[float]]:
        rect = bounds
        if rect is None and self.owner:
            rect = getattr(self.owner, "last_rect", None) or getattr(self.owner, "global_layout_rect", None)
        return rect

    def _with_local(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> PointerEvent:
        rect = self._resolve_rect(bounds)
        if rect is None:
            return event
        return replace(event, local_x=event.x - rect[0], local_y=event.y - rect[1])

    def _point_inside(self, bounds: Optional[Sequence[float]], x: float, y: float) -> bool:
        if self._hit_test:
            return self._hit_test(x, y)
        rect = self._resolve_rect(bounds)
        if rect is None:
            return False
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def handle_pointer_event(self, event: PointerEvent, bounds: Optional[Sequence[float]] = None) -> bool:
        if self.state.disabled:
            if self._active_pointer_id is not None:
                self._active_pointer_id = None
                self._active_button = None
            self._inside = False
            return False

        etype = event.type
        if etype == PointerEventType.PRESS:
            return self._handle_press(event, bounds)
        if etype in (PointerEventType.MOVE, PointerEventType.HOVER):
            return self._handle_move(event, bounds)
        if etype == PointerEventType.RELEASE:
            return self._handle_release(event, bounds)
        if etype == PointerEventType.ENTER:
            return self._handle_enter(event, bounds)
        if etype == PointerEventType.LEAVE:
            return self._handle_leave(event, bounds)
        if etype == PointerEventType.SCROLL:
            return self._handle_scroll(event, bounds)
        if etype == PointerEventType.CANCEL:
            return self._handle_cancel(event)
        return False

    def _handle_press(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        if not self._button_allowed(event.button):
            return False
        if not self._point_inside(bounds, event.x, event.y):
            return False

        self._active_pointer_id = event.id
        self._active_button = event.button
        if self._capture and self.owner:
            try:
                self.owner.capture_pointer(event, passive=False)
            except Exception:
                owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                exception_once(
                    logger,
                    f"pointer_listener_capture_pointer_exc:{owner_name}",
                    "capture_pointer raised (owner=%s)",
                    owner_name,
                )

        if self._on_press:
            self._invoke_callback(
                self._on_press,
                self._with_local(event, bounds),
                error_key="pointer_listener_press",
                error_msg="pointer_input on_press raised",
            )
        return True

    def _handle_move(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        captured = self._capture and self._active_pointer_id is not None and self._active_pointer_id == event.id
        inside = self._point_inside(bounds, event.x, event.y)
        self._inside = inside
        if not captured and not inside:
            return False
        if self._on_move:
            self._invoke_callback(
                self._on_move,
                self._with_local(event, bounds),
                error_key="pointer_listener_move",
                error_msg="pointer_input on_move raised",
            )
        return True

    def _handle_release(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        if self._active_pointer_id != event.id:
            return False
        # Ignore a release from a different button than the one that opened the
        # press (all buttons share one pointer id today). A synthetic release
        # (button is None) always matches.
        if event.button is not None and event.button != self._active_button:
            return False

        if self._capture and self.owner:
            try:
                self.owner.release_pointer(event.id)
            except Exception:
                owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                exception_once(
                    logger,
                    f"pointer_listener_release_pointer_exc:{owner_name}",
                    "release_pointer raised (owner=%s)",
                    owner_name,
                )
        self._active_pointer_id = None
        self._active_button = None

        if self._on_release:
            self._invoke_callback(
                self._on_release,
                self._with_local(event, bounds),
                error_key="pointer_listener_release",
                error_msg="pointer_input on_release raised",
            )
        return True

    def _handle_enter(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        self._inside = True
        if self._on_enter:
            self._invoke_callback(
                self._on_enter,
                self._with_local(event, bounds),
                error_key="pointer_listener_enter",
                error_msg="pointer_input on_enter raised",
            )
            return True
        return False

    def _handle_leave(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        self._inside = False
        if self._on_leave:
            self._invoke_callback(
                self._on_leave,
                self._with_local(event, bounds),
                error_key="pointer_listener_leave",
                error_msg="pointer_input on_leave raised",
            )
            return True
        return False

    def _handle_scroll(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        if not self._point_inside(bounds, event.x, event.y):
            return False
        if self._on_scroll:
            self._invoke_callback(
                self._on_scroll,
                self._with_local(event, bounds),
                error_key="pointer_listener_scroll",
                error_msg="pointer_input on_scroll raised",
            )
            return True
        return False

    def _handle_cancel(self, event: PointerEvent) -> bool:
        if self._active_pointer_id != event.id:
            return False
        self._active_pointer_id = None
        self._active_button = None
        return True

    def handle_modifier_keys_change(
        self, event: PointerEvent, bounds: Optional[Sequence[float]] = None
    ) -> bool:
        if self.state.disabled or self._on_modifier_keys_change is None:
            return False
        # Deliver only while the pointer is inside or captured — never for a
        # widget the pointer is neither over nor holding.
        if self._active_pointer_id is None and not self._inside:
            return False
        self._invoke_callback(
            self._on_modifier_keys_change,
            self._with_local(event, bounds),
            error_key="pointer_listener_modifier_keys_change",
            error_msg="pointer_input on_modifier_keys_change raised",
        )
        return True


class FileDropNode(InteractionNode):
    """File-drop node backing the ``drop_target()`` modifier.

    Receives OS file drops routed through the window (pyglet ``on_file_drop``).
    The dispatch hit-tests the drop point against the tree and bubbles from the
    innermost target, so the node fires only when the drop lands on its owner
    (or a descendant) and no descendant consumed it first.
    """

    def __init__(self, *, on_drop: Optional[FileDropCallback] = None) -> None:
        super().__init__()
        self.configure(on_drop=on_drop)

    def configure(self, *, on_drop: Optional[FileDropCallback] = None) -> None:
        """Replace the callback (setter semantics).

        Recomposition re-applies the modifier; replacing rather than appending
        keeps a single handler instead of accumulating N copies.
        """
        self._on_drop = on_drop

    def _resolve_rect(self, bounds: Optional[Sequence[float]]) -> Optional[Sequence[float]]:
        rect = bounds
        if rect is None and self.owner:
            rect = getattr(self.owner, "last_rect", None) or getattr(self.owner, "global_layout_rect", None)
        return rect

    def handle_file_drop(self, event: FileDropEvent, bounds: Optional[Sequence[float]] = None) -> bool:
        if self.state.disabled:
            return False
        if self._on_drop is None:
            return False
        rect = self._resolve_rect(bounds)
        if rect is not None:
            event = replace(event, local_x=event.x - rect[0], local_y=event.y - rect[1])
        owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
        invoke_event_handler(
            self._on_drop,
            event,
            error_key="file_drop_node_on_drop_exc",
            error_msg="on_drop raised",
            owner_name=owner_name,
        )
        return True


class DraggableNode(InteractionNode):
    """Handles drag gestures (press, move, release)."""

    def __init__(
        self,
        *,
        on_drag_start: Optional[PointerEventCallback] = None,
        on_drag_update: Optional[DragUpdateCallback] = None,
        on_drag_end: Optional[PointerEventCallback] = None,
        hit_test: Optional[Callable[[float, float], bool]] = None,
    ) -> None:
        super().__init__()
        self._on_drag_start = on_drag_start
        self._on_drag_update = on_drag_update
        self._on_drag_end = on_drag_end
        self._hit_test = hit_test
        self._active_pointer_id: Optional[int] = None
        self._active_button: Optional[int] = None
        self._last_pos: Optional[Tuple[float, float]] = None

    def _invoke_callback(self, cb: Callable[..., Any], *args: Any, error_key: str, error_msg: str) -> None:
        owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
        invoke_event_handler(cb, *args, error_key=error_key, error_msg=error_msg, owner_name=owner_name)

    def activate(self, event: PointerEvent) -> None:
        """Programmatically start a drag session.

        Call this when another node (e.g. a track-press handler) has already
        consumed the initial PRESS but subsequent MOVE events should be
        handled by this ``DraggableNode``.

        Args:
            event: The pointer event that initiated the interaction.
        """
        if self._active_pointer_id is not None:
            return
        self._active_pointer_id = event.id
        self._active_button = event.button
        self._last_pos = (event.x, event.y)
        self.state.dragging = True
        self.state.pressed = True

        if self.owner:
            try:
                self.owner.capture_pointer(event)
            except Exception:
                owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                exception_once(
                    logger,
                    f"draggable_activate_capture_exc:{owner_name}",
                    "capture_pointer raised during activate (owner=%s)",
                    owner_name,
                )
            self.owner.invalidate()

        if self._on_drag_start:
            self._invoke_callback(
                self._on_drag_start,
                event,
                error_key="draggable_activate_on_drag_start",
                error_msg="on_drag_start raised during activate",
            )

    def handle_pointer_event(self, event: PointerEvent, bounds: Optional[Sequence[float]] = None) -> bool:
        if self.state.disabled:
            return False

        etype = event.type
        if etype == PointerEventType.PRESS:
            return self._handle_press(event, bounds)
        if etype == PointerEventType.MOVE:
            return self._handle_move(event)
        if etype == PointerEventType.RELEASE:
            return self._handle_release(event)
        if etype == PointerEventType.CANCEL:
            return self._handle_cancel(event)
        return False

    def _handle_press(self, event: PointerEvent, bounds: Optional[Sequence[float]]) -> bool:
        if self._active_pointer_id is not None:
            return False

        # Only a primary (left / synthetic) button starts a drag. A right-drag
        # over e.g. a Slider must not move it.
        if not is_primary_button(event.button):
            return False

        inside = self._point_inside(bounds, event.x, event.y)
        if not inside:
            return False

        self._active_pointer_id = event.id
        self._active_button = event.button
        self._last_pos = (event.x, event.y)
        self.state.dragging = True
        self.state.pressed = True  # Sync with pressed state usually

        if self.owner:
            try:
                self.owner.capture_pointer(event)
            except Exception:
                owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                exception_once(
                    logger,
                    f"draggable_capture_pointer_exc:{owner_name}",
                    "capture_pointer raised (owner=%s)",
                    owner_name,
                )
            self.owner.invalidate()

        if self._on_drag_start:
            self._invoke_callback(
                self._on_drag_start,
                event,
                error_key="draggable_on_drag_start",
                error_msg="on_drag_start raised",
            )
        return True

    def _handle_move(self, event: PointerEvent) -> bool:
        if self._active_pointer_id != event.id:
            return False

        if self._last_pos:
            dx = event.x - self._last_pos[0]
            dy = event.y - self._last_pos[1]
            self._last_pos = (event.x, event.y)
            if self._on_drag_update:
                self._invoke_callback(
                    self._on_drag_update,
                    event,
                    dx,
                    dy,
                    error_key="draggable_on_drag_update",
                    error_msg="on_drag_update raised",
                )
            if self.owner:
                self.owner.invalidate()
        return True

    def _handle_release(self, event: PointerEvent) -> bool:
        if self._active_pointer_id != event.id:
            return False
        # A release from a different button than the one that opened the drag
        # (all buttons share one pointer id) must not end the drag.
        if event.button is not None and event.button != self._active_button:
            return False

        self._end_drag(event)
        return True

    def _handle_cancel(self, event: PointerEvent) -> bool:
        if self._active_pointer_id != event.id:
            return False

        self._end_drag(event)
        return True

    def _end_drag(self, event: PointerEvent) -> None:
        self._active_pointer_id = None
        self._active_button = None
        self._last_pos = None
        self.state.dragging = False
        self.state.pressed = False

        if self.owner:
            try:
                self.owner.release_pointer(event.id)
            except Exception:
                owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                exception_once(
                    logger,
                    f"draggable_release_pointer_exc:{owner_name}",
                    "release_pointer raised (owner=%s)",
                    owner_name,
                )
            self.owner.invalidate()

        if self._on_drag_end:
            self._invoke_callback(
                self._on_drag_end,
                event,
                error_key="draggable_on_drag_end",
                error_msg="on_drag_end raised",
            )

    def _point_inside(self, bounds: Optional[Sequence[float]], x: float, y: float) -> bool:
        if self._hit_test:
            return self._hit_test(x, y)
        rect = bounds
        if rect is None and self.owner:
            # Prefer last_rect (paint-time screen coords, accounts for scroll offsets)
            # over global_layout_rect (layout-time coords, ignores scroll).
            rect = getattr(self.owner, "last_rect", None) or getattr(self.owner, "global_layout_rect", None)
        if rect is None:
            return False
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh


class FocusTraversalBlocker(ABC):
    """Mixin for widgets whose subtree can drop out of the global Tab sequence.

    Inherit it to declare that this widget decides, at runtime, whether Tab
    reaches it and everything below it. While it blocks, the subtree keeps its
    :class:`FocusNode` instances — they are simply not collected as Tab stops —
    and focus currently held inside it is released.

    The property is abstract because blocking is always conditional: a closed
    ``Collapsible``, a disabled ``Clickable``. A widget that always blocks (or
    never does) has no reason to inherit this at all.
    """

    @property
    @abstractmethod
    def blocks_focus_traversal(self) -> bool:
        """Whether Tab must skip this widget and its whole subtree right now."""


class FocusNode(InteractionNode):
    """Handles focus state, traversal, and key events.

    Holding focus and being a Tab stop are separate concerns: ``traversable``
    decides only whether the global Tab sequence stops here. A non-traversable
    node can still be focused programmatically (e.g. by the
    :class:`FocusTraversalPolicy` of an enclosing :class:`FocusScope`), still
    receives key events, and still bubbles them to its ancestors.
    """

    def __init__(
        self,
        *,
        traversable: bool = True,
        on_focus_change: Optional[FocusChangeCallback] = None,
        on_key: Optional[Callable[[str, int], bool]] = None,
        on_key_up: Optional[Callable[[str, int], bool]] = None,
        on_text: Optional[Callable[[str], bool]] = None,
        on_text_motion: Optional[Callable[[int, bool], bool]] = None,
        on_ime_composition: Optional[Callable[[str, int, int], bool]] = None,
        on_ime_commit: Optional[Callable[[], bool]] = None,
    ) -> None:
        super().__init__()
        self.traversable = bool(traversable)
        self._on_focus_change = on_focus_change
        self._on_key = on_key
        self._on_key_up = on_key_up
        self._on_text = on_text
        self._on_text_motion = on_text_motion
        self._on_ime_composition = on_ime_composition
        self._on_ime_commit = on_ime_commit
        self._children: list["FocusNode"] = []
        self._parent: Optional["FocusNode"] = None

    def request_focus(self, source: FocusSource = FocusSource.KEYBOARD) -> None:
        if self.region and hasattr(self.region, "_app") and self.region._app:
            self.region._app.request_focus(self, source)
        else:
            self._set_focused(True, source)

    @property
    def parent(self) -> Optional["FocusNode"]:
        if self._parent:
            return self._parent

        # Bubbling: Find nearest ancestor InteractionRegion with a FocusNode
        if not self.region:
            return None

        # Walk up the widget tree
        # Note: WidgetKernel defines _parent
        current = cast(Widget, self.region)._parent
        while current:
            if isinstance(current, InteractionHostMixin):
                node = current.get_node(FocusNode)
                if node and isinstance(node, FocusNode):
                    return node
            current = getattr(current, "_parent", None)
        return None

    @property
    def accepts_text_input(self) -> bool:
        """Return True if this node, or an ancestor it bubbles to, consumes text.

        The dispatcher asks this before offering a key to the ``key_shortcut``
        tier: a node that takes text will turn a printable key into a character
        through the ``on_text`` route, and must not have that key stolen by a
        shortcut (see #331). It walks the same ``parent`` chain that
        :meth:`handle_text_event` delivers along, so what it reports and where
        the text actually goes cannot drift apart.
        """
        node: Optional["FocusNode"] = self
        while node is not None:
            if node._on_text is not None:
                return True
            node = node.parent
        return False

    def _set_focused(self, value: bool, source: FocusSource = FocusSource.KEYBOARD) -> None:
        if self.state.focused == value:
            # Focus did not move, but re-focusing an already-focused node still
            # says how the user is driving it now (pointer press on a Tab-focused
            # widget), and that must reach the widget.
            if value:
                self.notify_focus_source(source)
            return
        self.state.focused = value
        if self.region:
            cast(Widget, self.region).invalidate()
        if self._on_focus_change:
            owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
            invoke_event_handler(
                self._on_focus_change,
                value,
                source,
                error_key="focus_change_callback",
                error_msg="Focus change callback raised",
                owner_name=owner_name,
            )

    def notify_focus_source(self, source: FocusSource) -> None:
        """Re-announce the focus of an already-focused node under a new ``source``.

        Focus does not have to move for the way the user is driving it to change:
        dragging a slider that Tab focused makes it pointer-driven, and Tab-ing
        within it makes it keyboard-driven again. Widgets key their focus ring off
        that (see ``InteractiveWidget.should_show_focus_ring``), so the source has
        to reach them even when the focused node stays the same.
        """
        if not self.state.focused or self._on_focus_change is None:
            return

        owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
        invoke_event_handler(
            self._on_focus_change,
            True,
            source,
            error_key="focus_source_callback",
            error_msg="Focus change callback raised",
            owner_name=owner_name,
        )

    def handle_key_event(self, key: str, modifier_keys: int) -> bool:
        if self._on_key:
            if self._on_key(key, modifier_keys):
                return True

        # Bubbling: Try parent
        p = self.parent
        if p:
            return p.handle_key_event(key, modifier_keys)
        return False

    def handle_key_release_event(self, key: str, modifier_keys: int) -> bool:
        """Handle a key release, bubbling to ancestors like key press.

        Mirrors :meth:`handle_key_event`: the ``on_key_up`` callback may return
        True to consume the release and stop propagation; otherwise it bubbles to
        the nearest ancestor :class:`FocusNode`.
        """
        if self._on_key_up:
            if self._on_key_up(key, modifier_keys):
                return True

        # Bubbling: Try parent
        p = self.parent
        if p:
            return p.handle_key_release_event(key, modifier_keys)
        return False

    def handle_text_event(self, text: str) -> bool:
        if self._on_text:
            if self._on_text(text):
                return True

        # Bubbling: Try parent
        p = self.parent
        if p:
            return p.handle_text_event(text)
        return False

    def handle_text_motion_event(self, motion: int, select: bool = False) -> bool:
        if self._on_text_motion:
            if self._on_text_motion(motion, select):
                return True

        # Bubbling: Try parent
        p = self.parent
        if p:
            return p.handle_text_motion_event(motion, select)
        return False

    def handle_ime_composition_event(self, text: str, start: int, length: int) -> bool:
        if self._on_ime_composition:
            if self._on_ime_composition(text, start, length):
                return True

        # Bubbling: Try parent
        p = self.parent
        if p:
            return p.handle_ime_composition_event(text, start, length)
        return False

    def handle_ime_commit_event(self) -> bool:
        """Commit a pending IME composition (the window lost the OS focus)."""
        if self._on_ime_commit:
            if self._on_ime_commit():
                return True

        # Bubbling: Try parent
        p = self.parent
        if p:
            return p.handle_ime_commit_event()
        return False


class FocusTraversalPolicy:
    """Enumerates the members of a :class:`FocusScope` and tracks the current one.

    A member is whatever the owner traverses between: a real child
    :class:`FocusNode` (menu items) or a virtual stop the owner keeps for itself
    (slider handle indices). The scope never inspects a member; it only asks the
    policy how many there are, which one is current, and which to make current.
    """

    def members(self) -> Sequence[Any]:
        """Return the scope's members in traversal order."""
        raise NotImplementedError

    def current_index(self) -> int:
        """Return the index of the current member, or -1 if the scope has none."""
        raise NotImplementedError

    def set_current(self, index: int) -> None:
        """Make the member at ``index`` current, focusing it if it is a real node."""
        raise NotImplementedError

    def entry_index(self, backwards: bool) -> int:
        """Return the member Tab enters the scope at: the last one backwards, else the first.

        Which member the group hands the focus to is the policy's decision, not the
        scope's: a radio group is entered at its *selected* radio (WAI-ARIA), while
        a menu or a slider is entered at the end the user came from. Return -1 to
        enter with no member current.
        """
        count = len(self.members())
        if count == 0:
            return -1
        return count - 1 if backwards else 0

    def on_boundary(self, direction: int) -> bool:
        """Handle Tab stepping past the last (``+1``) or first (``-1``) member.

        Return True to consume the key — a menu dismisses itself here. Returning
        False (the default) lets Tab escape the scope and continue through the
        global traversal sequence, which is what sliders and toolbars want.
        """
        return False


class VirtualStopPolicy(FocusTraversalPolicy):
    """Policy whose members are virtual stops owned by the widget.

    The stops are plain indices — the owner decides what they mean (a slider's
    handles, for instance) and keeps the focus on its own :class:`FocusNode`
    while the scope roves between them.
    """

    def __init__(
        self,
        *,
        count: Callable[[], int],
        get_current: Callable[[], int],
        set_current: Callable[[int], None],
        on_boundary: Optional[Callable[[int], bool]] = None,
    ) -> None:
        """Initialize the policy.

        Args:
            count: Returns the current number of stops.
            get_current: Returns the index of the active stop.
            set_current: Makes the stop at the given index active.
            on_boundary: Optional boundary handler; Tab escapes the scope if omitted.
        """
        self._count = count
        self._get_current = get_current
        self._set_current = set_current
        self._on_boundary = on_boundary

    def members(self) -> Sequence[int]:
        return range(max(0, int(self._count())))

    def current_index(self) -> int:
        return int(self._get_current())

    def set_current(self, index: int) -> None:
        self._set_current(int(index))

    def on_boundary(self, direction: int) -> bool:
        if self._on_boundary is not None:
            return bool(self._on_boundary(direction))
        return False


class FocusNodePolicy(FocusTraversalPolicy):
    """Policy whose members are real child :class:`FocusNode` instances.

    Those children are typically non-traversable, so the global Tab sequence
    skips them and this policy is the only thing that moves focus between them.
    """

    def __init__(self, nodes: Callable[[], Sequence["FocusNode"]]) -> None:
        """Initialize the policy.

        Args:
            nodes: Returns the member nodes, in traversal order.
        """
        self._nodes = nodes

    def members(self) -> Sequence["FocusNode"]:
        return list(self._nodes())

    def current_index(self) -> int:
        for idx, node in enumerate(self.members()):
            if node.state.focused:
                return idx
        return -1

    def set_current(self, index: int) -> None:
        members = self.members()
        if 0 <= index < len(members):
            members[index].request_focus(FocusSource.KEYBOARD)


class FocusScope(InteractionNode):
    """Marks a subtree as one focus traversal group.

    The group is the unit Tab enters and leaves: it is a single stop in the
    global sequence, and the :class:`FocusTraversalPolicy` roves between its
    members inside. Tab enters the scope at the member the policy names
    (:meth:`FocusTraversalPolicy.entry_index` — the first one, or the last one on
    Shift+Tab, unless the policy says otherwise). Stepping past the last (or
    before the first) member hits the boundary,
    where the policy either consumes the key (a menu dismisses itself) or lets Tab
    escape to the next stop outside the scope (a slider, a toolbar).

    ``tab_roves`` says which key drives the roving. A slider roves on Tab, so its
    scope reaches the boundary only at the far handle. A menu roves on the arrow
    keys instead (WAI-ARIA); its scope sets ``tab_roves=False`` so that any Tab is
    a boundary — which, for a menu, means dismissal.
    """

    def __init__(self, policy: FocusTraversalPolicy, *, tab_roves: bool = True) -> None:
        """Initialize the scope.

        Args:
            policy: Enumerates the members and tracks which one is current.
            tab_roves: Whether Tab moves between members, or is always a boundary.
        """
        super().__init__()
        self.policy = policy
        self.tab_roves = bool(tab_roves)

    def on_enter(self, backwards: bool = False) -> bool:
        """Make the policy's entry member current — the last one on Shift+Tab, else the first."""
        members = self.policy.members()
        if not members:
            return False

        index = self.policy.entry_index(backwards)
        if not 0 <= index < len(members):
            return False

        self.policy.set_current(index)
        return True

    def move(self, step: int, *, wrap: bool = False) -> bool:
        """Move ``step`` members from the current one. Returns False at the boundary.

        With no current member this enters the scope from the matching end.
        """
        members = self.policy.members()
        if not members:
            return False

        index = self.policy.current_index()
        if index < 0:
            return self.on_enter(backwards=step < 0)

        next_index = index + step
        if wrap:
            next_index %= len(members)
        elif not 0 <= next_index < len(members):
            return False

        self.policy.set_current(next_index)
        return True

    def handle_tab(self, backwards: bool = False) -> bool:
        """Handle a Tab press inside the scope. Returns True if it was consumed."""
        step = -1 if backwards else 1
        if self.tab_roves and self.move(step):
            return True
        return self.policy.on_boundary(step)


class ShortcutNode(InteractionNode):
    """Holds the keyboard-shortcut bindings attached to a widget subtree.

    The :class:`Application` collects these nodes and decides which ones are live
    from each binding's :class:`~nuiitivet.input.shortcut.ShortcutScope`. The node
    itself only stores bindings and reports which of them a keystroke matches.
    """

    def __init__(self) -> None:
        super().__init__()
        self._bindings: dict[Shortcut, ShortcutBinding] = {}

    def bind(self, binding: ShortcutBinding) -> None:
        """Add ``binding``, replacing any existing binding for the same gesture.

        Keying on the gesture keeps re-application idempotent: recomposition
        re-applies the modifier with a fresh callback rather than stacking a
        second binding for the same keystroke.
        """
        self._bindings[binding.shortcut] = binding

    def unbind(self, shortcut: Shortcut) -> None:
        """Remove the binding for ``shortcut``. No-op if it is not bound."""
        self._bindings.pop(shortcut, None)

    @property
    def bindings(self) -> tuple[ShortcutBinding, ...]:
        return tuple(self._bindings.values())

    def match(self, key: str, modifier_keys: int, scope: ShortcutScope) -> Optional[ShortcutBinding]:
        """Return this node's binding for ``key`` + ``modifier_keys`` in ``scope``."""
        for binding in self._bindings.values():
            if binding.scope is scope and binding.shortcut.matches(key, modifier_keys):
                return binding
        return None

    def trigger(self, binding: ShortcutBinding) -> None:
        """Invoke ``binding``'s callback, containing any exception it raises."""
        owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
        invoke_event_handler(
            binding.on_trigger,
            error_key="shortcut_trigger_callback",
            error_msg="Shortcut trigger callback raised",
            owner_name=owner_name,
        )


class InteractionHostMixin:
    """Mixin for widgets that host InteractionNodes."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Note: Subclasses might initialize _state differently or pass it in.
        # If _state is not set by subclass before calling super().__init__ (which is rare for mixins),
        # we should ensure it exists. But usually mixins are initialized after.
        # Here we assume the host will manage _state or we provide a default if missing.
        if not hasattr(self, "_state"):
            self._state = InteractionState()

        self._nodes: list[InteractionNode] = []

        # Default PointerInputNode
        self._pointer_node = PointerInputNode()
        self.add_node(self._pointer_node)

    def add_node(self, node: InteractionNode) -> None:
        # self must be a Widget for attach to work correctly with type hints,
        # but at runtime it just needs to be the owner instance.
        node.attach(cast(Widget, self))
        self._nodes.append(node)

    def get_node(self, node_type: type) -> Optional[InteractionNode]:
        for node in self._nodes:
            if isinstance(node, node_type):
                return node
        return None

    @property
    def state(self) -> InteractionState:
        return self._state

    def _hit_self_opaque(self) -> bool:
        """Interactive hosts catch on their own surface (S = all).

        A widget that hosts interaction nodes is a hit target regardless of
        whether it paints, so pointer events reach its handlers. See issue #448.
        """
        return True

    def enable_hover(self, *, on_change: Optional[BoolCallback] = None) -> None:
        self._pointer_node.enable_hover(on_change=on_change)

    def enable_click(
        self,
        *,
        on_click: Optional[VoidCallback] = None,
        on_press: Optional[PointerEventCallback] = None,
        on_release: Optional[PointerEventCallback] = None,
        any_button: bool = False,
    ) -> None:
        self._pointer_node.enable_click(
            on_click=on_click,
            on_press=on_press,
            on_release=on_release,
            any_button=any_button,
        )

    def enable_file_drop(self, *, on_drop: Optional[FileDropCallback] = None) -> None:
        node = self.get_node(FileDropNode)
        if isinstance(node, FileDropNode):
            node.configure(on_drop=on_drop)
        else:
            self.add_node(FileDropNode(on_drop=on_drop))

    def add_hover_listener(self, callback: BoolCallback) -> None:
        """Add a hover listener without replacing existing ones."""
        self._pointer_node.add_hover_listener(callback)

    def remove_hover_listener(self, callback: BoolCallback) -> None:
        """Remove a previously added hover listener. No-op if not found."""
        self._pointer_node.remove_hover_listener(callback)

    def add_press_listener(self, callback: PointerEventCallback) -> None:
        """Additively register a press listener without replacing existing ones."""
        self._pointer_node.add_press_listener(callback)

    def remove_press_listener(self, callback: PointerEventCallback) -> None:
        """Remove a previously added press listener. No-op if not found."""
        self._pointer_node.remove_press_listener(callback)

    def add_release_listener(self, callback: Callable[[PointerEvent], None]) -> None:
        """Additively register a release listener without replacing existing ones."""
        self._pointer_node.add_release_listener(callback)

    def remove_release_listener(self, callback: Callable[[PointerEvent], None]) -> None:
        """Remove a previously added release listener. No-op if not found."""
        self._pointer_node.remove_release_listener(callback)

    def request_focus_from_pointer(self) -> None:
        """Called by PointerInputNode when a click occurs."""
        focus_node = self.get_node(FocusNode)
        if focus_node and isinstance(focus_node, FocusNode):
            focus_node.request_focus(FocusSource.POINTER)

    def on_pointer_event(self, event: PointerEvent) -> bool:
        # Dispatch to all nodes that can handle pointer events
        consumed = False
        # Prefer last_rect (paint-time screen coords, accounts for scroll offsets)
        # over global_layout_rect (layout-time coords, ignores scroll).
        bounds = getattr(self, "last_rect", None) or getattr(self, "global_layout_rect", None)
        for node in self._nodes:
            consumed = node.handle_pointer_event(event, bounds) or consumed
        return consumed

    def on_file_drop_event(self, event: FileDropEvent) -> bool:
        consumed = False
        bounds = getattr(self, "last_rect", None) or getattr(self, "global_layout_rect", None)
        for node in self._nodes:
            consumed = node.handle_file_drop(event, bounds) or consumed
        return consumed

    def dispatch_modifier_keys_change(self, event: PointerEvent) -> bool:
        """Deliver a modifier-key mask change to this region's nodes.

        Called by the :class:`Application` when the held modifier-key mask
        changes; only :class:`PointerListenerNode` responds, and only while the
        pointer is inside or captured. Returns True if any node consumed it.
        """
        consumed = False
        bounds = getattr(self, "last_rect", None) or getattr(self, "global_layout_rect", None)
        for node in self._nodes:
            consumed = node.handle_modifier_keys_change(event, bounds) or consumed
        return consumed


class InteractionRegion(InteractionHostMixin, Widget):
    """Wrapper widget that exposes a shared InteractionState to its child."""

    def __init__(
        self,
        child: Widget,
        *,
        state: Optional[InteractionState] = None,
        width: SizingLike = None,
        height: SizingLike = None,
        padding: Optional[Tuple[int, int, int, int]] = None,
    ) -> None:
        self._state = state or InteractionState()
        super().__init__(width=width, height=height, padding=padding)
        self.add_child(child)

    # InteractionHostMixin provides add_node, get_node, state property, controller property,
    # enable_hover, enable_click, request_focus_from_pointer, on_pointer_event.

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        if not self.children:
            return
        l, t, r, b = self.padding
        cw = max(0, width - l - r)
        ch = max(0, height - t - b)
        self.children[0].layout(cw, ch)

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:

        self.set_last_rect(x, y, width, height)
        if not self.children:
            return
        cx, cy, cw, ch = self.content_rect(x, y, width, height)
        child = self.children[0]
        child.set_last_rect(cx, cy, cw, ch)
        child.paint(canvas, cx, cy, cw, ch)

    def preferred_size(self, max_width: Optional[int] = None, max_height: Optional[int] = None) -> Tuple[int, int]:
        child_size = (0, 0)
        if self.children:
            child_size = self.children[0].preferred_size(max_width=max_width, max_height=max_height)
        l, t, r, b = self.padding
        width = int(child_size[0]) + int(l) + int(r)
        height = int(child_size[1]) + int(t) + int(b)

        w_dim = self.width_sizing
        h_dim = self.height_sizing

        if w_dim.kind == "fixed":
            width = int(w_dim.value)
        elif max_width is not None:
            width = min(width, int(max_width))

        if h_dim.kind == "fixed":
            height = int(h_dim.value)
        elif max_height is not None:
            height = min(height, int(max_height))

        return (width, height)


def ensure_interaction_region(widget: Widget) -> InteractionRegion:
    if isinstance(widget, InteractionRegion):
        return widget
    return InteractionRegion(
        widget,
        width=widget.width_sizing,
        height=widget.height_sizing,
        padding=widget.padding,
    )


InteractionController = PointerInputNode
