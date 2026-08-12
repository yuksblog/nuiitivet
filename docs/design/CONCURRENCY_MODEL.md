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
3. **State bridge**: Cross-thread communication goes through an observable value, which marshals a write from any non-UI thread onto the UI thread by default.
4. **Async is still UI-thread code**: Async handlers/tasks run on the UI thread and must not block.

## Choosing a concurrency tool

- **CPU-bound work**: Use a worker thread, then publish results through an observable (`self.progress.value = ...`); the marshal is automatic.
- **I/O-bound work**: Use `asyncio` (`await` network / file I/O), keeping the UI responsive.
- **High-frequency updates**: The default marshal already coalesces (last-write-wins per tick). Pass `dispatch=False` only where every intermediate value is needed and no widget is bound.

## Interaction: threads × asyncio

- Async code can update observables directly because it runs on the UI thread.
- Worker threads may write to any observable bound to the UI; do not opt such an observable out with `dispatch=False`.
- If an async handler offloads work to a thread, the thread must communicate back via observables (not UI calls).

## Testing notes

- For cross-thread writes, tests pump the harness clock (`settle()`), or patch the clock used by the observable runtime and flush scheduled events.
- For async handlers, behavior depends on whether the framework async runtime is active; tests without a running loop may intentionally skip scheduling.
