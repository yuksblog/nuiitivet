"""Application-level routing of modifier-key mask changes (issue #308).

When the held modifier-key mask changes, the app synthesizes a pointer event at
the last known position and routes it to the widget under (or capturing) the
pointer so ``pointer_input(on_modifier_keys_change=...)`` fires even while the
pointer is stationary. The mask is cleared on window deactivation.
"""

from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.runtime.window import Window
from nuiitivet.input.codes import BUTTON_LEFT, MOD_ALT
from nuiitivet.input.pointer import PointerEvent, PointerEventType as T
from nuiitivet.modifiers.pointer_input import pointer_input
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgets.box import Box
from nuiitivet.widgets.interaction import InteractionRegion


class _FakeApp:
    """Minimal host that borrows the real modifier-key routing methods."""

    _set_modifier_keys = Window._set_modifier_keys
    _clear_modifier_keys = Window._clear_modifier_keys
    _dispatch_modifier_keys_change = Window._dispatch_modifier_keys_change

    def __init__(self, hover_target=None):
        self._modifier_keys = 0
        self._last_pointer_pos = None
        self._last_pointer_buttons = 0
        self._pointer_capture_manager = PointerCaptureManager()
        self._primary_pointer_id = 1
        self._last_hover_target = hover_target
        self.invalidated = 0

    def invalidate(self, immediate: bool = False) -> None:
        del immediate
        self.invalidated += 1


def _region(**kw) -> InteractionRegion:
    region = Box(width=Sizing.fixed(100), height=Sizing.fixed(50)).modifier(pointer_input(**kw))
    assert isinstance(region, InteractionRegion)
    region.set_last_rect(0, 0, 100, 50)
    return region


def test_modifier_change_delivered_to_hovered_widget():
    seen = []
    region = _region(on_modifier_keys_change=lambda e: seen.append((e.modifier_keys, e.local_x, e.local_y)))
    region.on_pointer_event(PointerEvent.mouse_event(1, T.ENTER, 10, 15))

    app = _FakeApp(hover_target=region)
    app._last_pointer_pos = (10.0, 15.0)

    app._set_modifier_keys(MOD_ALT)
    assert seen == [(MOD_ALT, 10.0, 15.0)]
    assert app.invalidated == 1


def test_modifier_change_cleared_on_deactivation():
    seen = []
    region = _region(on_modifier_keys_change=lambda e: seen.append(e.modifier_keys))
    region.on_pointer_event(PointerEvent.mouse_event(1, T.ENTER, 10, 15))

    app = _FakeApp(hover_target=region)
    app._last_pointer_pos = (10.0, 15.0)

    app._set_modifier_keys(MOD_ALT)
    # Deactivation (e.g. Cmd+Tab) clears the mask and notifies handlers so no
    # stuck modifier state survives.
    app._clear_modifier_keys()
    assert seen == [MOD_ALT, 0]
    assert app._modifier_keys == 0


def test_no_dispatch_when_mask_unchanged():
    seen = []
    region = _region(on_modifier_keys_change=lambda e: seen.append(1))
    region.on_pointer_event(PointerEvent.mouse_event(1, T.ENTER, 10, 15))

    app = _FakeApp(hover_target=region)
    app._last_pointer_pos = (10.0, 15.0)

    app._set_modifier_keys(MOD_ALT)
    app._set_modifier_keys(MOD_ALT)  # same mask — mirrors a non-modifier keypress
    assert seen == [1]  # exactly one delivery, the second call is a no-op


def test_modifier_change_delivered_while_captured_outside():
    seen = []
    region = _region(on_modifier_keys_change=lambda e: seen.append(e.modifier_keys), capture=True)
    # Press inside so the listener node marks itself active/captured.
    region.on_pointer_event(PointerEvent.mouse_event(1, T.PRESS, 10, 15, button=BUTTON_LEFT))

    app = _FakeApp(hover_target=None)
    app._pointer_capture_manager.capture(
        region, PointerEvent.mouse_event(1, T.PRESS, 10, 15, button=BUTTON_LEFT)
    )
    # Pointer has since moved well outside the widget bounds.
    app._last_pointer_pos = (500.0, 500.0)

    app._set_modifier_keys(MOD_ALT)
    assert seen == [MOD_ALT]
