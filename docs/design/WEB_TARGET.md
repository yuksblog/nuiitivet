# Web Target

One app runs on the desktop and in a browser from the same source. In the
browser, Pyodide runs the app's Python unmodified. A CanvasKit adapter with
the shape of skia-python draws it onto one canvas. The browser's event loop
replaces the pyglet one. The two marks an app makes for the web, `@worker`
and `@server`, run on the desktop too.

## Overview

Four groups of modules take part.

### Structure

```mermaid
flowchart LR
    page[The Page]
    backend[The Backend]
    remote[The Remote Functions]
    server[The Server]
    app[the app, in Pyodide]
    pyodide[Pyodide]
    canvaskit[CanvasKit]

    server -- "index.html · boot.mjs · host.mjs · workers.mjs · worker.mjs · config.json · bundle.zip" --> page
    page -- "prepare() · the events" --> backend
    page -- "runpy.run_path(entry)" --> app
    app -- "App.run()" --> backend
    backend -- "frame() · pick() · download() · writeClipboard()" --> page
    backend -- "Window._dispatch_* · paint" --> app
    backend -- "skia calls, one crossing per draw" --> canvaskit
    page -- "loadPyodide · unpackArchive" --> pyodide
    app -- "await fn(...)" --> remote
    remote -- "postMessage to worker.mjs" --> page
    remote -- "POST nv/call/module.fn" --> server
```

| Module | Role |
| --- | --- |
| The Page | the files the browser loads, the boot that starts Pyodide and the worker, the host that owns the canvas and the input |
| The Backend | the frame loop, the clock, the input translation, the skia adapter and the file dialogs, in Pyodide |
| The Remote Functions | `@worker` and `@server`: a call that leaves the UI thread, on both targets |
| The Server | `run`, `build` and `serve`: the page's files, the stubs for server-only modules, the call route |
| the app | the app's own code, unchanged from the desktop |
| Pyodide | Python in the browser |
| CanvasKit | skia in the browser |

### Promises

- The app does not branch on the target.
- The `@server` functions are the only code that runs on a server.
- A built site is static files.

## The Page

The files the browser loads, and the two it starts: the page's Pyodide and
the worker's.

### Structure

```mermaid
flowchart LR
    index[index.html]
    boot[boot.mjs]
    config[config.json]
    bundle[bundle.zip]
    host[host.mjs]
    workers[workers.mjs]
    worker[worker.mjs]
    entry[the app's entry script]
    runner[backends/web/runner.py]
    side[backends/web/worker.py]
    remote[remote/worker.py]
    pyodide[Pyodide]
    canvaskit[CanvasKit]

    index -- "loads" --> boot
    boot -- "fetch" --> config & bundle
    boot -- "loadPyodide · unpackArchive" --> pyodide
    boot -- "CanvasKitInit" --> canvaskit
    boot -- "startWorkers(config), when config names a worker module" --> workers
    workers -- "new Worker · postMessage(init · call) · terminate" --> worker
    worker -- "loadPyodide · fetch the same zip · unpackArchive" --> pyodide
    worker -- "prepare(modules) · handle(id, name, values)" --> side
    boot -- "installHost(CK, canvas, input, fonts)" --> host
    boot -- "prepare()" --> runner
    boot -- "runpy.run_path(entry, __main__)" --> entry
    host -- "onPointer · onWheel · onKey · onText · onCompose · onPaste · onResize" --> runner
    remote -- "NV_WORKERS.start() · handle.post · handle.end" --> workers
```

| Module | Role |
| --- | --- |
| `index.html` | the canvas, the unseen input element, the script tag for `boot.mjs` |
| `boot.mjs` | starts the worker, loads the runtimes, the zip and the fonts in parallel, unpacks the zip, installs the host, runs the entry |
| `config.json` | where Pyodide and CanvasKit are, the Pyodide packages the app imports and where their wheels are, the fonts, the entry, the modules that hold a `@worker` function |
| `bundle.zip` | the framework under `lib/` and the app's directory under `app/` |
| `host.mjs` | owns the canvas, the WebGL surface, the input element, the clipboard, the file picker and the download |
| `workers.mjs` | starts Web Workers on request and relays their messages |
| `worker.mjs` | a second Pyodide that imports the worker modules and runs calls |
| the app's entry script | the app's `main()`, run as `__main__` |
| `backends/web/runner.py` | the backend the page hands the events to (The Backend) |
| `backends/web/worker.py` | the worker's side of a call (The Remote Functions) |
| `remote/worker.py` | the pool that asks the page for workers (The Remote Functions) |
| Pyodide | Python in the browser |
| CanvasKit | skia in the browser |

### Sequence

#### The page boots

```mermaid
sequenceDiagram
    participant B as boot.mjs
    participant Wk as workers.mjs
    participant P as Pyodide
    participant CK as CanvasKit
    participant H as host.mjs
    participant R as runner.py
    participant E as the app's entry script

    B->>B: fetch config.json
    opt config names a worker module
        B->>Wk: startWorkers(config)
    end
    par
        B->>B: import pyodide.mjs
    and
        B->>B: fetch bundle.zip
    and
        B->>B: fetch the fonts and the icon font
    end
    B->>P: loadPyodide
    B->>CK: CanvasKitInit
    B->>P: unpackArchive(bundle, /nuiitivet)
    B->>H: installHost(CK, canvas, input, fonts)
    B->>R: prepare()
    B->>E: runpy.run_path(entry, run_name="__main__")
    E->>R: App.run() → run_app(app), returns
    Note over R: the module keeps the app, and the browser's loop drives it
```

### Promises

- Every URL in the page is relative to the page.
- A development page loads the runtimes from a CDN. A built site carries
  them, with the licences of everything it redistributes.

## The Backend

The backend turns the page's events into the window's dispatch calls, draws
a frame when one is asked for, and keeps time on the browser's loop.

### Structure

```mermaid
flowchart LR
    runner[backends/web/runner.py]
    clock[backends/web/clock.py]
    input[backends/web/input.py]
    adapter[backends/web/skia.py]
    dialogs[platform/file_dialog_browser.py]
    pacer[runtime/gc_pacing.py]
    idle[widgeting/idle_work.py]
    host[host.mjs]
    window[runtime/window.py]
    browser[the browser]
    pyodide[Pyodide]
    canvaskit[CanvasKit]

    host -- "onPointer · onWheel · onKey · onText · onCompose · onPaste · onResize" --> runner
    runner -- "button_code · buttons_mask · wheel_steps · key_name" --> input
    runner -- "_dispatch_mouse_* · _dispatch_key_* · _dispatch_text · _dispatch_ime_composition · _flush_frame_queues · layout · paint" --> window
    runner -- "tick()" --> clock
    clock -- "_request_frame()" --> runner
    clock -- "setTimeout · clearTimeout" --> browser
    runner -- "requestAnimationFrame · setTimeout, for the idle call after a frame" --> browser
    runner -- "before_frame() · after_frame(now) · idle(now)" --> pacer
    runner -- "run_idle_work(budget)" --> idle
    window -- "Paint · Path · TextBlob · Picture …" --> adapter
    adapter -- "the matrix once per run of draws, geometry and paint state as numbers" --> canvaskit
    runner -- "frame() · placeInput · writeClipboard" --> host
    dialogs -- "pick(accept, multiple, directory) · download(name, bytes)" --> host
    dialogs -- "a fresh directory, the files copied in" --> pyodide
```

| Module | Role |
| --- | --- |
| `backends/web/runner.py` | `_Loop`: requests a frame on an invalidation, a resize or a due callback; dispatches the events; draws |
| `backends/web/clock.py` | `BrowserClock`: keeps the deadlines; asks for a frame or a `setTimeout`; fires what is due on `tick()` |
| `backends/web/input.py` | translates buttons, wheel deltas and key names once, at the host boundary |
| `backends/web/skia.py` | the `skia` module the rendering code imports in the browser |
| `platform/file_dialog_browser.py` | the file picker, and a download in place of a save dialog |
| `runtime/gc_pacing.py` | `GcPacer`: holds the collector for the page's life; collects on the timer after a frame ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `widgeting/idle_work.py` | the tasks the timer after a frame runs ([RENDERING_PIPELINE.md](RENDERING_PIPELINE.md)) |
| `host.mjs` | the canvas, the input element, the clipboard, the picker, the download (The Page) |
| `runtime/window.py` | the dispatch methods and the paint the pyglet backend also calls ([APP_WINDOW.md](APP_WINDOW.md)) |
| the browser | `requestAnimationFrame` and `setTimeout` |
| Pyodide | the page's file system, where a picked or saved file lives |
| CanvasKit | the WebGL surface the adapter draws on |

### Sequence

#### A frame is requested and drawn

```mermaid
sequenceDiagram
    participant W as runtime/window.py
    participant L as runner.py
    participant C as clock.py
    participant Br as the browser
    participant H as host.mjs
    participant A as skia.py

    alt an invalidation, or a resize
        W->>L: request_draw()
    else a callback is due within a frame
        C->>L: _request_frame()
    end
    L->>Br: requestAnimationFrame, once until it fires
    Br->>L: _frame(timestamp)
    L->>C: tick()
    opt a draw was wanted
        L->>H: frame()
        opt the canvas size or the device pixel ratio changed
            L->>L: a new skia.Surface over the WebGL surface, the window follows
        end
        L->>W: _flush_frame_queues() · layout if needed · paint(canvas)
        W->>A: the draw calls
        A->>H: one crossing per draw
        L->>H: placeInput(caret)
    end
```

#### A save becomes a download

```mermaid
sequenceDiagram
    participant T as the handler's task
    participant D as file_dialog_browser.py
    participant P as Pyodide
    participant H as host.mjs

    T->>D: await save_file(default_name)
    D->>P: a fresh directory in the page's file system
    D->>T: add_done_callback(download the path)
    D-->>T: the path, at once
    T->>P: write the file
    T->>T: the handler returns, the task ends
    D->>H: download(name, bytes)
```

### Promises

- The rendering code is the desktop code.
- The adapter covers the calls the framework makes.
- The canvas matrix lives in Python. It reaches CanvasKit once per run of
  draws.
- Geometry and paint state cross to JS as plain numbers, once per draw.
- Every font family name resolves to the typefaces the page loaded.
- A frame runs only when one was asked for.
- No collection runs inside a frame. The collector runs on a timer the frame
  arms as it ends, after the idle work. Idle work left over re-arms the
  timer at once.
- The WebGL surface is made again when the canvas or the device pixel ratio
  changes. That frame repaints everything.
- A deadline within a frame's time waits for the next frame. A later one is a
  `setTimeout`.
- The main window fills the canvas.
- From the host boundary on, the key handling is the desktop's.
- The clipboard crosses in one direction at a time. A copy writes through
  `navigator.clipboard`. A paste arrives only as a paste event.

## The Remote Functions

`@worker` and `@server` mark the functions whose call leaves the UI thread,
on both targets. Nothing is shared with the caller.

### Structure

```mermaid
flowchart LR
    function[remote/function.py]
    worker[remote/worker.py]
    codec[remote/codec.py]
    writer[remote/writer.py]
    pool[remote/pool.py]
    threads[remote/threads.py]
    process[remote/process.py]
    side[backends/web/worker.py]
    scope[remote/scope.py]
    calls[web/calls.py]
    workersjs[workers.mjs]
    observable[the caller's Observable]

    worker -- "WorkerFunction is a RemoteFunction" --> function
    function -- "a Codec per annotation, at definition" --> codec
    function -- "CallWriter(observable, codec)" --> writer
    writer -- "the latest value per tick" --> observable
    worker -- "web_pool · thread_pool · process_pool: Pool.call(name, ceiling, values, writers)" --> pool
    pool -- "Transport.start(slot) · Worker.post · Worker.end" --> threads & process & worker
    worker -- "_WebTransport: NV_WORKERS.start() · handle.post · handle.end" --> workersjs
    side -- "RemoteFunction.run(values, writers, token)" --> function
    threads & process -- "RemoteFunction.run(values, writers, token)" --> function
    function -- "POST nv/call/module.fn, ndjson back" --> calls
    worker -- "is_server_only(module)" --> scope
```

| Module | Role |
| --- | --- |
| `remote/function.py` | `RemoteFunction`: the codecs from the annotations, the call that encodes and decodes, `run()` on the function's side; `ServerFunction`: the server mark's one request; `register`, the two marks |
| `remote/worker.py` | `WorkerFunction`: `parallel`, `process`, `warm`; the three pools; `_WebTransport`, the page's Web Workers as a transport |
| `remote/codec.py` | `Codec`: encode and decode by annotation; the scalars, `datetime`, an `Enum`, a dataclass, the containers |
| `remote/writer.py` | `WriteOnlyObservable`, the progress parameter; `CallWriter`, which lands each write on the caller's observable |
| `remote/pool.py` | `Pool`: the workers of one kind and the calls waiting for them; the ceiling, the machine's limit, `warm`, `retire` |
| `remote/threads.py` | a pooled thread as a transport |
| `remote/process.py` | a child process started with `spawn` and fed through a pipe, as a transport |
| `backends/web/worker.py` | the worker's side in the browser: imports the modules, runs a call, posts the writes and the result |
| `remote/scope.py` | `server_only()`, which marks a module as one the browser never gets |
| `web/calls.py` | the server's side of a `@server` call (The Server) |
| `workers.mjs` | starts and relays the Web Workers (The Page) |
| the caller's Observable | the app's observable a progress parameter writes to |

### Sequence

#### A worker call

```mermaid
sequenceDiagram
    participant App as the app (UI thread)
    participant F as remote/function.py
    participant Wf as remote/worker.py
    participant P as remote/pool.py
    participant T as the transport (threads.py, process.py or workers.mjs)
    participant Wr as remote/writer.py
    participant O as the caller's Observable

    App->>F: await fn(args, progress)
    F->>F: encode the arguments by their codecs
    F->>Wf: _call_on_web, or _call_on_desktop
    Wf->>P: call(name, ceiling, values, writers)
    P->>P: queue, then run when fewer calls of fn run than its ceiling and a worker is idle or can start
    P->>T: start(slot) if needed, post(call_id, name, values)
    loop while the function runs
        T-->>P: a message per write to a progress parameter
        P->>Wr: CallWriter.receive(value)
        Wr->>O: the latest value per clock tick
    end
    alt the function returns
        T-->>P: the result, or the error
        P-->>Wf: the encoded result
        Wf-->>F: the encoded result
        F-->>App: decoded, or a builtin exception by type, or RemoteError
    else the caller cancels
        App--xP: CancelledError
        alt the call is queued
            P->>P: forget it
        else the call is running
            P->>T: end(), and another starts when a call needs it
        end
    end
```

### Promises

- Both marks go on a module-level function. The app calls it the same way on
  both targets, `await fn(...)`.
- On the desktop a call of either mark runs on a thread the runtime owns, or
  in a child process under `process`.
- The arguments, the result and every progress write pass through the codec
  on both targets.
- The codec comes from the type annotations, never from the data. A type the
  codec has no rule for is refused when the function is defined.
- Progress flows through a `WriteOnlyObservable` parameter. The caller's
  observable takes the latest value per clock tick.
- The `CancelToken` is a parameter with a default. On a thread, cancelling
  sets it. In a worker or a child process, cancelling ends the Python running
  the call.
- A builtin exception raised in the function is raised again in the caller by
  type. Any other arrives as `RemoteError`.
- `@worker` marks a function in a module the browser gets.
- The ceiling is per function. The pool is per kind, grown to the largest
  ceiling and never past the machine's cores.
- A worker that ends on its own fails its call with `ConnectionError`. One
  that never becomes ready fails every call until the pool is retired.
- A child process imports the functions' modules by name. It imports the
  entry script the way `multiprocessing` does.
- Hot reload retires the desktop's pools.

## The Server

One process serves the page and answers the server functions.

### Structure

```mermaid
flowchart LR
    cli[web/__main__.py]
    server[web/server.py]
    stubs[web/stubs.py]
    assets[web/assets.py]
    calls[web/calls.py]
    function[remote/function.py]
    app[the app's sources]
    browser[the browser]

    cli -- "site(app, bundle_runtime) · make_server · write_site · write_server · load_server_functions" --> server
    server -- "ServerOnly(app_dir) · stub_source · server_modules · worker_modules" --> stubs
    server -- "fetch(asset): Pyodide · CanvasKit · the fonts · the licences" --> assets
    server -- "do_POST → handle_call" --> calls
    calls -- "lookup(name) · run(values, writers, token)" --> function
    stubs -- "ast.parse" --> app
    server -- "the files of the site" --> browser
    browser -- "POST nv/call/module.fn" --> calls
```

| Module | Role |
| --- | --- |
| `web/__main__.py` | `run` serves the source tree and opens a browser; `build` writes the site and the server directory; `serve` serves a built site and its calls |
| `web/server.py` | builds the zip, lists the page's files, writes the two directories, serves both over HTTP |
| `web/stubs.py` | finds the server-only files and the modules that hold a mark by reading the sources; writes a stub per server-only module |
| `web/assets.py` | downloads and caches Pyodide, CanvasKit, the fonts and their licences |
| `web/calls.py` | runs a `@server` function on a thread per request and streams its writes and result back |
| `remote/function.py` | the function the server runs (The Remote Functions) |
| the app's sources | what is read, zipped, stubbed and served |
| the browser | fetches the page and posts the calls |

### Sequence

#### A server call

```mermaid
sequenceDiagram
    participant App as the app (browser)
    participant S as web/calls.py
    participant F as the function, on a thread

    App->>S: POST nv/call/module.fn, arguments as JSON
    S->>F: run(values, writers, token)
    loop while the function runs
        F-->>S: a write to a progress parameter
        S-->>App: a line {"w": name, "v": data}
    end
    alt the function returns
        S-->>App: a line {"r": data}, or {"e": error}
    else the caller cancels
        App--xS: the request closes
        S->>F: token set
    end
```

#### The build writes the site

```mermaid
sequenceDiagram
    participant C as web/__main__.py
    participant S as web/server.py
    participant St as web/stubs.py
    participant A as web/assets.py

    C->>S: site(app, bundle_runtime=True)
    S->>St: ServerOnly(app_dir), worker_modules(app_dir)
    St-->>S: the server-only files, their stubs, the worker modules
    S->>A: fetch(Pyodide, CanvasKit, fonts, licences)
    S->>S: build_bundle: lib/ · app/ without the server-only files · the stubs
    C->>S: write_site(files, dist/site)
    C->>S: write_server(app, dist/server)
```

### Promises

- The server keeps no session state.
- A server-only module stays out of the zip. A stub with the same signatures
  takes its place.
- A dataclass in a `@server` signature comes from a module the page gets.
- Each progress write streams back as a line of the response. Cancellation is
  the request closing.
- `run` reads the sources at every request.
- `server/` is the only part that needs Python.
