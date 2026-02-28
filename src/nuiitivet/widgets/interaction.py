from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable, Optional, Sequence, Tuple, cast

from ..input.pointer import PointerEvent, PointerEventType
from ..widgeting.widget import Widget
from ..rendering.sizing import SizingLike
from nuiitivet.common.logging_once import exception_once
from nuiitivet.widgeting.callbacks import invoke_event_handler


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
        self._hover_callbacks: list[Callable[[bool], None]] = []
        self._click_callbacks: list[Callable[[], None]] = []
        self._press_callbacks: list[Callable[[PointerEvent], None]] = []
        self._release_callbacks: list[Callable[[PointerEvent], None]] = []
        self._hover_enabled = False
        self._click_enabled = False
        self._active_pointer_id: Optional[int] = None

    @property
    def state(self) -> InteractionState:
        if self._explicit_state:
            return self._explicit_state
        return super().state

    def enable_hover(self, *, on_change: Optional[Callable[[bool], None]] = None) -> None:
        self._hover_enabled = True
        if on_change is not None:
            self._hover_callbacks.append(on_change)

    def enable_click(
        self,
        *,
        on_click: Optional[Callable[[], None]] = None,
        on_press: Optional[Callable[[PointerEvent], None]] = None,
        on_release: Optional[Callable[[PointerEvent], None]] = None,
    ) -> None:
        self._click_enabled = True
        # Treat enable_click as a setter.
        # Repeated calls (common in recomposition/modifiers) must not accumulate
        # callbacks, otherwise one click triggers N handlers and can freeze UI.
        if on_click is not None:
            self._click_callbacks = [on_click]
        if on_press is not None:
            self._press_callbacks = [on_press]
        if on_release is not None:
            self._release_callbacks = [on_release]

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
        inside = True if bounds is None else self._point_inside(bounds, event.x, event.y)
        if not inside:
            return False

        # Click-to-Focus logic
        if self.region:
            self.region.request_focus_from_pointer()

        self._active_pointer_id = event.id
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
            rect = getattr(self.owner, "global_layout_rect", None)
        if rect is None:
            return False
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh


class DraggableNode(InteractionNode):
    """Handles drag gestures (press, move, release)."""

    def __init__(
        self,
        *,
        on_drag_start: Optional[Callable[[PointerEvent], None]] = None,
        on_drag_update: Optional[Callable[[PointerEvent, float, float], None]] = None,
        on_drag_end: Optional[Callable[[PointerEvent], None]] = None,
        hit_test: Optional[Callable[[float, float], bool]] = None,
    ) -> None:
        super().__init__()
        self._on_drag_start = on_drag_start
        self._on_drag_update = on_drag_update
        self._on_drag_end = on_drag_end
        self._hit_test = hit_test
        self._active_pointer_id: Optional[int] = None
        self._last_pos: Optional[Tuple[float, float]] = None

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
            try:
                self._on_drag_start(event)
            except Exception:
                owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                exception_once(
                    logger,
                    f"draggable_activate_on_drag_start_exc:{owner_name}",
                    "on_drag_start raised during activate (owner=%s)",
                    owner_name,
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

        inside = self._point_inside(bounds, event.x, event.y)
        if not inside:
            return False

        self._active_pointer_id = event.id
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
            try:
                self._on_drag_start(event)
            except Exception:
                owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                exception_once(
                    logger,
                    f"draggable_on_drag_start_exc:{owner_name}",
                    "on_drag_start raised (owner=%s)",
                    owner_name,
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
                try:
                    self._on_drag_update(event, dx, dy)
                except Exception:
                    owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                    exception_once(
                        logger,
                        f"draggable_on_drag_update_exc:{owner_name}",
                        "on_drag_update raised (owner=%s)",
                        owner_name,
                    )
            if self.owner:
                self.owner.invalidate()
        return True

    def _handle_release(self, event: PointerEvent) -> bool:
        if self._active_pointer_id != event.id:
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
            try:
                self._on_drag_end(event)
            except Exception:
                owner_name = type(self.owner).__name__ if self.owner is not None else "<none>"
                exception_once(
                    logger,
                    f"draggable_on_drag_end_exc:{owner_name}",
                    "on_drag_end raised (owner=%s)",
                    owner_name,
                )

    def _point_inside(self, bounds: Optional[Sequence[float]], x: float, y: float) -> bool:
        if self._hit_test:
            return self._hit_test(x, y)
        rect = bounds
        if rect is None and self.owner:
            rect = getattr(self.owner, "global_layout_rect", None)
        if rect is None:
            return False
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh


class FocusNode(InteractionNode):
    """Handles focus state, traversal, and key events."""

    def __init__(
        self,
        *,
        on_focus_change: Optional[Callable[[bool], None]] = None,
        on_key: Optional[Callable[[str, int], bool]] = None,
        on_text: Optional[Callable[[str], bool]] = None,
        on_text_motion: Optional[Callable[[int, bool], bool]] = None,
        on_ime_composition: Optional[Callable[[str, int, int], bool]] = None,
    ) -> None:
        super().__init__()
        self._on_focus_change = on_focus_change
        self._on_key = on_key
        self._on_text = on_text
        self._on_text_motion = on_text_motion
        self._on_ime_composition = on_ime_composition
        self._children: list["FocusNode"] = []
        self._parent: Optional["FocusNode"] = None
        self._wants_tab: Optional[Callable[[int], bool]] = None

    def wants_tab(self, modifiers: int = 0) -> bool:
        """Return True if this node wants to consume Tab internally.

        Composite widgets (e.g. RangeSlider) override this via the
        ``_wants_tab`` callback to intercept Tab before the App moves
        focus to the next node in the traversal list.

        Args:
            modifiers: Keyboard modifier flags (e.g. Shift).
        """
        if self._wants_tab is not None:
            return self._wants_tab(modifiers)
        return False

    def request_focus(self) -> None:
        if self.region and hasattr(self.region, "_app") and self.region._app:
            self.region._app.request_focus(self)
        else:
            self._set_focused(True)

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

    def _set_focused(self, value: bool) -> None:
        if self.state.focused == value:
            return
        self.state.focused = value
        if self.region:
            cast(Widget, self.region).invalidate()
        if self._on_focus_change:
            self._on_focus_change(value)

    def handle_key_event(self, key: str, modifiers: int) -> bool:
        if self._on_key:
            if self._on_key(key, modifiers):
                return True

        # Bubbling: Try parent
        p = self.parent
        if p:
            return p.handle_key_event(key, modifiers)
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

    def enable_hover(self, *, on_change: Optional[Callable[[bool], None]] = None) -> None:
        self._pointer_node.enable_hover(on_change=on_change)

    def enable_click(
        self,
        *,
        on_click: Optional[Callable[[], None]] = None,
        on_press: Optional[Callable[[PointerEvent], None]] = None,
        on_release: Optional[Callable[[PointerEvent], None]] = None,
    ) -> None:
        self._pointer_node.enable_click(on_click=on_click, on_press=on_press, on_release=on_release)

    def request_focus_from_pointer(self) -> None:
        """Called by PointerInputNode when a click occurs."""
        focus_node = self.get_node(FocusNode)
        if focus_node and isinstance(focus_node, FocusNode):
            focus_node.request_focus()

    def on_pointer_event(self, event: PointerEvent) -> bool:
        # Dispatch to all nodes that can handle pointer events
        consumed = False
        bounds = getattr(self, "global_layout_rect", None)
        for node in self._nodes:
            consumed = node.handle_pointer_event(event, bounds) or consumed
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
