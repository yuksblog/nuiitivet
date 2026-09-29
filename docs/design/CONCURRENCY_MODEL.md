# Concurrency Model

The UI runs on one thread. Widget construction, tree mutation, layout and
paint happen there; a worker thread never touches a widget; and every value
that crosses from a worker to the UI crosses through an `Observable`. Async
code is UI-thread code too: an `async` handler runs on the UI thread and must
not block. The event loop that makes `await` possible is in
[ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md).

## One UI Thread

The UI thread is the thread that runs the frame loop, the main thread unless
a backend registers another (`runtime.threading.set_ui_thread`, called by the
pyglet backend when it installs its clock). `is_ui_thread()` compares thread
idents as integers rather than `current_thread() is main_thread()`, because
it runs on the hot path of every observable write and `current_thread()`
costs a dict lookup.

In debug mode `assert_ui_thread()` guards `Widget.mount()` / `unmount()`,
`layout()` and `paint()` and raises `RuntimeError` from a worker; `python -O`
strips the checks.

## The Observable Is the Bridge

An `Observable` written from a worker thread marshals the notification onto
the UI thread, so subscribers run where widgets may be touched whichever
thread set the value. The write is deferred to the next tick and rapid writes
are coalesced: subscribers see the latest value per tick. A write already on
the UI thread applies inline. The semantics, and the `dispatch=False` opt-out
for a value no widget binds, are defined in [OBSERVABLE.md](OBSERVABLE.md).

A generic `run_on_ui(callback)` is not offered. It invites imperative code
that races the state it updates; routing every cross-thread value through an
observable keeps the UI a reflection of application state.

Coalescing exists because a tight loop on a worker updating a progress bar
would otherwise flood the event loop queue and starve input.

## Which Tool

- A value derived asynchronously from another value: `switch_map`. It runs
  the transform on a worker per source change and publishes only the newest
  run's result; a superseded run is discarded, never raced.
- CPU-bound work that needs progress, an explicit start or an explicit cancel,
  none of which `switch_map` expresses: a worker thread that writes
  observables.
- Short work the screen waits for: an `async` handler that awaits it, on a
  thread the runtime owns (`asyncio.to_thread`); the line after the `await`
  is back on the UI thread.
- I/O: an `async` handler that awaits it.
- High-frequency values: the default marshal already coalesces. `dispatch=False`
  only where every intermediate value is needed and no widget is bound.

A worker that a handler starts communicates back through observables, never
through UI calls, and a worker outlives the widget that started it: the
framework did not create the thread and cannot know whether its work still
matters, so stopping it is the application's decision.

## Testing

A test body under the pytest plugin runs on the UI thread, so its writes
apply inline. A write from a worker is queued on the clock and `settle()`
pumps it; outside the harness the clock used by the observable runtime is
patched and its scheduled events flushed. An `async` handler needs a running
loop, so a test without one may skip scheduling by design.
