# Asyncio Integration

This document focuses on the framework-owned async runtime and event loop integration.
For the overall concurrency entry point, see [CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md).

## Relationship to the threading model

- Async tasks and async event handlers execute on the UI thread.
- The threading model still applies: widgets must only be touched on the UI thread.
- Use worker threads for CPU-heavy or blocking work, and publish results via `.dispatch_to_ui()` on an observable value.

## Concurrency Model

- Single-threaded concurrency.
- The framework owns the async runtime.
- UI callbacks may be sync or async. Async callbacks are scheduled as tasks on the active asyncio loop.

## Runtime Ownership

The framework owns the runtime so application code can use `await` naturally without managing an event loop.

Notes:

- The default desktop runner starts an asyncio event loop internally.
- If an asyncio loop is already running, the pyglet runner may fall back to the synchronous loop. In that case, features that require a running asyncio loop (e.g. awaiting overlay handles) are not available.

## Event Loop Integration (Pyglet)

The pyglet backend uses a custom event loop, `ResponsiveEventLoop`, as the integration point.

- Default mode: asyncio-driven loop (`ResponsiveEventLoop.run()` calls `asyncio.run(self.run_async())`).
- Fallback mode: synchronous loop, used when forced or when an asyncio loop is already running.

### Async-driven loop

`ResponsiveEventLoop.run_async()` pumps pyglet while yielding control back to asyncio:

- Dispatches pyglet events via `platform_loop.step(0.0)` and `window.dispatch_events()`.
- Renders frames based on a draw cadence and explicit invalidation.
- Uses short `await asyncio.sleep(...)` slices (up to 16ms) to keep UI responsive and allow other tasks to run.

This makes `await asyncio.sleep(...)` and other awaited I/O operations cooperative with UI rendering.

### Configuration knobs

- `NUIITIVET_PYGLET_SYNC=1`: force the synchronous pyglet loop.
- `NUIITIVET_PYGLET_MAX_STEP`: caps blocking step time in the synchronous loop.

## Async Event Handlers

UI event handlers may return an awaitable.

- Invocation is centralized in `nuiitivet.widgeting.callbacks.invoke_event_handler`.
- If the handler returns an awaitable, it is wrapped and scheduled with `loop.create_task(...)`.
- The wrapper detaches the current observable batch context via `detach_batch()`.
- Exceptions in async handlers are caught and logged (they do not crash the UI loop).

If no asyncio loop is running (e.g. during some tests or shutdown), async handlers are not scheduled.

## Overlay Awaiting

Overlay APIs are awaitable by using an internal asyncio future per entry.

- `Overlay.show(...)` returns an `OverlayHandle`.
- Awaiting the handle requires a running asyncio loop (`asyncio.get_running_loop()`).
- Closing/dismissing/disposal completes the future with an `OverlayResult`.

### Cancellation and disposal

- If an overlay entry is disposed (e.g. navigation/unmount), the future resolves with reason `DISPOSED`.
- Callers should handle `OverlayResult.reason` rather than relying on cancellation.

## Lifecycle Considerations

### Await guarantees

`await handle` must not hang.

- Removing an entry (without an explicit close) completes the awaitable with `OverlayDismissReason.DISPOSED`.
- Call sites should branch on `OverlayResult.reason`.

### Widget disposal

Dispose ordering and timing should be compatible with async flows:

- Dispose should occur after any exit animation finishes.
- Dispose order is parent  child.

### Observable subscriptions

Async handlers and awaited workflows tend to outlive synchronous scopes.

- Prefer framework helpers (e.g. `bind(...)`) for lifecycle-managed subscriptions.
- Direct `subscribe()` requires explicit disposal by the caller.

## Sample

See `src/samples/async_demo.py` for an end-to-end demonstration:

- `async with MaterialOverlay.root().loading(...)` while awaiting work.
- Awaiting `MaterialOverlay.root().dialog(...)`.
- Updating `Observable` values from async code without `dispatch_to_ui()`.

## Testing

- Tests should prefer running code under the framework-driven async runtime.
- When unit tests run without an active asyncio loop, async handler scheduling may be skipped by design.

## Related

- Archived task document: `docs/design/archive/TASK_ASYNCIO_AWAIT_INTEGRATION.md`
