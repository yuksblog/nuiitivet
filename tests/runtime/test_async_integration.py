"""Async flows end to end: awaited overlays, and an async event handler.

Every wait here goes through the harness. A test that sleeps a fixed amount
instead is asserting that a machine is fast enough, which is true until CI is
busy -- and ``await asyncio.sleep(0)`` is no safer for a flow whose task spawns
another, because then the number of turns needed is an implementation detail of
the code under test.
"""

import asyncio

from nuiitivet.material.overlay import MaterialOverlay
from nuiitivet.overlay import LoadingDialogIntent, Overlay
from nuiitivet.overlay.dialogs import PlainLoadingDialog
from nuiitivet.widgets.interaction import PointerInputNode
from nuiitivet.widgets.text import TextBase as Text
from nuiitivet.widgeting.widget import Widget


async def test_overlay_dialog_await(nuiitivet_app) -> None:
    """``await handle`` resolves with the value the closer passed."""
    overlay = Overlay()
    app = nuiitivet_app(overlay, size=(400, 300))

    handle = overlay.show(Text("Dialog"), backdrop=True)
    await app.idle()
    assert overlay.has_entries()

    handle.close("result")
    result = await handle

    assert result.value == "result"
    await app.wait_for(lambda: not overlay.has_entries())


async def test_overlay_loading_returns_handle(nuiitivet_app) -> None:
    overlay = MaterialOverlay(
        intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i.message)}
    )
    app = nuiitivet_app(overlay, size=(400, 300))

    handle = overlay.loading()
    await app.idle()
    assert overlay.has_entries()

    handle.close(None)
    await app.wait_for(lambda: not overlay.has_entries())


async def test_overlay_while_loading_async_with(nuiitivet_app) -> None:
    """The loading dialog is up for exactly as long as the body runs."""
    overlay = MaterialOverlay(
        intents={LoadingDialogIntent: lambda i: PlainLoadingDialog(i.message)}
    )
    app = nuiitivet_app(overlay, size=(400, 300))
    finished = asyncio.get_running_loop().create_future()

    async def _work() -> None:
        async with overlay.while_loading():
            await finished

    from nuiitivet.widgeting.callbacks import spawn_task

    spawn_task(_work(), owner_name="test.work")
    # idle() returns with the handler parked on `finished`: an app waiting for
    # something only the test can supply is at rest, not busy.
    await app.idle()
    assert overlay.has_entries()

    finished.set_result(None)
    await app.wait_for(lambda: not overlay.has_entries())


async def test_async_event_handler(nuiitivet_mount) -> None:
    """An ``async def`` click handler is scheduled and awaited like production."""
    from nuiitivet.input.pointer import PointerEvent, PointerEventType, PointerType

    class AsyncButton(Widget):
        def __init__(self) -> None:
            super().__init__()
            self.clicked = False
            self.interaction = PointerInputNode(self)
            self.interaction.enable_click(on_click=self.on_click)

        async def on_click(self) -> None:
            await asyncio.sleep(0)
            self.clicked = True

    button = AsyncButton()
    host = nuiitivet_mount(button)
    host.layout(100, 40)

    for event_type in (PointerEventType.PRESS, PointerEventType.RELEASE):
        button.interaction.handle_pointer_event(
            PointerEvent(
                id=1,
                type=event_type,
                x=0,
                y=0,
                pointer_type=PointerType.MOUSE,
                timestamp=0,
            )
        )

    await host.idle()

    assert button.clicked
