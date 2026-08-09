# Lifecycle Modifiers

Lifecycle modifiers run a callback when a widget enters or leaves the widget tree, so you no longer have to subclass a widget just to override `on_mount()` / `on_unmount()`.

## On Mount / On Unmount

`on_mount()` and `on_unmount()` register a callback on the widget **instance** they are applied to, and fire every time that instance enters or leaves the tree. Since `build()` returns freshly created widgets on every rebuild, a callback attached inside `build()` fires again on each rebuild — it follows the widget instance, not the component that built it.

This screen polls a sensor for as long as the polled `Column` is in the tree. Press *Rebuild* and the log shows the callbacks firing again for the new `Column`; press *Back* and the poll stops for good:

```python
class LiveScreen(nv.ComposableWidget):
    """Polls a sensor for as long as the polled Column is in the tree."""

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
        LOG.add("column unmounted")

    def build(self) -> nv.Widget:
        # Every rebuild produces a *new* Column, so the callbacks fire again:
        # press Rebuild and watch the log.
        return nv.Column(
            children=[
                nv.Text("Live reading (updates every 0.5s):"),
                nv.Text(self.reading),
                nv.Row(
                    children=[
                        nv.Button("Rebuild", on_click=self.rebuild, style=nv.ButtonStyle.text()),
                        nv.Button(
                            "Back",
                            on_click=lambda: nv.Navigator.of(self).pop(),
                            style=nv.ButtonStyle.text(),
                        ),
                    ],
                    gap=10,
                ),
                nv.Text(LOG.text),
            ],
            gap=14,
            cross_alignment="start",
            padding=24,
        ).modifier(nv.on_mount(self._poll) | nv.on_unmount(self._stopped))
```

Callbacks take no arguments and fire at exactly the same point as the corresponding override: `on_mount` right after the widget's `on_mount()` hook and before its children mount, `on_unmount` right after `on_unmount()` and before its children unmount. Multiple callbacks on one widget run in registration order, and an exception in any of them is logged and contained.

> **Note:** These modifiers report tree lifetime and nothing else. A widget on a route that another route has covered stays mounted, so `on_unmount` does **not** fire when a screen merely stops being visible — and no other callback fires at that moment either. There is deliberately no "became foreground / background" hook: drive pause and resume from the side that *causes* the change — the code calling `Navigator.push()`, or the `Observable` behind a `Deck` index — which keeps it explicit what stops and what deliberately keeps running.

### Async callbacks

`on_mount()` also accepts a coroutine function. The framework starts it as a task on mount and **cancels that task on unmount**, which covers polling, subscriptions and async loading without any manual bookkeeping.

That is what `_poll` above relies on: it loops forever and never stops itself. Cancellation is automatic, so there is no need for an `on_unmount()` that tears the task down — put cleanup in a `finally` block instead. The `on_unmount` callback (`_stopped`) fires first, and the task is cancelled immediately afterwards.

`on_unmount()` accepts a coroutine function too, but it is scheduled as a fire-and-forget task that may outlive the widget — and may never complete if the app is shutting down. **Prefer a synchronous callback for cleanup that must complete.**

### Running something only once

Loading a screen's data, or any other initialization that must not repeat, is the common case where "fires on every rebuild" is the wrong behavior. There are two ways to get "once", and which one you need depends on where the work belongs.

**Override `on_mount()` on the composable itself.** A rebuild replaces the *built subtree*, not the host that built it, so the host is never unmounted by its own `rebuild()` and its `on_mount()` runs exactly once per instance. No flag is involved:

```python
class LiveScreen(nv.ComposableWidget):
    def on_mount(self) -> None:
        super().on_mount()
        # Runs once for this LiveScreen. Pressing Rebuild does not run it again.
        self._load_initial_data()
```

This is the right tool for screen-level initialization, and it is what most samples use. Unlike `__init__`, it runs with the widget attached, so `X.of(self)` lookups resolve and a coroutine can be started as a task.

**Use a flag when the callback is attached inside `build()`.** The modifier form registers on whichever widget `build()` just created, and that widget is a new instance on every rebuild — so the callback fires again. Guard it with a flag, and put the flag on something that **outlives the rebuild**:

```python
class SensorVm:
    def __init__(self) -> None:
        self._loaded = False

    async def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        await self._fetch()
```

```python
# self.vm is held by the composable, so the flag survives the rebuild.
nv.Column(children=[...]).modifier(nv.on_mount(self.vm.ensure_loaded))
```

The flag's owner is what defines "once" — a flag stored on the widget the modifier is attached to is discarded along with that widget and buys you nothing. The same rule applies one level up: if a parent's `build()` constructs `LiveScreen()` directly, then a parent rebuild produces a *new* `LiveScreen` and even the override above runs again. Hold such a component in a field, or keep the state it initializes outside the built subtree.
