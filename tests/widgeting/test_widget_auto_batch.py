import asyncio
from typing import Awaitable, Callable, Optional, Union

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.material.buttons import Button
from nuiitivet.material.text import Text
from nuiitivet.testing import AppHarness
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.input.pointer import PointerEvent, PointerEventType
from nuiitivet.observable import State
from nuiitivet.material import ButtonStyle


class DummyWidget(Widget):
    vm_val = State(0)

    def __init__(self):
        super().__init__()
        self.computations = 0

        def compute():
            self.computations += 1
            return self.vm_val.value * 2

        self.computed = State.compute(compute)

    def on_pointer_event(self, event):
        self.vm_val.value = 1
        return True

    def on_key_event(self, key, modifier_keys):
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
        def on_key_event(self, key, modifier_keys):
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
    from nuiitivet.material.buttons import Button

    class ViewModel:
        count = State(0)
        double_count = None

        def __init__(self):
            self.computations = 0

            def compute():
                self.computations += 1
                return self.count.value * 2

            self.double_count = State.compute(compute)

    vm = ViewModel()
    assert vm.computations == 1

    clicked = False

    def on_click():
        nonlocal clicked
        clicked = True
        vm.count.value = 5
        assert vm.computations == 1, "Computation should be deferred inside button click handler"

    button = Button("Test", on_click=on_click, style=ButtonStyle.filled())

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


class _Counter(ComposableWidget):
    """A button and a label derived from the count.

    The click calls ``start`` from a sync handler, or awaits ``work`` as an
    async handler when ``start`` is ``None``.
    """

    def __init__(self, start: Optional[Callable[["_Counter"], None]]) -> None:
        super().__init__()
        self.count = State(0)
        self.label = self.count.map(lambda n: f"count={n}")
        self.done = asyncio.Event()
        self._start = start

    def bump(self) -> None:
        self.count.value += 1
        self.done.set()

    async def work(self) -> None:
        await asyncio.sleep(0)
        self.bump()

    def _on_click(self) -> None:
        assert self._start is not None
        self._start(self)

    def build(self) -> Widget:
        on_click: Union[Callable[[], None], Callable[[], Awaitable[None]]] = self._on_click
        if self._start is None:
            on_click = self.work
        return Column([Button("go", on_click=on_click, key="go"), Text(self.label)])


def _create_task(counter: _Counter) -> None:
    asyncio.get_running_loop().create_task(counter.work())


def _call_soon(counter: _Counter) -> None:
    asyncio.get_running_loop().call_soon(counter.bump)


def _call_later(counter: _Counter) -> None:
    asyncio.get_running_loop().call_later(0.01, counter.bump)


@pytest.mark.asyncio
@pytest.mark.parametrize("start", [_create_task, _call_soon, _call_later])
async def test_work_a_sync_handler_schedules_updates_the_derived_state(start: Callable[[_Counter], None]) -> None:
    counter = _Counter(start)

    with AppHarness(lambda: counter, size=(300, 200)) as app:
        await app.idle()
        app.click(key="go")
        await asyncio.wait_for(counter.done.wait(), timeout=1.0)
        await app.idle()

    assert counter.count.value == 1
    assert counter.label.value == "count=1"


@pytest.mark.asyncio
async def test_an_async_handler_updates_the_derived_state_after_its_await() -> None:
    counter = _Counter(None)

    with AppHarness(lambda: counter, size=(300, 200)) as app:
        await app.idle()
        app.click(key="go")
        await asyncio.wait_for(counter.done.wait(), timeout=1.0)
        await app.idle()

    assert counter.label.value == "count=1"
