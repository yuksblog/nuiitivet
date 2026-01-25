# Threading Model Architecture

This document describes the internal threading architecture of the framework.
For a broader entry point, see [CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md).
For user-facing guidelines, see [docs/guide/threading.md](../guide/threading.md).

## Core Principles

The framework enforces a **Single UI Thread** model.

1. **Main Thread Affinity**: All UI operations (widget creation, tree manipulation, layout, paint) must occur on the main thread (UI thread).
2. **State-Driven Updates**: Cross-thread communication is handled exclusively through reactive state (`Observable`), not by posting arbitrary callbacks.
3. **Coalesced Updates**: High-frequency updates from background threads are automatically coalesced to prevent event loop starvation.

## Architecture

### 1. UI Thread Enforcement

To ensure stability, the framework performs runtime checks in debug mode.

* **Mechanism**: `assert_ui_thread()` helper checks `threading.current_thread() is threading.main_thread()`.
* **Checkpoints**:
  * `Widget.mount()` / `unmount()`
  * `Widget.layout()`
  * `Widget.paint()`
* **Behavior**: Raises `RuntimeError` if violated. These checks are stripped in optimized builds (`python -O`) for performance.

### 2. Cross-Thread State Synchronization

The `Observable` class is the designated bridge between worker threads and the UI thread.

The design and semantics of UI dispatching and coalescing are defined in [OBSERVABLE.md](OBSERVABLE.md).

### 3. Low-Level Primitives

* **Event Loop Integration**: The framework relies on `pyglet.clock` for scheduling tasks on the main thread.
* **Thread Identification**: `threading.main_thread()` is used as the source of truth for the UI thread identity.

## Testing Strategy

Testing concurrent UI logic requires deterministic behavior.

* **Mocking**: Patch the clock used by the observable runtime to capture scheduled tasks.
* **Flushing**: Execute captured tasks synchronously to simulate the UI event loop tick.
* **Verification**: Tests must verify that:
  * `assert_ui_thread` raises correctly on worker threads.
  * Rapid updates are correctly coalesced into a single notification.

See [tests/test_threading_model.py](../../tests/test_threading_model.py) for the current test pattern.

## Design Rationale

### Why not `run_on_ui`?

We deliberately avoid exposing a generic `run_on_ui(callback)` API to users.

* **Reason**: It encourages imperative code and race conditions.
* **Alternative**: By forcing updates through `Observable`, we ensure the UI is always a pure reflection of the application state (Reactive UI pattern).

### Why Coalescing?

Without coalescing, a tight loop in a worker thread updating a progress bar could flood the event loop queue, causing the UI to become unresponsive to input events. Coalescing ensures the UI thread remains responsive.
