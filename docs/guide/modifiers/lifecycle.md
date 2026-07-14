# Lifecycle Modifiers

Lifecycle modifiers run a callback when a widget enters or leaves the widget tree, so you no longer have to subclass a widget just to override `on_mount()` / `on_unmount()`.

## On Mount / On Unmount

`on_mount()` and `on_unmount()` register a callback on the widget they are applied to.

This screen polls a sensor while it is on screen, and stops as soon as it is popped:

```python
class LiveScreen(nv.ComposableWidget):
    """Polls a sensor while it is on screen, and stops as soon as it is popped."""

    def __init__(self) -> None:
        super().__init__()
        self.reading = nv.Observable("--")

    async def _poll(self) -> None:
        # Started as a task on mount, cancelled automatically on unmount.
        LOG.add("poll started")
        try:
            while True:
                self.reading.value = f"{random.uniform(20.0, 25.0):.2f} °C"
                await asyncio.sleep(0.5)
        finally:
            LOG.add("poll cancelled")

    def _stopped(self) -> None:
        LOG.add("live view unmounted")

    def build(self) -> nv.Widget:
        return nv.Column(
            children=[
                nv.Text("Live reading (updates every 0.5s):"),
                nv.Text(self.reading),
                nv.Button(
                    "Back",
                    on_click=lambda: nv.Navigator.root().pop(),
                    style=nv.ButtonStyle.text(),
                ),
            ],
            gap=14,
            cross_alignment="start",
            padding=24,
        ).modifier(nv.on_mount(self._poll) | nv.on_unmount(self._stopped))
```

Callbacks take no arguments and fire at exactly the same point as the corresponding override: `on_mount` right after the widget's `on_mount()` hook and before its children mount, `on_unmount` right after `on_unmount()` and before its children unmount. Multiple callbacks on one widget run in registration order, and an exception in any of them is logged and contained.

### Async callbacks

`on_mount()` also accepts a coroutine function. The framework starts it as a task on mount and **cancels that task on unmount**, which covers polling, subscriptions and async loading without any manual bookkeeping.

That is what `_poll` above relies on: it loops forever and never stops itself. Cancellation is automatic, so there is no need for an `on_unmount()` that tears the task down — put cleanup in a `finally` block instead. The `on_unmount` callback (`_stopped`) fires first, and the task is cancelled immediately afterwards.

`on_unmount()` accepts a coroutine function too, but it is scheduled as a fire-and-forget task that may outlive the widget — and may never complete if the app is shutting down. **Prefer a synchronous callback for cleanup that must complete.**

### Mount is not "once per component"

When a `ComposableWidget` rebuilds, it unmounts the subtree it previously built and mounts the **freshly created** instances returned by the new `build()`. The widget your modifier was attached to is a new object, so its mount callback runs again:

```python
    def _child_mounted(self) -> None:
        # build() returns a new Column on every rebuild, so this runs every time.
        self.modifier_count += 1
        self._update_summary()
```

An `on_mount()` override belongs to the `ComposableWidget` itself, which survives its own rebuilds, so it fires once:

```python
    def on_mount(self) -> None:
        # Runs once for the lifetime of this RebuildCaveat instance.
        super().on_mount()
        self.override_count += 1
        self._update_summary()
```

Press *Rebuild* in `samples/modifiers/lifecycle/on_mount_caveat.py` and the two counters diverge. So `on_mount` means "this widget instance entered the tree", **not** "this component appeared for the first time" — if the work must happen once per component, put it in the `ComposableWidget`'s `on_mount()` override instead.
