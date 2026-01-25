import asyncio
import pytest
from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.overlay import Overlay, LoadingDialogIntent
from nuiitivet.overlay.dialogs import PlainLoadingDialog
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgets.interaction import PointerInputNode
from nuiitivet.input.pointer import PointerEvent, PointerEventType, PointerType
from nuiitivet.widgeting.widget import Widget


class MockOverlay(Overlay):
    def __init__(self):
        # Initialize without full App/Widget tree dependency if possible
        # But Overlay inherits ComposableWidget, so it needs some setup.
        # For this test, we just want to test the future logic.
        super().__init__()
        # We need to mock the navigator or just rely on the base implementation
        # which uses a private navigator.


@pytest.mark.asyncio
async def test_overlay_dialog_await():
    # Setup
    overlay = Overlay()
    Overlay.set_root(overlay)

    # Create a dialog handle
    handle = overlay.show(Text("Dialog"), dismiss_on_outside_tap=False)

    # Create a task to close the dialog after a delay
    async def close_later():
        await asyncio.sleep(0.1)
        handle.close("result")

    asyncio.create_task(close_later())

    # Await the handle
    result = await handle

    assert result.value == "result"
    assert not overlay.has_entries()


@pytest.mark.asyncio
async def test_overlay_loading_async_with():
    overlay = MaterialOverlay(intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i.message)})
    Overlay.set_root(overlay)

    async with overlay.loading():
        assert overlay.has_entries()
        await asyncio.sleep(0.1)

    assert not overlay.has_entries()


@pytest.mark.asyncio
async def test_async_event_handler():
    # Setup a widget with async click handler
    class AsyncButton(Widget):
        def __init__(self):
            super().__init__()
            self.clicked = False
            self.interaction = PointerInputNode(self)
            self.interaction.enable_click(on_click=self.on_click)

        async def on_click(self):
            await asyncio.sleep(0.01)
            self.clicked = True

    button = AsyncButton()

    # Simulate click
    event = PointerEvent(id=1, type=PointerEventType.RELEASE, x=0, y=0, pointer_type=PointerType.MOUSE, timestamp=0)

    # We need to simulate the sequence: PRESS -> RELEASE
    # But _emit_click is called on RELEASE if inside.
    # Let's just call _emit_click directly or simulate the events.

    # Simulate PRESS
    press_event = PointerEvent(id=1, type=PointerEventType.PRESS, x=0, y=0, pointer_type=PointerType.MOUSE, timestamp=0)
    button.interaction.handle_pointer_event(press_event)

    # Simulate RELEASE
    button.interaction.handle_pointer_event(event)

    # At this point, the async task should have been scheduled.
    # We yield to the loop to let it run.
    await asyncio.sleep(0.05)

    assert button.clicked
