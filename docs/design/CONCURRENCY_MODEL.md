# Concurrency Model

The UI runs on one thread. A value produced on another thread reaches the UI
through a `State`.

## Overview

Four groups of modules take part.

### Structure

```mermaid
flowchart LR
    thread[The UI Thread]
    marshal[The Marshal]
    workers[The Workers]
    harness[The Harness]
    tree[the widget tree]
    backend[the backend]

    backend -- "set_ui_thread()" --> thread
    backend -- "set_clock(clock)" --> marshal
    tree -- "assert_ui_thread()" --> thread
    marshal -- "is_ui_thread()" --> thread
    workers -- "obs.value = result, off the UI thread" --> marshal
    marshal -- "the subscribers, on the UI thread" --> tree
    harness -- "set_clock(harness)" --> marshal
```

| Module | Role |
| --- | --- |
| The UI Thread | one definition of which thread the UI runs on |
| The Marshal | carries a `State` write from any thread onto the UI thread |
| The Workers | the places work runs away from the UI thread |
| The Harness | runs a test on the UI thread with its own clock |
| the widget tree | the subscribers ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| the backend | names the UI thread and installs the clock ([APP_WINDOW.md](APP_WINDOW.md)) |

### Promises

- A worker thread never touches a widget.
- Every value that crosses from a worker to the UI crosses through a
  `State`.

## The UI Thread

`runtime/threading.py` holds the one answer to "is this the UI thread".

### Structure

```mermaid
flowchart LR
    threading[runtime/threading.py]
    runner[backends/pyglet/runner.py]
    lifecycle[widgeting/widget_lifecycle.py]
    kernel[widgeting/widget_kernel.py]
    value[observable/value.py]
    os[os]

    runner -- "set_ui_thread()" --> threading
    lifecycle -- "assert_ui_thread(), in mount and unmount" --> threading
    kernel -- "assert_ui_thread(), in layout and paint" --> threading
    value -- "is_ui_thread()" --> threading
    os -- "register_at_fork: the child's main thread" --> threading
```

| Module | Role |
| --- | --- |
| `runtime/threading.py` | the cached thread ident; `set_ui_thread`, `is_ui_thread`, `assert_ui_thread` |
| `backends/pyglet/runner.py` | names the thread that runs the frame loop ([APP_WINDOW.md](APP_WINDOW.md)) |
| `widgeting/widget_lifecycle.py` | asserts at mount and unmount ([WIDGET_ARCHITECTURE.md](WIDGET_ARCHITECTURE.md)) |
| `widgeting/widget_kernel.py` | asserts at layout and paint ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `observable/value.py` | asks on every write (The Marshal) |
| `os` | re-seats the ident after a fork |

### Promises

- The UI thread is the main thread until a backend names another.
- The thread that installs the clock is the thread the marshal targets.

## The Marshal

A `State` written off the UI thread notifies on the UI thread.

### Structure

```mermaid
flowchart LR
    value[observable/value.py]
    computed[observable/computed.py]
    batching[observable/batching.py]
    clock[observable/runtime.py]
    threading[runtime/threading.py]
    worker[a worker thread]
    tree[the widget tree]

    worker -- "obs.value = v" --> value
    value & computed & batching -- "is_ui_thread()" --> threading
    value & computed & batching -- "schedule_once(_process_pending_update, 0)" --> clock
    clock -- "the tick, on the UI thread" --> value & computed & batching
    value & computed -- "the subscribers" --> tree
```

| Module | Role |
| --- | --- |
| `observable/value.py` | `State`: holds a pending value and the scheduled flag; applies and notifies |
| `observable/computed.py` | `ComputedState`: the same for a derived value |
| `observable/batching.py` | `BatchContext`: flushes the queued recomputes |
| `observable/runtime.py` | the installed clock ([OBSERVABLE.md](OBSERVABLE.md)) |
| `runtime/threading.py` | the thread test (The UI Thread) |
| a worker thread | writes a value |
| the widget tree | the subscribers |

### Sequence

#### A State is written

```mermaid
sequenceDiagram
    participant W as a worker thread
    participant V as observable/value.py
    participant Th as runtime/threading.py
    participant K as observable/runtime.py
    participant T as the widget tree

    W->>V: obs.value = 1
    V->>Th: is_ui_thread()
    alt on the UI thread
        V->>V: _apply(1), notify
        V->>T: the subscribers, with 1
    else off the UI thread
        V->>V: _pending_value = 1, scheduled
        V->>K: schedule_once(_process_pending_update, 0)
        W->>V: obs.value = 2
        V->>V: _pending_value = 2, already scheduled
        Note over K: the next tick, on the UI thread
        K->>V: _process_pending_update
        V->>V: _apply(2), notify
        V->>T: the subscribers, with 2
    end
```

### Promises

- A write off the UI thread is applied on the next tick. Writes before the
  tick coalesce to the latest value.
- A write on the UI thread applies inline.
- A batch whose `State`s want the UI thread flushes its recomputes there.

## The Workers

Work leaves the UI thread through `switch_map`, a `@worker` or `@server`
function, or a thread the app starts.

### Structure

```mermaid
flowchart LR
    switched[observable/switched.py]
    worker[remote/worker.py]
    function[remote/function.py]
    threads[remote/threads.py]
    process[remote/process.py]
    web[backends/web/]
    callbacks[widgeting/callbacks.py]
    stdthread[threading]
    value[observable/value.py]
    app[the app]

    app -- "source.switch_map(fn)" --> switched
    switched -- "Thread(run), for a plain fn" --> stdthread
    switched -- "spawn_task(run), for a coroutine fn" --> callbacks
    app -- "@worker · @server · await fn(args)" --> worker
    worker -- "is a: RemoteFunction · call(args)" --> function
    function -- "a thread" --> threads
    function -- "a child process, with process=True" --> process
    function -- "a Web Worker, or the server, in a browser" --> web
    switched & function -- "obs.value = result" --> value
    app -- "Thread(target), writing States" --> stdthread
```

| Module | Role |
| --- | --- |
| `observable/switched.py` | `switch_map`: a mapped value whose `fn` takes time to answer ([OBSERVABLE.md](OBSERVABLE.md)) |
| `remote/worker.py` | `@worker`, a function the app awaits that runs away from the UI |
| `remote/function.py` | `RemoteFunction`, `@server`: the declared types and the call |
| `remote/threads.py` | the desktop's threads |
| `remote/process.py` | the desktop's child processes |
| `backends/web/` | the Web Worker and the server call ([WEB_TARGET.md](WEB_TARGET.md)) |
| `widgeting/callbacks.py` | the task a coroutine `fn` runs as ([ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md)) |
| `threading` | the standard library's threads |
| `observable/value.py` | the values the work reports through (The Marshal) |
| the app | starts the work |

### Sequence

#### A source changes before its run has answered

```mermaid
sequenceDiagram
    participant S as the source, observable/value.py
    participant M as observable/switched.py
    participant R as the run, on its thread
    participant O as the result, observable/value.py

    S->>M: value 1
    M->>R: fn(1, token 1)
    S->>M: value 2
    M->>M: cancel token 1
    M->>R: fn(2, token 2)
    R->>M: the answer to 1
    M->>M: token 1 is stale, discarded
    R->>M: the answer to 2
    M->>O: obs.value = the answer to 2
```

### Promises

- A superseded `switch_map` run publishes nothing.
- A `@worker` or `@server` function shares nothing with its caller. Arguments
  and the result are copied.

## The Harness

The pytest plugin runs a test on the UI thread. The harness is the clock.

### Structure

```mermaid
flowchart LR
    plugin[testing/plugin.py]
    hclock[testing/clock.py]
    tasks[testing/_tasks.py]
    callbacks[widgeting/callbacks.py]
    runtime[observable/runtime.py]
    asyncio[asyncio]
    test[the test]

    plugin -- "set_clock(harness) · set_clock(previous)" --> runtime
    runtime -- "schedule_once(fn, delay), while installed" --> hclock
    plugin -- "new_event_loop() · set_event_loop() · run_until_complete" --> asyncio
    plugin -- "_task_observers.add(record) · install_sink · drop_pending_tasks()" --> callbacks
    callbacks -- "record(task) · the contained error" --> tasks
    test -- "await app.idle() · settle()" --> hclock
```

| Module | Role |
| --- | --- |
| `testing/plugin.py` | installs the harness clock, owns the loop, registers the task observer and the error sink |
| `testing/clock.py` | the clock a test pumps by hand |
| `testing/_tasks.py` | `TaskRegistry`: the tasks a harness caused and the failures it contained |
| `widgeting/callbacks.py` | the hooks the harness observes through ([ASYNCIO_INTEGRATION.md](ASYNCIO_INTEGRATION.md)) |
| `observable/runtime.py` | the clock slot ([OBSERVABLE.md](OBSERVABLE.md)) |
| `asyncio` | the loop the harness owns |
| the test | drives the app |

### Promises

- A test body runs on the UI thread.
- A write from a worker lands on the harness clock. Nothing runs it until the
  test pumps the clock.
- An exception a handler raised reaches the test.
