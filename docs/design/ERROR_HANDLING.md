# Error Handling

An exception is caught once, at a boundary. Inside the boundary it
propagates.

## Overview

Three groups of modules take part, with the internal modules and the app's
callbacks at their edges.

### Structure

```mermaid
flowchart LR
    boundaries[The Boundaries]
    log[The Log]
    report[The Report]
    internal[the internal modules]
    app[the app's callbacks]

    internal -- "an exception, propagated" --> boundaries
    app -- "an exception, from a callback" --> boundaries
    boundaries -- "exception_once(logger, key, msg) · exception_once_per_exc(logger, prefix, msg)" --> log
    boundaries -- "report_contained(exc, owner, site)" --> report
```

| Module | Role |
| --- | --- |
| The Boundaries | the entry points from the OS, the backend and the app's callbacks, where an exception is finalised |
| The Log | emits a record once per key |
| The Report | hands a contained exception to whoever is listening |
| the internal modules | `widgeting`, `layout`, `rendering`, `observable` and the rest, which propagate |
| the app's callbacks | user code the framework calls |

### Promises

- A boundary logs and continues, or it raises. An internal catch adds
  context and re-raises.
- `logger.exception` is called at a boundary only.
- `RendererError` passes every boundary.

## The Boundaries

Each entry point catches what the code below it propagated.

### Structure

```mermaid
flowchart LR
    runner[backends/pyglet/runner.py]
    loop[backends/pyglet/event_loop.py]
    events[runtime/app_events.py]
    lifecycle[widgeting/widget_lifecycle.py]
    callbacks[widgeting/callbacks.py]
    notify[observable/_notify.py]
    once[common/logging_once.py]
    internal[the internal modules]
    app[the app's callbacks]

    runner -- "_dispatch_mouse_press · _dispatch_key_press · ..., in a try" --> events
    loop -- "_draw_callback(dt), in a try" --> internal
    events -- "hit_test · the handler chain, in a try" --> callbacks
    lifecycle -- "on_mount() · on_unmount() · child.mount(), in _call_contained" --> app
    callbacks -- "cb(args), in invoke_event_handler" --> app
    notify -- "callback(value), each subscriber in a try" --> app
    runner & loop & events & lifecycle & callbacks & notify -- "exception_once(logger, key, msg) · exception_once_per_exc(logger, prefix, msg)" --> once
```

| Module | Role |
| --- | --- |
| `backends/pyglet/runner.py` | the window's event handlers, each dispatch in its own try ([APP_WINDOW.md](APP_WINDOW.md)) |
| `backends/pyglet/event_loop.py` | the draw callback in a try ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `runtime/app_events.py` | pointer delivery, each step in a try ([INTERACTION_ARCHITECTURE.md](INTERACTION_ARCHITECTURE.md)) |
| `widgeting/widget_lifecycle.py` | the lifecycle hooks and the children's mounts, contained ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| `widgeting/callbacks.py` | `invoke_event_handler`, containing a handler ([ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md)) |
| `observable/_notify.py` | notifies each subscriber, surviving one that raises ([OBSERVABLE.md](OBSERVABLE.md)) |
| `common/logging_once.py` | the record (The Log) |
| the internal modules | propagate |
| the app's callbacks | may raise |

### Sequence

#### A click handler raises

```mermaid
sequenceDiagram
    participant R as backends/pyglet/runner.py
    participant E as runtime/app_events.py
    participant C as widgeting/callbacks.py
    participant A as the app's callbacks
    participant L as common/logging_once.py

    R->>E: _dispatch_mouse_press(x, y)
    E->>C: invoke_event_handler(on_click, ...)
    C->>A: on_click()
    A-->>C: raises
    C->>L: exception_once_per_exc(logger, prefix, msg)
    C->>C: report_contained(exc, owner, site)
    C-->>E: None
    Note over E: the dispatch continues
    Note over R: the frame continues
```

### Promises

- A callback's exception never unwinds the dispatch it was called from.
- `CancelledError` passes through a task boundary.
- A failure in `run_app` before the loop starts raises.

## The Log

`exception_once` and its siblings de-duplicate by a key the call site
chooses.

### Structure

```mermaid
flowchart LR
    once[common/logging_once.py]
    logging[logging]
    capture[dev/runtime_capture.py]
    sites[the boundaries]

    sites -- "debug_once · warning_once · exception_once(logger, key, msg) · exception_once_per_exc(logger, prefix, msg)" --> once
    once -- "logger.debug · warning · exception" --> logging
    capture -- "set_log_once_enabled(enabled)" --> once
```

| Module | Role |
| --- | --- |
| `common/logging_once.py` | the keys seen, the per-exception signature and the kill switch |
| `logging` | the standard library's logger, `nuiitivet` and its children |
| `dev/runtime_capture.py` | switches the de-duplication off for a verbose runtime log ([DEV_BRIDGE.md](DEV_BRIDGE.md)) |
| the boundaries | the call sites (The Boundaries) |

### Promises

- The key is a category and a site, chosen by the call site. It is never the
  message.
- A different failure at the same site is logged again.
- The framework adds no logging handler. It calls no `basicConfig`.
- Logging never raises.

## The Report

`report_contained` tells a listening harness that user code raised.

### Structure

```mermaid
flowchart LR
    callbacks[widgeting/callbacks.py]
    contained[testing/_contained.py]
    tasks[testing/_tasks.py]
    sites[the boundaries]

    sites -- "report_contained(exc, owner, site)" --> callbacks
    callbacks -- "sink(ContainedError)" --> contained
    contained -- "the error, claimed once" --> tasks
```

| Module | Role |
| --- | --- |
| `widgeting/callbacks.py` | `report_contained` and the sink set |
| `testing/_contained.py` | the harness's sink; claims an error and reports it at teardown ([CONCURRENCY_MODEL.md](CONCURRENCY_MODEL.md)) |
| `testing/_tasks.py` | holds the failure until the test reads it |
| the boundaries | the containment sites (The Boundaries) |

### Promises

- A containment site reports.
- A sink never raises.
- A contained exception keeps its type when it reaches a test.
- One containment is one record.
