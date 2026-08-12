# Threading Model

nuiitivet is designed with a strict threading model to ensure stability and predictability.

## The Golden Rule

**All UI operations must happen on the main thread (UI thread).**

This includes:

- Creating widgets
- Modifying widget properties
- Layout and Paint operations
- Mounting and Unmounting widgets

Violating this rule raises a `RuntimeError` in debug mode. The rule applies to
*every* path into the UI — not only Observables, but also asyncio callbacks, raw
`threading.Thread` workers, and anything scheduled outside the main loop.

## Working with Background Threads

You can run expensive work (network requests, heavy computation) on background
threads, but the results must reach the UI on the main thread. An `Observable`
does that for you: a write from any other thread is marshalled onto the UI
thread automatically. See the
[Observable: Thread Safety](../state-management/thread_safety.md) guide for what
that changes, and for the `dispatch=False` opt-out.

For a worked example — progress, a live step display, cancellation, and a
worker that raises — see
[Background Work](../state-management/background_work.md).
