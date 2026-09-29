# Error Handling

An exception is never silenced by `try/except: pass`. It is caught once, at a
boundary, logged with its stack trace, and the framework continues or fails
fast; inside the boundary it propagates. This keeps a root cause findable and
keeps one failure from flooding the log.

## Boundary and Internal

A **boundary** is an entry point from the OS or the backend into the
framework: it finalises the treatment of an exception, to log and continue,
to fail fast, or to raise. **Internal** code, everything the boundary calls
(rendering, layout, tree operations, subscriptions), propagates an exception
to its boundary. An internal catch that is needed adds context, by wrapping
or by message, and re-raises.

Boundaries in the repository: the app run entry (`App.run` and the frame
driving around `Window._render_frame`), the backend's `@window.event`
handlers in `backends.pyglet.runner.run_app` (`on_draw`, `on_mouse_*`,
`on_key_*`), the event loop (`ResponsiveEventLoop.run` / `_perform_draw`) and
input delivery (`runtime.app_events.dispatch_*`). Internal: `widgeting`,
`layout`, `scrolling`, `rendering`, `animation`, `theme`, `colors`,
`observable` and `widgets`, except where a widget calls a user-provided
callback, which is a boundary of the callback kind below.

## By Kind of Work

| Work | Policy |
| --- | --- |
| Startup: app start, backend initialisation, an essential resource | Raise; failing to start means the app cannot continue. An auxiliary feature that fails to initialise logs and falls back. |
| Event input: a click, a key, navigation, focus delivered from the OS | Catch at the delivery boundary, log, continue to the next event. |
| Rebuild: a state update, a recomposition | Catch at the boundary, log, skip the affected subtree or unit of work where possible, continue. |
| The frame hot path: draw, layout, animation, once per frame | Catch at the frame boundary, log once per occurrence, drop the frame, continue to the next. |
| Calling external code: a user callback, a subscription notification, an async task completion | Catch at the caller, log, keep the subscription alive. An explicit cancellation (`CancelledError`) is ignored or logged at DEBUG. |

A synchronous handler that raises is reported and the frame continues: it is
on the frame's own call stack, where unwinding would abandon the rest of the
dispatch. The task of an async handler can re-raise, because the task is the
harness's to await.

## Logging

`logger.exception(...)` preserves the stack trace and is called only at a
boundary, where the exception is converted to a continuation; an internal
catch never calls it, so a trace appears once.

The `*_once` helpers (`debug_once`, `warning_once`, `exception_once`,
`exception_once_per_exc` in `common.logging_once`) emit a record once per
process per key, so a failure that recurs every frame is logged once. The key
is a string the call site chooses, a category and site such as
`"modifier_box_cross_align_copy_exc"`, never the message; up to 1024 keys are
kept under a lock and the oldest are evicted. `exception_once_per_exc` keys
on the exception as well, so a new failure at the same site after a hot
reload is logged again. The dev runner switches the de-duplication off for
its verbose runtime log, because a suppressed record never reaches the
handler that captures it.

The framework logs to `logging.getLogger("nuiitivet")` and its sub-loggers
and configures nothing: no `basicConfig`, no handler. Configuration is the
application's, and `WARNING` is the recommended level for the `nuiitivet`
logger.
