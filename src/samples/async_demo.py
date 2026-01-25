"""Async/Await integration demo.

This sample demonstrates:
1. Using `async` event handlers (on_click).
2. Using `async with MaterialOverlay.loading()` while awaiting.
3. Updating UI (Observable) from within an async handler without blocking.
4. Awaiting `MaterialOverlay.dialog` results directly.
"""

import asyncio

import nuiitivet as nv
import nuiitivet.material as md


class AsyncDemoApp(nv.ComposableWidget):
    counter = nv.Observable(0)
    status = nv.Observable("Ready")
    progress = nv.Observable(0.0)

    async def _heavy_task(self) -> None:
        """Simulate a heavy async task that updates UI progress."""
        self.status.value = "Processing..."
        self.progress.value = 0.0

        # Simulate 2 seconds of work
        steps = 20
        for i in range(steps):
            await asyncio.sleep(0.1)  # Non-blocking sleep
            self.progress.value = (i + 1) / steps
            self.counter.value += 1  # Update UI state from async context

        self.status.value = "Task Complete"

    async def on_start_task(self) -> None:
        """Handler for the 'Start Task' button."""

        # 1. Show loading dialog using async context manager
        async with md.MaterialOverlay.root().loading():
            await self._heavy_task()

        # 2. Show confirmation dialog and await result
        result = await md.MaterialOverlay.root().dialog(
            md.AlertDialog(
                title=md.Text("Task Finished"),
                content=md.Text(f"Count reached {self.counter.value}. Reset?"),
                actions=[
                    md.TextButton("No", on_click=lambda: md.MaterialOverlay.root().close(False)),
                    md.TextButton("Yes", on_click=lambda: md.MaterialOverlay.root().close(True)),
                ],
            )
        )

        # 3. Handle result
        if bool(result.value):
            self.counter.value = 0
            self.progress.value = 0.0
            self.status.value = "Reset"
            md.MaterialOverlay.root().snackbar("Counter reset!")
        else:
            md.MaterialOverlay.root().snackbar("Kept current count")

    async def on_concurrent_test(self) -> None:
        """Demonstrate that UI is responsive during async sleep."""
        self.status.value = "Waiting 3 seconds..."

        # This await should NOT block the UI.
        # You should be able to click other buttons or see animations while this waits.
        await asyncio.sleep(3)

        self.status.value = "Wait finished!"
        md.MaterialOverlay.root().snackbar("3 seconds passed")

    def on_start_task_click(self) -> None:
        from nuiitivet.widgeting.callbacks import invoke_event_handler

        invoke_event_handler(
            self.on_start_task,
            error_key="async_demo_start_task",
            error_msg="AsyncDemo start task handler raised",
            owner_name=type(self).__name__,
        )

    def on_concurrent_test_click(self) -> None:
        from nuiitivet.widgeting.callbacks import invoke_event_handler

        invoke_event_handler(
            self.on_concurrent_test,
            error_key="async_demo_concurrent_test",
            error_msg="AsyncDemo concurrent test handler raised",
            owner_name=type(self).__name__,
        )

    def build(self) -> nv.Widget:
        status_card = md.FilledCard(
            padding=16,
            child=nv.Column(
                gap=8,
                children=[
                    md.Text(self.status.map(lambda s: f"Status: {s}")),
                    md.Text(self.counter.map(lambda c: f"Counter: {c}")),
                    md.Text(self.progress.map(lambda p: f"Progress: {p:.0%}")),
                ],
            ),
        )

        return nv.Container(
            alignment="center",
            child=nv.Container(
                padding=20,
                width=420,
                child=nv.Column(
                    gap=16,
                    cross_alignment="start",
                    children=[
                        md.Text("Async/Await Demo"),
                        status_card,
                        md.TextButton(
                            "Start Heavy Task (with Overlay.loading)",
                            on_click=self.on_start_task_click,
                        ),
                        md.TextButton(
                            "Test Non-blocking Wait (3s)",
                            on_click=self.on_concurrent_test_click,
                        ),
                        md.TextButton(
                            "Increment Counter Manually",
                            on_click=lambda: setattr(self.counter, "value", self.counter.value + 1),
                        ),
                        md.Text(
                            "Try clicking 'Increment Counter Manually' while 'Test Non-blocking Wait' is running.\n"
                            "The UI should remain responsive.",
                        ),
                    ],
                ),
            ),
        )


if __name__ == "__main__":
    print("Starting Async Demo...")
    # Initialize the app with our demo widget
    app = md.MaterialApp(content=AsyncDemoApp())
    print("App initialized. Running...")
    app.run()
    print("App finished.")
