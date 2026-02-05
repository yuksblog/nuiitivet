# Error handling

## Error handling policy

Avoid states where exceptions occurring throughout the framework are silenced by `try/except: pass`, making root cause tracking difficult.

- Reduce "silent failures"
- Enable consistent handling of exceptions
- Preserve stack traces while preventing log flooding

### Boundary vs internal

This document divides exception handling into two roles: "Boundary" and "Internal".

- **Boundary** (Perimeter)
  - Entry points from the OS/backend into the framework interior.
  - Finalizes the treatment of exceptions.
    - Convert to log + continue / fail fast
    - raise
- **Internal** (Implementation details)
  - Core processing called from boundaries, such as rendering, layout, tree operations, and subscriptions.
  - Propagates exceptions to boundaries without silencing them.

## Processing categories

### Startup / initialization

Sections where "failure to start means inability to continue," such as app startup, backend initialization, and essential resource resolution.

- Principle: raise (fail fast)
- Exception: If an auxiliary feature fails to initialize but the app can still continue, log and fallback.

### Event input

The section that delivers inputs arriving from the OS/backend (clicks, keys, navigation, focus, etc.) to the application.

- Principle: Catch at the boundary (outer perimeter of input delivery), log it, and continue to the next event.

### Rebuild (State update / Composition)

The section that updates state in response to events/timers and rebuilds or reflects differences in the UI tree.

- Principle: Catch at the boundary and log; if possible, skip the affected subtree or unit of work and continue.

### Rendering / frame update hot path

The section that repeats on a per-frame basis to perform drawing, layout, and animation updates.

- Principle: Catch at the frame boundary and log (only once for the same occurrence).
- Safely drop the current frame and proceed to the next frame.

### Subscriptions / callbacks

Sections that "call external code," such as user-provided callbacks, subscription notifications, and async task completion notifications.

- Principle: Catch at the caller (outer perimeter of subscription notification/callback execution) and log; do not stop the subscription.
- Exception: Explicit cancellation/termination (equivalent to `CancelledError`) should be ignored or logged as DEBUG.

### Repository mapping examples

Examples of **boundaries** (perimeters):

- Entry point: `src/__main__.py`
- App execution boundary: `nuiitivet.runtime.app.App.run` and its frame driving surroundings (e.g., `_render_frame`)
- Backend boundary: `@window.event` handlers in `nuiitivet.backends.pyglet.runner.run_app` (`on_draw`, `on_mouse_*`, `on_key_*`, etc.)
- Event loop boundary: `nuiitivet.backends.pyglet.event_loop.ResponsiveEventLoop.run` / `_perform_draw`
- Input delivery perimeter: `nuiitivet.runtime.app_events.dispatch_*`

Examples of **internal** implementation details:

- Tree / Composition: `nuiitivet.widgeting.*`
- Layout / Scrolling: `nuiitivet.layout.*` / `nuiitivet.scrolling.*`
- Rendering: `nuiitivet.rendering.*`
- Animation: `nuiitivet.animation.*`
- Theme / Colors: `nuiitivet.theme.*` / `nuiitivet.colors.*`
- Observation / Subscription: `nuiitivet.observable.*`
- Widget implementation: `nuiitivet.widgets.*` (places calling user-provided callbacks fall under "Subscriptions / callbacks")

## Logging policy

### Exception logging

- Use `logger.exception(...)` to preserve stack traces.
- `logger.exception(...)` should only be called at "boundaries" where exceptions are caught and converted to continuations.

### Avoid duplicate stack traces

- Internally, avoid calling `logger.exception(...)`.
- if an internal catch is necessary, provide context (message formatting, exception wrapping, etc.) and re-raise.

### debug_once / exception_once

To prevent log flooding, introduce a mechanism to emit the same event only once.

- **Key design**
  - `category` (e.g., render/event/subscription) + `site` (e.g., function name or logical trigger point) + Exception type name.
  - Do not include the full message in the key.
- **Capacity**
  - Default to N items (e.g., 1024).
  - Use LRU or similar to discard old keys when capacity is exceeded.
- **Thread-safety**
  - Ensure internal state updates are thread-safe if called from outside the UI thread.

### Default logger behavior

- The framework uses `logging.getLogger("nuiitivet")` (or sub-loggers).
- Logging configuration is left to the user, with recommended settings provided in the documentation.
  - The framework does not perform logging configuration (no `basicConfig` or handler additions).
  - The recommended level for the `nuiitivet` logger is `WARNING`.

Example: `logging.yaml`

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: "%(asctime)s %(levelname)s %(name)s: %(message)s"

handlers:
  stderr:
    class: logging.StreamHandler
    level: WARNING
    formatter: standard
    stream: ext://sys.stderr

loggers:
  nuiitivet:
    level: WARNING
    handlers: [stderr]
    propagate: false

root:
  level: WARNING
  handlers: [stderr]
```
