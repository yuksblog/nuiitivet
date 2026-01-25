from nuiitivet.widgeting.widget import Widget
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.observable import Observable


class DummyWidget(Widget):
    vm_val = Observable(0)

    def __init__(self):
        super().__init__()
        self.computations = 0

        def compute():
            self.computations += 1
            return self.vm_val.value * 2

        self.computed = Observable.compute(compute)

    def on_pointer_event(self, event):
        self.vm_val.value = 1
        return True

    def on_key_event(self, key, modifiers):
        self.vm_val.value = 2
        return True


def test_pointer_event_auto_batch():
    w = DummyWidget()
    # Initial computation
    assert w.computations == 1

    # Dispatch pointer event
    event = PointerEvent.mouse_event(1, PointerEventType.PRESS, 0, 0)
    w.dispatch_pointer_event(event)

    # After dispatch returns, batch should have flushed.
    # Inside handler: value changed to 1.
    # If batching worked:
    #   Inside handler: computed marked dirty, not recomputed.
    #   Batch exit: computed recomputed.
    # Total computations: 1 (init) + 1 (flush) = 2.

    # If batching DID NOT work:
    #   Inside handler: computed recomputed immediately.
    # Total computations: 1 (init) + 1 (immediate) = 2.

    # Wait, the end result is the same (2).
    # We need to verify it was deferred.
    # We can check this by adding an assertion INSIDE the handler.

    class VerifyingWidget(DummyWidget):
        def on_pointer_event(self, event):
            self.vm_val.value = 10
            # Should be 1 because recomputation is deferred
            assert self.computations == 1, "Computation should be deferred inside handler"
            return True

    w2 = VerifyingWidget()
    assert w2.computations == 1
    w2.dispatch_pointer_event(event)
    assert w2.computations == 2
    assert w2.computed.value == 20


def test_key_event_auto_batch():
    class VerifyingWidget(DummyWidget):
        def on_key_event(self, key, modifiers):
            self.vm_val.value = 20
            assert self.computations == 1, "Computation should be deferred inside handler"
            return True

    w = VerifyingWidget()
    assert w.computations == 1
    w.handle_key_event("A")
    assert w.computations == 2
    assert w.computed.value == 40


def test_button_click_auto_batch():
    """Test that button on_click callbacks are automatically batched via dispatch_pointer_event."""
    from nuiitivet.material.buttons import FilledButton

    class ViewModel:
        count = Observable(0)
        double_count = None

        def __init__(self):
            self.computations = 0

            def compute():
                self.computations += 1
                return self.count.value * 2

            self.double_count = Observable.compute(compute)

    vm = ViewModel()
    assert vm.computations == 1

    clicked = False

    def on_click():
        nonlocal clicked
        clicked = True
        vm.count.value = 5
        assert vm.computations == 1, "Computation should be deferred inside button click handler"

    button = FilledButton("Test", on_click=on_click)

    # Simulate click through dispatch_pointer_event (which wraps in batch)
    press_event = PointerEvent.mouse_event(1, PointerEventType.PRESS, 10, 10)
    button.dispatch_pointer_event(press_event)
    release_event = PointerEvent.mouse_event(1, PointerEventType.RELEASE, 10, 10)
    button.dispatch_pointer_event(release_event)

    assert clicked
    assert vm.computations == 2  # Flushed after click handler
    assert vm.double_count.value == 10


def test_interaction_controller_batching():
    """Test that InteractionController works correctly with dispatch_pointer_event batching."""
    from nuiitivet.widgets.interaction import InteractionController, InteractionState

    class WidgetWithCapture(DummyWidget):
        def capture_pointer(self, event, passive=False):
            return True

        def release_pointer(self, pointer_id):
            return True

    w = WidgetWithCapture()
    assert w.computations == 1

    callback_called = False

    def callback():
        nonlocal callback_called
        callback_called = True
        w.vm_val.value = 100
        # Should be deferred because dispatch_pointer_event wraps in batch
        assert w.computations == 1

    state = InteractionState()
    controller = InteractionController(w, state)
    controller.enable_click(on_click=callback)

    # Override on_pointer_event to delegate to controller
    def on_pointer_event(event):
        return controller.handle_pointer_event(event, (0, 0, 100, 100))

    w.on_pointer_event = on_pointer_event

    # Use dispatch_pointer_event which provides the batch context
    press_event = PointerEvent.mouse_event(1, PointerEventType.PRESS, 10, 10)
    w.dispatch_pointer_event(press_event)

    release_event = PointerEvent.mouse_event(1, PointerEventType.RELEASE, 10, 10)
    w.dispatch_pointer_event(release_event)

    assert callback_called
    assert w.computations == 2  # Flushed after callback
    assert w.computed.value == 200
