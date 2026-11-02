# Asyncio Integration

The framework owns the asyncio runtime. Application code writes `await`
without managing an event loop.

## Overview

Two groups of modules take part, with the awaitables the framework hands out
at their edges.

### Structure

```mermaid
flowchart LR
    loop[The Loop]
    tasks[The Tasks]
    overlay[overlay/overlay.py]
    navigation[navigation/navigator.py]
    switched[observable/switched.py]
    app[the app]

    app -- "async def on_click(): await ..." --> tasks
    app -- "await overlay.dialog(...) · await handle" --> overlay
    tasks -- "create_task(coro), on the running loop" --> loop
    loop -- "start_pending_tasks(), on entry" --> tasks
    overlay -- "a future per entry · spawn_task(dismiss)" --> tasks
    navigation -- "spawn_task(pop)" --> tasks
    switched -- "spawn_task(run), for a coroutine fn" --> tasks
```

| Module | Role |
| --- | --- |
| The Loop | pumps the platform loop inside an asyncio loop |
| The Tasks | the running tasks, and the work kept until a loop runs |
| `overlay/overlay.py` | an awaitable handle per entry ([OVERLAY.md](OVERLAY.md)) |
| `navigation/navigator.py` | an awaited pop, gated on `will_pop` ([NAVIGATION.md](NAVIGATION.md)) |
| `observable/switched.py` | a coroutine `fn` run as a task ([CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md)) |
| the app | writes `async` handlers and awaits the framework's futures |

### Promises

- An `async` handler runs on the UI thread.
- Every task the framework creates is born in `spawn_task`.

## The Loop

On the desktop `ResponsiveEventLoop.run_async` pumps pyglet inside an
asyncio loop. In a browser the page's own loop drives asyncio.

### Structure

```mermaid
flowchart LR
    loop[backends/pyglet/event_loop.py]
    callbacks[widgeting/callbacks.py]
    pyglet[pyglet]
    asyncio[asyncio]
    runner[backends/pyglet/runner.py]

    runner -- "run()" --> loop
    loop -- "asyncio.run(run_async())" --> asyncio
    loop -- "start_pending_tasks(), on entry · drop_pending_tasks(), under the sync loop" --> callbacks
    loop -- "platform_event_loop.step(0) · dispatch the window events" --> pyglet
    loop -- "await asyncio.sleep(min(timeout, 0.016))" --> asyncio
```

| Module | Role |
| --- | --- |
| `backends/pyglet/event_loop.py` | pumps pyglet inside an asyncio loop, or runs synchronously as a fallback |
| `widgeting/callbacks.py` | the work kept until a loop runs (The Tasks) |
| `pyglet` | the platform events and the windows |
| `asyncio` | the loop the pump runs inside |
| `backends/pyglet/runner.py` | starts the loop ([APP_WINDOW.md](APP_WINDOW.md)) |

### Sequence

#### The pump yields between frames

```mermaid
sequenceDiagram
    participant R as backends/pyglet/runner.py
    participant L as backends/pyglet/event_loop.py
    participant A as asyncio
    participant C as widgeting/callbacks.py
    participant P as pyglet

    R->>L: run()
    L->>A: asyncio.run(run_async())
    L->>C: start_pending_tasks()
    loop each iteration
        L->>P: the window events, a frame when pending
        L->>A: await asyncio.sleep(at most 16 ms)
        Note over A: the other tasks run
        L->>P: step(0)
    end
```

### Promises

- Under the synchronous loop an `await` on a framework future never
  completes.

## The Tasks

`widgeting/callbacks.py` turns an awaitable a handler returned into a task,
or keeps it until a loop runs.

### Structure

```mermaid
flowchart LR
    callbacks[widgeting/callbacks.py]
    batching[observable/batching.py]
    asyncio[asyncio]
    loop[backends/pyglet/event_loop.py]
    runner[backends/pyglet/runner.py]
    window[runtime/window.py]
    harness[testing/plugin.py]
    widgets[the widgets and modifiers]
    app[the app]

    widgets -- "invoke_event_handler(cb, args, error_key, error_msg, owner_name)" --> callbacks
    callbacks -- "cb(args)" --> app
    callbacks -- "detach_batch()" --> batching
    callbacks -- "get_running_loop() · create_task(coro)" --> asyncio
    loop -- "start_pending_tasks()" --> callbacks
    runner & loop & window -- "drop_pending_tasks()" --> callbacks
    harness -- "_task_observers · _error_sinks" --> callbacks
```

| Module | Role |
| --- | --- |
| `widgeting/callbacks.py` | turns a handler's awaitable into a task, or keeps it as a `PendingTask` until a loop runs; the hooks a harness observes through |
| `observable/batching.py` | the batch the task detaches from ([OBSERVABLE.md](OBSERVABLE.md)) |
| `asyncio` | the running loop |
| `backends/pyglet/event_loop.py` | starts the kept work on entry (The Loop) |
| `backends/pyglet/runner.py` | drops the kept work after the loop ([APP_WINDOW.md](APP_WINDOW.md)) |
| `runtime/window.py` | drops the kept work after a headless render ([APP_WINDOW.md](APP_WINDOW.md)) |
| `testing/plugin.py` | observes every task and every contained error ([CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md)) |
| the widgets and modifiers | invoke the app's handlers |
| the app | the handler, sync or async |

### Sequence

#### An async handler is invoked

```mermaid
sequenceDiagram
    participant Wd as the widgets and modifiers
    participant C as widgeting/callbacks.py
    participant A as the app
    participant B as observable/batching.py
    participant L as asyncio

    Wd->>C: invoke_event_handler(cb, ...)
    C->>A: cb(args)
    A-->>C: an awaitable
    alt a loop is running
        C->>L: create_task(wrapper)
        L->>C: the wrapper runs
        C->>B: detach_batch()
        C->>A: await the awaitable
    else no loop yet, under a test harness
        C->>C: close the coroutine, raise UnschedulableAsyncWork
    else no loop yet
        C->>C: PendingTask(coro), kept in spawn order
    end
```

### Promises

- A task detaches from the batch of the dispatch that started it.
- An exception in a task is contained.
- Kept work is dropped where no loop will come.
- Under a test harness, an exception in a task is re-raised.
