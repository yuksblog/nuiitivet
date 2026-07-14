# Lifecycle Modifiers

Lifecycle modifiers run a callback when a widget enters or leaves the widget tree, without forcing you to subclass a widget just to override `on_mount()` / `on_unmount()`.

## On Mount / On Unmount

`on_mount()` and `on_unmount()` register a callback on the widget they are applied to. Unlike most modifiers they do **not** wrap the target in a new widget — the same instance is returned, so no extra node appears in the tree and layout, painting and hit-testing are completely unaffected.

```python
import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import on_mount, on_unmount
from nuiitivet.observable import Observable


class Dashboard(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.status = Observable("idle")

    def _start(self) -> None:
        self.status.value = "connected"

    def _stop(self) -> None:
        self.status.value = "idle"

    def build(self) -> nv.Widget:
        return nv.Column(
            children=[md.Text(self.status)],
            padding=24,
        ).modifier(on_mount(self._start) | on_unmount(self._stop))
```

The callback takes no arguments. Timing is exactly that of the corresponding override:

- `on_mount` callbacks run right after the widget's `on_mount()` hook, **before** its children are mounted.
- `on_unmount` callbacks run right after the widget's `on_unmount()` hook, **before** its children are unmounted.

Multiple callbacks on the same widget fire in registration order. An exception in one callback is logged and contained — it does not abort the mount, nor prevent the remaining callbacks from running.

## Async Callbacks

`on_mount()` also accepts a coroutine function. The framework starts it as a task on mount and **cancels that task on unmount**, which covers polling, subscriptions and async loading without any manual bookkeeping.

```python
import asyncio

import nuiitivet as nv
import nuiitivet.material as md
from nuiitivet.modifiers import on_mount
from nuiitivet.observable import Observable


class PriceTicker(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.price = Observable("--")

    async def _poll(self) -> None:
        # Cancelled automatically when the widget unmounts.
        while True:
            self.price.value = await fetch_price()
            await asyncio.sleep(5)

    def build(self) -> nv.Widget:
        return nv.Column(
            children=[md.Text(self.price)],
            padding=24,
        ).modifier(on_mount(self._poll))
```

There is no need to pair this with an `on_unmount()` that cancels the task — cancellation is automatic. Write cleanup that must run inside a `finally` block in the coroutine, or in a separate synchronous `on_unmount()` callback.

`on_unmount()` accepts a coroutine function too, but it is scheduled as a fire-and-forget task that may outlive the widget (and may not complete at all if the app is shutting down). **Prefer a synchronous callback for cleanup that must complete.**

## Caveat: Mount Is Not "Once Per Component"

This is the one thing to internalize before using these modifiers.

When a `ComposableWidget` rebuilds, it unmounts the subtree it previously built and mounts the **freshly created** widget instances returned by the new `build()` call. The widget your modifier was attached to is a new object, so its mount callback runs again:

```python
class Screen(nv.ComposableWidget):
    def build(self) -> nv.Widget:
        # A new Column instance on every rebuild → _load() runs on every rebuild.
        return nv.Column(children=[...]).modifier(on_mount(self._load))
```

So `on_mount` means "this widget instance entered the tree", **not** "this logical component appeared for the first time". Use it for work tied to the instance's presence in the tree — starting a subscription, beginning a poll, registering with a service.

For genuine one-time initialization, put the work in the owning `ComposableWidget` instead, since that instance survives rebuilds:

```python
class Screen(nv.ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items = Observable([])

    # Runs once for the lifetime of this Screen instance.
    def on_mount(self) -> None:
        super().on_mount()
        self.load_items()

    def build(self) -> nv.Widget:
        return nv.Column(children=[...])
```

## Relationship to `on_mount()` / `on_unmount()` Overrides

The modifiers do not replace the override hooks — they are a declarative entry point to the same lifecycle.

| | Override (`def on_mount(self)`) | Modifier (`on_mount(cb)`) |
| --- | --- | --- |
| Applies to | The widget you are subclassing | Any widget, including composed ones |
| Requires a subclass | Yes | No |
| Async support | No (write your own task) | Yes, with automatic cancellation |
| Survives a parent rebuild | Yes, if defined on the `ComposableWidget` | Only if the instance itself survives |

Reach for the override when you are already writing a widget class, and for the modifier when you want to attach a callback to a widget you merely composed.
