# Lifecycle Modifiers

Lifecycle modifiers run a callback when a widget enters or leaves the widget tree, without forcing you to subclass a widget just to override `on_mount()` / `on_unmount()`.

The examples below are excerpts from the runnable sample at `samples/modifiers/lifecycle/live_view.py`.

## On Mount / On Unmount

`on_mount()` and `on_unmount()` register a callback on the widget they are applied to. Unlike most modifiers they do **not** wrap the target in a new widget — the same instance is returned, so no extra node appears in the tree and layout, painting and hit-testing are completely unaffected.

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

The callback takes no arguments. Timing is exactly that of the corresponding override:

- `on_mount` callbacks run right after the widget's `on_mount()` hook, **before** its children are mounted.
- `on_unmount` callbacks run right after the widget's `on_unmount()` hook, **before** its children are unmounted.

Multiple callbacks on the same widget fire in registration order. An exception in one callback is logged and contained — it does not abort the mount, nor prevent the remaining callbacks from running.

## Async Callbacks

`on_mount()` also accepts a coroutine function. The framework starts it as a task on mount and **cancels that task on unmount**, which covers polling, subscriptions and async loading without any manual bookkeeping.

That is what `_poll` above relies on — it loops forever and never stops itself:

```python
    async def _poll(self) -> None:
        # Started as a task on mount, cancelled automatically on unmount.
        LOG.add("poll started")
        try:
            while True:
                self.reading.value = f"{random.uniform(20.0, 25.0):.2f} °C"
                await asyncio.sleep(0.5)
        finally:
            LOG.add("poll cancelled")
```

There is no need to pair this with an `on_unmount()` that cancels the task — cancellation is automatic, and the `finally` block runs when it happens. Note the ordering: the `on_unmount` callback (`_stopped`) fires first, and the task is cancelled immediately afterwards.

`on_unmount()` accepts a coroutine function too, but it is scheduled as a fire-and-forget task that may outlive the widget (and may not complete at all if the app is shutting down). **Prefer a synchronous callback for cleanup that must complete.**

## Caveat: Mount Is Not "Once Per Component"

This is the one thing to internalize before using these modifiers.

When a `ComposableWidget` rebuilds, it unmounts the subtree it previously built and mounts the **freshly created** widget instances returned by the new `build()` call. The widget your modifier was attached to is a new object, so its mount callback runs again.

The sample at `samples/modifiers/lifecycle/rebuild_caveat.py` puts the two side by side. The modifier is attached to the `Column` that `build()` returns, so it fires on every rebuild:

```python
    def _child_mounted(self) -> None:
        # build() returns a new Column on every rebuild, so this runs every time.
        self.modifier_count += 1
        self._update_summary()
```

The `on_mount()` override, on the other hand, belongs to the `ComposableWidget` itself — an instance that survives its own rebuilds — so it fires once:

```python
    def on_mount(self) -> None:
        # Runs once for the lifetime of this RebuildCaveat instance.
        super().on_mount()
        self.override_count += 1
        self._update_summary()
```

Press *Rebuild* in the sample and the two counters diverge: the override stays at 1 while the modifier keeps climbing.

So `on_mount` means "this widget instance entered the tree", **not** "this logical component appeared for the first time". Use the modifier for work tied to the instance's presence in the tree — starting a subscription, beginning a poll, registering with a service — and the override for genuine one-time initialization.

## Relationship to `on_mount()` / `on_unmount()` Overrides

The modifiers do not replace the override hooks — they are a declarative entry point to the same lifecycle.

| | Override (`def on_mount(self)`) | Modifier (`on_mount(cb)`) |
| --- | --- | --- |
| Applies to | The widget you are subclassing | Any widget, including composed ones |
| Requires a subclass | Yes | No |
| Async support | No (write your own task) | Yes, with automatic cancellation |
| Survives a parent rebuild | Yes, if defined on the `ComposableWidget` | Only if the instance itself survives |

Reach for the override when you are already writing a widget class, and for the modifier when you want to attach a callback to a widget you merely composed.
