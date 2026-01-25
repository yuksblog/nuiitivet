# Concurrency & Execution Model

This document is the entry point for concurrency in nuiitivet.

See also:

- [THREADING_MODEL.md](THREADING_MODEL.md)
- [ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md)
- [OBSERVABLE.md](OBSERVABLE.md)

## Terminology

- **UI thread**: The main thread. All UI operations must run here.
- **Worker thread**: Background threads used for CPU-heavy or blocking work.
- **Async task**: An `asyncio` task running on the framework-owned event loop.

## Core rules

1. **Single UI thread**: Widget tree manipulation, layout, and paint must run on the UI thread.
2. **No cross-thread UI callbacks**: Worker threads must not touch widgets directly.
3. **State bridge**: Cross-thread communication is done via `.dispatch_to_ui()` on an observable value.
4. **Async is still UI-thread code**: Async handlers/tasks run on the UI thread and must not block.

## Choosing a concurrency tool

- **CPU-bound work**: Use a worker thread, then publish results through an observable configured with UI dispatch (e.g. `self.progress.dispatch_to_ui()`).
- **I/O-bound work**: Use `asyncio` (`await` network / file I/O), keeping the UI responsive.
- **High-frequency updates**: Prefer `dispatch_to_ui()` with coalescing (last-write-wins per tick).

## Interaction: threads × asyncio

- Async code can update observables directly because it runs on the UI thread.
- Worker threads must use `dispatch_to_ui()` for observables that are bound to the UI.
- If an async handler offloads work to a thread, the thread must communicate back via observables (not UI calls).

## Testing notes

- For `dispatch_to_ui()`, tests typically patch the clock used by the observable runtime and flush scheduled events.
- For async handlers, behavior depends on whether the framework async runtime is active; tests without a running loop may intentionally skip scheduling.
