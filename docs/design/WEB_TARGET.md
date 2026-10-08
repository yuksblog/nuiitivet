# Web Target

One app runs on the desktop and in a browser from the same source. The app
does not branch on the target: the widgets, the observables, the handlers
and the navigation are written once, and the web target is realised under
them. The two marks an app makes for the web, `@worker` and `@server`, run on
the desktop too.

In the browser, Pyodide runs the app's Python unmodified, a CanvasKit adapter
with the shape of skia-python draws it onto one canvas, and the browser's
event loop replaces the pyglet one. The page is files that any file server
can serve. The functions an app marks with `@worker` run on a Web Worker the
page starts; the functions it marks with `@server` are the only code that
runs on a server; everything else ships to the browser.

```mermaid
flowchart RL
    server[Server: the @server functions]
    subgraph browser [Browser]
        worker[Web Worker: a second Pyodide, the @worker functions]
        py[Pyodide: nuiitivet and the app]
        adapter[CanvasKit adapter]
        host[host.mjs: canvas, input, clipboard]
    end
    server <-- "a call: POST nv/call/name, then progress and the result" --> py
    worker <-- "a call: a message, then progress and the result" --> py
    py -- "skia calls" --> adapter
    adapter -- "one crossing per draw" --> host
    host -- "events" --> py
```

## The Page

The page is seven files beside the fonts: `index.html`, `boot.mjs`,
`host.mjs`, `workers.mjs`, `worker.mjs`, `config.json` and `bundle.zip`. The
zip holds the framework under
`lib/` and the app's directory under `app/`, built from the sources at every
request, so a browser reload shows an edit. One zip is one fetch; the
framework alone is hundreds of modules, and the page would otherwise start
with hundreds of requests.

`config.json` says where Pyodide and CanvasKit are, and names the app's
modules that hold a `@worker` function. A development page loads the runtimes
from a CDN; a built site carries them, with the licences of everything it
redistributes, so it needs no other server. Every URL is relative to the page,
so a built site works under any path.

`boot.mjs` starts the worker when `config.json` names a worker module, then
loads CanvasKit, Pyodide, the zip and the fonts in parallel, unpacks the zip
to `/nuiitivet`, installs the host, and runs the entry script as `__main__`.
Before the entry runs it calls the backend's `prepare()`, which
installs the adapter as the `skia` module, registers the UI thread and
installs the browser clock. The clock goes in first because a widget mounted
while the App is constructed arms its timers at once, and the fallback clock
would start a thread for them.

`App.run()` in a browser hands the app to the backend and returns. The
browser's event loop drives the app from then on; the backend module keeps a
reference to the app, since the entry script has finished.

## Drawing

The adapter is installed under the name `skia`, so the rendering code is the
desktop code: paints, paths, text blobs, pictures and the paint cache run
unchanged. The adapter covers the calls that code makes; a skia-python call
nothing in the framework uses is not mirrored.

The canvas matrix lives in Python. CanvasKit has no `setMatrix`; a matrix
pushed to it could only be replaced by multiplying with an inverse, and at a
device pixel ratio such as 1.5 that leaves a matrix that is almost the
identity. The adapter's matrix reaches CanvasKit once per run of draws, inside
a save level the host pops before every save, restore and clip, and clips are
applied in device coordinates. Geometry and paint state cross to JS as plain
numbers, once per draw, so no array is built on the Python side.

Every font family name resolves to the text typefaces the page loaded, and a
font file loads as its own typeface. The browser has no system font list to
match against.

A frame runs only when one was asked for: by an invalidation, by a resize, or
by the clock for a callback that is due. The request is a
`requestAnimationFrame`, so frames pace to the display and `draw_fps` has no
effect. The WebGL surface is made again when the canvas or the device pixel
ratio changes, and that frame repaints everything.

The main window fills the canvas and follows its size. A browser shows one
window, so a second window stays unrealized and a warning says so once.

## The Clock

The browser clock keeps its own list of deadlines. A deadline within a frame's
time waits for the next frame, so an animation ticks in step with the
display; a later one is a `setTimeout`. Every frame ticks the clock before it
draws, so a callback due at that frame runs before the paint it invalidates.

## Input

The host forwards pointer, wheel, key, text, composition and paste events to
the same dispatch methods of `Window` that the pyglet backend calls. Key names
are translated once, at the host boundary; from there the key handling is the
desktop's, including a held key repeating only as a text motion.

An input element the user never sees sits at the caret. It is what the
browser composes IME text into and what a phone shows its keyboard for;
without a focused text field it asks for no keyboard. The browser does not
report a selection inside the composition, so the caret sits at its end.

The clipboard crosses in one direction at a time. A copy writes through
`navigator.clipboard`. A paste arrives only as a paste event, because the
browser gives a page the clipboard on that gesture alone; the backend stores
the text and dispatches Ctrl+V, so a text field pastes as on the desktop.

Escape is back navigation, on the release. The press reports whether the app
can handle it, so the browser acts on the key itself only when the app would
not.

## One Thread

Pyodide runs on the browser's main thread and cannot start another. The UI
thread is the only thread, and a `threading.Thread` is refused. This is the
one place where the desktop and the browser differ in what an app may do,
and the one place where the framework offers an API of its own instead of
the standard library's: `@worker` and `@server`. A thread shares memory with
the UI; a Web Worker and a server cannot, so the standard API could not be
made to mean the same thing on both targets. `switch_map` accepts a coroutine
function and runs it as a task, so an async transform needs no thread on
either target.

Both marks go on a module-level function, and the app calls it the same way
on both targets: `await fn(...)`. The function itself is a plain `def`, so it
is unit-tested as any function. What differs between the marks is where the
call goes in the browser: `@worker` to a Web Worker the page owns, `@server`
to a server. Under either mark the function is a function of its arguments,
and its body and its callers are the same; an app picks the mark by what the
place costs it: the worker's boot and its cancel, the server's round trip
and its process, the libraries each can run, and whether the module may be
read in the browser.

On the desktop a call of either mark runs on a thread the runtime owns, in
the same process. The arguments, the result and every progress write still
pass through the codec, so the function shares no object with its caller;
cancelling the awaiting task sets the function's token; and an exception
that is not builtin arrives as `RemoteError`. The desktop follows the
browser's rules so that an app which works on the desktop works in the
browser, instead of failing there on an object it passed by reference.

Arguments and the result cross as JSON, and the codec comes from the type
annotations, never from the data: a float annotated `float` arrives as a
float even when it was sent as `2`, a dataclass arrives as that dataclass,
and a value of another type is refused with the field named. A type the
codec has no rule for is refused when the function is defined, not at the
first call.

Progress flows through a `WriteOnlyObservable` parameter. The caller passes an
observable, the function's side writes it, and each write crosses back as it
happens. The caller's observable takes the latest value per clock tick, so a
tight loop does not flood the page.

The `CancelToken` is a parameter with a default, so the function runs
unchanged when nobody cancels. A builtin exception raised in the function is
raised again in the caller by type. Any other exception arrives as
`RemoteError`, carrying the type's name and the message: the caller's side
may have no class to rebuild it from.

## Worker Functions

`@worker` marks a function in a module the browser gets. In the browser the
call goes to a Web Worker: a second Pyodide that `boot.mjs` starts when
`config.json` names a worker module. The worker fetches the same zip,
unpacks it, and imports the worker modules while the page loads, so the
first call pays no import. The modules are found by reading the sources, as
the stubs are; a server-only module is never one of them, and the desktop
refuses a `@worker` function placed there.

```mermaid
sequenceDiagram
    participant App as App (browser)
    participant W as Web Worker
    App->>W: a message: the call's number, the function, arguments as JSON
    loop while the function runs
        W-->>App: a message per write to a progress observable
    end
    alt the function returns
        W-->>App: the result, or the error
    else the caller cancels
        App--xW: the worker is ended, and another boots
    end
```

The page runs one worker, and hands it one call at a time: the next call
leaves the page's queue when the previous one has answered. A queued call is
cancelled by forgetting it. The running call cannot be: a busy worker reads
no message until its function returns, so cancelling it ends the worker, and
the page boots a replacement that the queue waits for. A worker that ends
on its own fails its call with `ConnectionError` and is replaced the same
way; one that fails to boot fails every call with the reason.

A token the worker polls through a `SharedArrayBuffer` would stop a running
function without ending the worker; it was rejected because the buffer needs
cross-origin isolation headers that a plain file host does not send.
`pickle` as the transport, which the browser could carry, was rejected
because it would accept on the desktop a value the codec refuses, and the
desktop would stop predicting the browser. A `multiprocessing` pool is not
an option: Pyodide's standard library refuses to construct one.

## Server Functions

`@server` marks a function in a server-only module. In the browser the call
becomes one HTTP request to the server that holds the function. The server
keeps no session state, so any instance can answer any call.

```mermaid
sequenceDiagram
    participant App as App (browser)
    participant S as Server
    App->>S: POST nv/call/module.fn, arguments as JSON
    loop while the function runs
        S-->>App: a line per write to a progress observable
    end
    alt the function returns
        S-->>App: the result, or the error
    else the caller cancels
        App--xS: the request closes, and the token on the server is set
    end
```

The function lives in a server-only module: one whose top level calls
`server_only()`, or that sits under a package whose `__init__.py` does. A
server-only module never reaches the browser. The build leaves its files out
of the zip and writes a stub in their place, with the same signatures, whose
functions send their call to the server. The stubs come from the source text,
so the build imports nothing of the server side; a DB password in a
server-only module stays on the server without the author doing more than
marking the module. A dataclass in the signature must come from a module the
page gets, since the stub's signature names it.

Each progress write streams back as a line of the response. Cancellation is
the request closing: the caller cancels its task, the browser aborts the
request, and the handler, which watches the connection while the function
runs, sets the function's `CancelToken`.

## Build and Serve

The development server serves the page from the source tree and answers the
server functions from the same process. The build writes two directories: the
site, which any static host serves and which carries the worker and its
functions, and the server, which is the app's sources. An app without server
functions deploys the site alone; one with them deploys both, and the server
is the only part that needs Python.
