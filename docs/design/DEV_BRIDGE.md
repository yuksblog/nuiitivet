# Dev Bridge

The dev bridge lets a tool see and drive a running app. Hot reload lets its
author edit it ([HOT_RELOAD.md](HOT_RELOAD.md)). The human's side of the
same session is [DEV_MODES.md](DEV_MODES.md).

## Overview

Four groups of modules take part, with the dev runner, the hot reload
controller and the backend's input handlers at their edges.

### Structure

```mermaid
flowchart LR
    clients[The Clients]
    bridge[The Bridge]
    perception[The Perception and the Actions]
    journals[The Journals]
    runner[dev/__main__.py]
    controller[dev/controller.py]
    backend[backends/pyglet/runner.py]
    agent[the coding agent]

    agent -- "MCP tools · python -m nuiitivet.dev verb" --> clients
    clients -- "HTTP on 127.0.0.1" --> bridge
    bridge -- "call_on_ui_thread(job)" --> perception
    bridge -- "recent(limit)" --> journals
    runner -- "DevBridge(...) · install() · start()" --> bridge
    runner -- "the journals · InteractionRecorder · RuntimeLogCapture" --> journals
    controller -- "record_success · record_error" --> journals
    backend -- "on_mouse_press · on_mouse_scroll · on_key_press · on_text" --> journals
```

| Module | Role |
| --- | --- |
| The Clients | the MCP server and the CLI |
| The Bridge | the HTTP server the clients talk to |
| The Perception and the Actions | what a tool reads, and the input it synthesises |
| The Journals | what happened while the agent was not looking |
| `dev/__main__.py` | the dev runner ([HOT_RELOAD.md](HOT_RELOAD.md)) |
| `dev/controller.py` | the reloader ([HOT_RELOAD.md](HOT_RELOAD.md)) |
| `backends/pyglet/runner.py` | the real input path ([APP_WINDOW.md](APP_WINDOW.md)) |
| the coding agent | reads and acts in turns |

### Promises

- The bridge opens inside a dev session only.
- Everything the bridge does to the tree runs on the UI thread.
- The agent pulls. Nothing is pushed to it.

## The Bridge

A localhost HTTP server on a port the OS picks, started by the dev runner
beside hot reload.

### Structure

```mermaid
flowchart LR
    bridge[dev/bridge.py]
    session[dev/session.py]
    loader[dev/loader.py]
    clock[pyglet.clock]
    runner[dev/__main__.py]
    client[dev/client.py]
    verbs[the verbs]
    journals[the journals]
    fs[the project root]

    runner -- "DevBridge(app, discovery_root, journals, capture, comments) · install() · start() · shutdown()" --> bridge
    runner -- "find_discovery_root(project_root)" --> loader
    bridge -- "current_dev_session()" --> session
    bridge -- "schedule_interval(_drain, 0.03) · unschedule(_drain)" --> clock
    bridge -- ".nuiitivet/dev-bridge.json: host, port, pid" --> fs
    client -- "GET /status · /describe_tree · /reload_log · POST /click · /type · /key · /scroll · /wait_for" --> bridge
    bridge -- "describe_tree · describe_state · click · type_text · press_key · scroll · settle, on the UI thread" --> verbs
    bridge -- "recent(limit) · set_verbose(enabled)" --> journals
```

| Module | Role |
| --- | --- |
| `dev/bridge.py` | `DevBridge`: the HTTP server on a daemon thread, the handler per route, the discovery file; `_UIThreadMarshaller`: a queue drained on the clock, each worker blocking on its job's event |
| `dev/session.py` | answers whether a dev session is active |
| `dev/loader.py` | the anchor of the discovery file, the user-facing project root |
| `pyglet.clock` | the UI thread's tick the drain runs on |
| `dev/__main__.py` | wires the bridge around the app. Tears it down after the loop |
| `dev/client.py` | the HTTP client (The Clients) |
| the verbs | the work the bridge runs on the UI thread (The Perception and the Actions) |
| the journals | read by the bridge (The Journals) |
| the project root | holds the discovery file |

### Sequence

#### A request touches the tree

```mermaid
sequenceDiagram
    participant C as client.py
    participant B as bridge.py, the worker thread
    participant D as bridge.py, the drain on pyglet.clock
    participant V as the verbs

    C->>B: POST /click, key or label
    B->>B: queue.put(job, holder, event), event.wait(timeout)
    D->>D: _drain(dt): get_nowait()
    D->>V: click(app, key, label)
    V-->>D: the result, or an exception
    D->>B: holder, event.set()
    B-->>C: 200 with the result, or an error status with the message
```

### Promises

- The discovery file is removed on shutdown.
- A worker thread never touches the tree.
- A job's exception reaches the client as an error response.

## The Perception and the Actions

A tool reads the tree, the state behind it or a screenshot. A tool
synthesises the input the real backend delivers.

### Structure

```mermaid
flowchart LR
    perception[_interaction/perception.py]
    action[_interaction/action.py]
    devaction[dev/action.py]
    observer[dev/action_observer.py]
    bridge[dev/bridge.py]
    window[runtime/window.py]
    tree[the widget tree]

    bridge -- "describe_tree(root) · describe_state(root, include_animations) · find_target" --> perception
    bridge -- "click · scroll · scroll_into_view · type_text · press_key · check_condition" --> devaction
    devaction -- "the same verb, on_action=OVERLAY_OBSERVER" --> action
    action -- "find_target(root, key, label) · find_obstruction · visible_rect" --> perception
    action -- "_dispatch_mouse_press · _dispatch_mouse_release · _dispatch_mouse_scroll · _dispatch_text · _dispatch_key_press · _modal_blocked()" --> window
    action -- "flush bindings and recompositions · root.layout(w, h)" --> tree
    bridge -- "_render_snapshot(scale)" --> window
    devaction -- "on_click · on_scroll · on_key" --> observer
    perception -- "key · label · text · title · global rect · published state · State values" --> tree
```

| Module | Role |
| --- | --- |
| `_interaction/perception.py` | `describe_tree`, each mounted node's type, identity, root rect and published state; `describe_state`, the `State` values reachable from the tree in the same shape; the target lookup and the obstruction test. Re-exported by `dev/perception.py` |
| `_interaction/action.py` | the verbs |
| `dev/action.py` | the verbs with the on-screen marker bound |
| `dev/action_observer.py` | draws the marker of a bridge-driven action ([DEV_MODES.md](DEV_MODES.md)) |
| `dev/bridge.py` | runs them on the UI thread (The Bridge) |
| `runtime/window.py` | the dispatch entry points; the offscreen render ([APP_WINDOW.md](APP_WINDOW.md)) |
| the widget tree | what is described and driven |

### Sequence

#### A click lands and the tree settles

```mermaid
sequenceDiagram
    participant A as _interaction/action.py
    participant P as _interaction/perception.py
    participant W as runtime/window.py
    participant T as the widget tree

    A->>W: _modal_blocked()
    A->>P: find_target(root, key, label)
    A->>P: visible_rect(node) · find_obstruction(root, node, x, y)
    alt no target, scrolled out, or covered
        Note over A: TargetNotFoundError or TargetNotVisibleError
    else
        A->>W: _dispatch_mouse_press(x, y) · _dispatch_mouse_release(x, y)
        A->>T: flush_binding_invalidations() · flush_scope_recompositions()
        A->>T: root.layout(w, h)
        A->>W: invalidate()
    end
```

### Promises

- A synthesised action enters at the window's dispatch, below the backend's
  input handlers.
- Every verb settles the app before it returns.
- The screenshot is rendered on an offscreen raster surface, never read
  back from the framebuffer.
- Perception never paints.

## The Journals

Three ring buffers tell the agent what happened between its turns.

### Structure

```mermaid
flowchart LR
    reload[dev/journal.py]
    interaction[dev/interaction.py]
    runtime[dev/runtime_journal.py]
    capture[dev/runtime_capture.py]
    controller[dev/controller.py]
    backend[backends/pyglet/runner.py]
    window[runtime/window.py]
    logging[logging · threading · sys]
    once[common/logging_once.py]
    bridge[dev/bridge.py]

    controller -- "record_success(modules, changed) · record_error(traceback, changed)" --> reload
    backend -- "on_mouse_press(app, x, y) · on_mouse_scroll(handler, dx, dy) · on_key_press(name, mask) · on_text()" --> interaction
    window -- "_interaction_recorder" --> interaction
    capture -- "setLogRecordFactory · threading.excepthook · sys.excepthook, each chained to the previous" --> logging
    once -- "one record per distinct failure" --> logging
    capture -- "record(level, message, traceback)" --> runtime
    bridge -- "recent(limit) · set_verbose(enabled)" --> reload & interaction & runtime & capture
```

| Module | Role |
| --- | --- |
| `dev/journal.py` | `ReloadJournal`, each reload's outcome |
| `dev/interaction.py` | `InteractionJournal`, the human's coarse actions and the window opens and closes; `InteractionRecorder`, the hook on the real input path that writes them |
| `dev/runtime_journal.py` | `RuntimeJournal`: log records at WARNING and above, uncaught exceptions |
| `dev/runtime_capture.py` | `RuntimeLogCapture`: the taps on the log record factory and the two exception hooks; the verbose switch |
| `dev/controller.py` | the reloader ([HOT_RELOAD.md](HOT_RELOAD.md)) |
| `backends/pyglet/runner.py` | calls the window's recorder from its input handlers ([APP_WINDOW.md](APP_WINDOW.md)) |
| `runtime/window.py` | the slot the dev runner puts a recorder in, `None` in production |
| `logging · threading · sys` | the standard library's record factory and exception hooks |
| `common/logging_once.py` | logs each distinct failure once at its emit site ([ERROR_HANDLING.md](ERROR_HANDLING.md)) |
| `dev/bridge.py` | serves the journals (The Bridge) |

### Promises

- Every entry carries a monotonic `seq`.
- A reload entry's `changed` names the modules whose source bytes changed.
  A save with identical bytes leaves it empty.
- The interaction journal records the human only. A synthesised action
  bypasses the recorder.
- The interaction journal's vocabulary is the action vocabulary. A semantic
  event is not recorded.
- Typed content never enters a journal. A printable key is dropped. A burst
  of text is one marker.
- A scroll entry is recorded only for an event a region consumed. A gesture
  on one region in one direction is one entry.
- Console output is unchanged by the capture. No handler is added to the
  root logger.
- The journal de-duplicates nothing. The verbose switch makes the emit sites
  record every occurrence.

## The Clients

The MCP server and the CLI issue the same HTTP requests.

### Structure

```mermaid
flowchart LR
    mcp[dev/mcp_server.py]
    cli[dev/__main__.py]
    client[dev/client.py]
    bridge[dev/bridge.py]
    fs[the project root]
    sdk[the mcp SDK]
    host[the MCP host]
    shell[the shell]

    host -- "stdio" --> mcp
    shell -- "python -m nuiitivet.dev status · describe-tree · click ..." --> cli
    mcp -- "BridgeClient.discover(), per call" --> client
    cli -- "BridgeClient.discover()" --> client
    client -- "find_discovery_file(start), upward · _pid_alive(pid)" --> fs
    client -- "GET · POST, with urllib" --> bridge
    mcp -- "FastMCP · Image · the tool descriptions" --> sdk
```

| Module | Role |
| --- | --- |
| `dev/mcp_server.py` | `python -m nuiitivet.dev mcp`: one tool per bridge route, each forwarding to a freshly discovered client; the descriptions that steer the model |
| `dev/__main__.py` | the one-shot subcommands |
| `dev/client.py` | `BridgeClient`: finds the discovery file, drops a stale one whose process is gone, speaks HTTP |
| `dev/bridge.py` | the server (The Bridge) |
| the project root | holds the discovery file (The Bridge) |
| the mcp SDK | an optional dependency, 1.x or 2.x |
| the MCP host | the agent's runtime |
| the shell | a session without an MCP host |

### Promises

- The MCP server holds no app logic.
- The MCP server starts with no app running.
- The CLI depends on the standard library only.
