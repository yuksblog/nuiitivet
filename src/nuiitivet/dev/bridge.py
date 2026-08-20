"""Dev bridge: a localhost control channel into the running app (dev-only).

Every "live" operation an assistant might perform on a running app -- read the
tree, screenshot it, later click or type -- needs the same primitive: post a
request onto the app's UI thread and return the result. Hot reload already owns
that primitive (watcher thread -> flag -> ``pyglet.clock`` drain on the UI
thread). This module generalizes it into one bridge that perception (#374),
action, and the MCP server are all thin clients of.

Design:

* An HTTP server (:class:`http.server.ThreadingHTTPServer`) bound to
  ``127.0.0.1`` on an ephemeral port. Localhost only, never opened in
  production -- :meth:`DevBridge.start` refuses to run without an active dev
  session (:func:`nuiitivet.dev.current_dev_session`).
* Each request runs on an HTTP worker thread. Work that touches the widget tree
  is marshalled onto the UI thread via :meth:`call_on_ui_thread`: the worker
  enqueues a callable and blocks on an event; a ``pyglet.clock`` drain
  registered by :meth:`install` runs the callable on the UI thread and signals
  completion. This satisfies the main-thread-only rule for tree access
  (``docs/design/THREADING_MODEL.md``).
* On start the chosen port is written to ``<project_root>/.nuiitivet/
  dev-bridge.json`` so CLI clients can discover the running app; the file is
  removed on shutdown.

See #374 and ``docs/design/HOT_RELOAD.md``.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from .action import (
    TargetNotFoundError,
    check_condition,
    click,
    press_key,
    scroll,
    scroll_into_view,
    type_text,
)
from .interaction import InteractionJournal
from .journal import ReloadJournal
from .perception import describe_state, describe_tree
from .selection import Selection, describe_selection
from .runtime_capture import RuntimeLogCapture
from .runtime_journal import RuntimeJournal
from .session import current_dev_session

if TYPE_CHECKING:
    from nuiitivet.runtime.app import App

logger = logging.getLogger(__name__)

# Relative location of the discovery file under the project root.
DISCOVERY_DIRNAME = ".nuiitivet"
DISCOVERY_FILENAME = "dev-bridge.json"

# How long an HTTP worker waits for the UI thread to service a request before
# giving up (the UI thread may be busy laying out or blocked in a modal op).
_UI_CALL_TIMEOUT = 5.0

# Type of a unit of UI-thread work: takes the App, returns anything.
_UIJob = Callable[["App"], Any]

_WAIT_FOR_DEFAULT_TIMEOUT = 3.0

# Every poll settles, and ``settle`` calls ``app.invalidate()``, so each poll
# queues a UI-thread job and a repaint request. The floor bounds that to ~200
# per second.
_WAIT_FOR_DEFAULT_MIN_INTERVAL = 0.005

# Cap on one sleep, as a share of the time left. Uncapped, a 1.4 s poll against
# a 3 s timeout sleeps 1.4 s and leaves room for a single further attempt.
_WAIT_FOR_REMAINING_SHARE = 4.0


class _UIThreadMarshaller:
    """Runs callables on the UI thread and returns their results synchronously.

    Mirrors the hot-reload controller's watcher-thread -> clock-drain pattern,
    but is request/response: the caller blocks until the UI thread produces a
    result (or raises), rather than fire-and-forget.
    """

    def __init__(self, app: "App", *, drain_interval: float = 0.03) -> None:
        self._app = app
        self._drain_interval = drain_interval
        self._queue: "queue.Queue[tuple[_UIJob, dict[str, Any], threading.Event]]" = queue.Queue()
        self._installed = False

    def call_on_ui_thread(self, job: _UIJob, *, timeout: float = _UI_CALL_TIMEOUT) -> Any:
        """Run ``job(app)`` on the UI thread and return its result.

        Raises:
            TimeoutError: If the UI thread does not service the job in time.
            Exception: Whatever ``job`` raised, re-raised on the caller's thread.
        """
        holder: dict[str, Any] = {}
        done = threading.Event()
        self._queue.put((job, holder, done))
        if not done.wait(timeout):
            raise TimeoutError("UI thread did not service the request in time")
        if "error" in holder:
            raise holder["error"]
        return holder.get("result")

    def _drain(self, dt: float) -> None:
        """UI-thread tick: run every queued job, signalling each completion."""
        while True:
            try:
                job, holder, done = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                holder["result"] = job(self._app)
            except Exception as exc:  # surfaced on the waiting worker thread
                holder["error"] = exc
            finally:
                done.set()

    def install(self) -> None:
        """Register the UI-thread drain on the pyglet clock."""
        if self._installed:
            return
        self._installed = True
        import pyglet

        pyglet.clock.schedule_interval(self._drain, self._drain_interval)

    def shutdown(self) -> None:
        """Unschedule the drain and fail any jobs still waiting."""
        if not self._installed:
            return
        self._installed = False
        try:
            import pyglet

            pyglet.clock.unschedule(self._drain)
        except Exception:
            logger.debug("dev bridge: failed to unschedule drain", exc_info=True)
        while True:
            try:
                _job, holder, done = self._queue.get_nowait()
            except queue.Empty:
                break
            holder["error"] = RuntimeError("dev bridge is shutting down")
            done.set()


def _parse_limit(query: str) -> Optional[int]:
    """Extract an integer ``limit`` from a URL query string, if present.

    Returns ``None`` when absent or unparseable, meaning "no cap -- return all".
    """
    from urllib.parse import parse_qs

    values = parse_qs(query).get("limit")
    if not values:
        return None
    try:
        return int(values[0])
    except (TypeError, ValueError):
        return None


def _parse_flag(query: str, name: str) -> bool:
    """Extract a boolean ``name`` flag from a URL query string.

    Accepts the usual truthy spellings (``1`` / ``true`` / ``yes`` / ``on``,
    case-insensitively) and a bare ``?name`` with no value. Anything else --
    including an absent parameter -- reads as ``False``, so a malformed flag
    degrades to the default rather than failing the request.
    """
    from urllib.parse import parse_qs

    values = parse_qs(query, keep_blank_values=True).get(name)
    if not values:
        return False
    return values[0].strip().lower() in ("", "1", "true", "yes", "on")


# Runtime-log levels that count as a real failure for ``status``'s error_count,
# so ordinary WARNING noise does not read as "the app died".
_STATUS_ERROR_LEVELS = frozenset({"ERROR", "CRITICAL"})


def _probe_app(app: "App") -> tuple[Optional[str], bool]:
    """Read the two live signals ``status`` needs off the app (UI thread).

    Returns ``(title, blank)``: the resolved window title and whether the
    current frame is a single uniform color (see :meth:`App._frame_is_blank`).
    The blank probe renders, so it is defended -- a render failure reports
    ``blank=False`` (do not claim blank) rather than aborting the status call.
    """
    title = app.title
    try:
        blank = bool(app._frame_is_blank())
    except Exception:
        logger.debug("dev bridge: blank-frame probe raised", exc_info=True)
        blank = False
    return title, blank


def _latest_reload(journal: Optional[ReloadJournal]) -> Optional[dict[str, Any]]:
    """Return the newest reload as ``{"seq", "outcome"}``, or ``None`` if none.

    A compact roll-up of :class:`ReloadJournal` for ``status``: ``outcome ==
    "error"`` flags that the last save did not compile (the live UI is stale),
    and ``seq`` lets a client tell a new reload from the one it already saw.
    """
    if journal is None:
        return None
    events = journal.recent(1)
    if not events:
        return None
    event = events[-1]
    return {"seq": event.seq, "outcome": event.outcome}


def _error_count(runtime_journal: Optional[RuntimeJournal]) -> int:
    """Count retained runtime events at ERROR/CRITICAL for ``status``.

    Covers both uncaught exceptions (excepthook / background thread) and
    swallowed callback exceptions the framework logs at ERROR, while excluding
    WARNING noise -- a nonzero count means "something failed at runtime". The
    count is cumulative over the journal's retained tail (a presence signal);
    drill into ``runtime_log`` for the detail.
    """
    if runtime_journal is None:
        return 0
    return sum(1 for event in runtime_journal.recent() if event.level in _STATUS_ERROR_LEVELS)


def _build_status(
    marshaller: _UIThreadMarshaller,
    journal: Optional[ReloadJournal],
    runtime_journal: Optional[RuntimeJournal],
    selection: Optional[Selection] = None,
) -> dict[str, Any]:
    """Aggregate a cheap liveness/health snapshot of the running app.

    A thin roll-up over existing primitives -- the app (title + blank-frame
    probe, read on the UI thread), the reload journal (newest reload outcome),
    and the runtime journal (retained error count) -- so an assistant can answer
    "is it up and healthy?" without the widget tree or a screenshot. Reaching
    this code at all means the bridge is up, so ``running`` is always ``True``;
    a *stopped* app surfaces earlier as a failed discovery on the client.
    """
    title, blank = marshaller.call_on_ui_thread(_probe_app)
    return {
        "running": True,
        "title": title,
        "blank": blank,
        "last_reload": _latest_reload(journal),
        "error_count": _error_count(runtime_journal),
        # A pull-only surface nobody calls does not exist. ``status`` is the
        # cheapest tool and the one called first, so it is the most reliable
        # place for an assistant to notice the human designated something (#591).
        "selection": selection.summary() if selection is not None else None,
    }


def _run_wait_for(marshaller: _UIThreadMarshaller, body: dict[str, Any]) -> dict[str, Any]:
    """Poll a tree condition until it holds or the timeout elapses.

    The loop stays on the HTTP worker thread: each poll marshals a
    :func:`~nuiitivet.dev.action.check_condition` (settle + evaluate) onto the
    UI thread, then the worker sleeps. Running the loop inside one UI-thread job
    would freeze the async work the caller is waiting on.

    Each gap between polls is the previous poll's duration, floored by
    ``min_interval`` and capped at a share of the time left: a poll costs
    O(tree), so a fixed gap would spin on a big tree and idle on a small one.

    Returns a structured result (never raises on timeout): ``satisfied`` is the
    outcome, ``timed_out`` distinguishes a miss from a hit, and ``waited`` /
    ``polls`` report the effort so the assistant can decide its next step.

    Raises:
        ValueError: If the condition is empty or the numeric params are invalid.
    """
    key = body.get("key")
    label = body.get("label")
    text = body.get("text")
    present = bool(body.get("present", True))
    if key is None and label is None and text is None:
        raise ValueError("wait_for needs one of: key, label, text")
    timeout = max(0.0, float(body.get("timeout", _WAIT_FOR_DEFAULT_TIMEOUT)))
    min_interval = max(0.0, float(body.get("min_interval", _WAIT_FOR_DEFAULT_MIN_INTERVAL)))

    condition = {"present": present}
    for name, value in (("key", key), ("label", label), ("text", text)):
        if value is not None:
            condition[name] = value

    started = time.monotonic()
    deadline = started + timeout
    polls = 0
    while True:
        polls += 1
        poll_started = time.monotonic()
        satisfied = bool(
            marshaller.call_on_ui_thread(
                lambda app: check_condition(
                    app, key=key, label=label, text=text, present=present
                )
            )
        )
        now = time.monotonic()
        if satisfied:
            return {
                "satisfied": True,
                "timed_out": False,
                "waited": round(now - started, 3),
                "polls": polls,
                "condition": condition,
            }
        remaining = deadline - now
        if remaining <= 0:
            return {
                "satisfied": False,
                "timed_out": True,
                "waited": round(now - started, 3),
                "polls": polls,
                "condition": condition,
            }
        # ``min`` outside ``max``, not a clamp: near the deadline the cap drops
        # below the floor, and a clamp with ``hi < lo`` is undefined.
        elapsed = now - poll_started
        time.sleep(
            max(
                0.0,
                min(
                    max(elapsed, min_interval),
                    remaining / _WAIT_FOR_REMAINING_SHARE,
                ),
            )
        )


def _make_handler(
    marshaller: _UIThreadMarshaller,
    journal: Optional[ReloadJournal],
    interaction_journal: Optional[InteractionJournal],
    runtime_journal: Optional[RuntimeJournal],
    runtime_capture: Optional[RuntimeLogCapture],
    selection: Optional[Selection] = None,
) -> type[BaseHTTPRequestHandler]:
    """Build the request handler class bound to ``marshaller`` and the journals."""

    class _Handler(BaseHTTPRequestHandler):
        # Silence the default stderr access log; the runner owns dev output.
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            logger.debug("dev bridge: " + format, *args)

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_png(self, data: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _fail(self, status: int, message: str) -> None:
            self._send_json(status, {"error": message})

        def _read_json_body(self) -> dict[str, Any]:
            """Parse the request body as a JSON object (``{}`` when empty)."""
            try:
                length = int(self.headers.get("Content-Length", 0))
            except (TypeError, ValueError):
                length = 0
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            if not raw:
                return {}
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def do_POST(self) -> None:  # noqa: N802 (http.server API)
            path = self.path.split("?", 1)[0].rstrip("/")
            try:
                body = self._read_json_body()
            except ValueError as exc:
                self._fail(400, f"invalid JSON body: {exc}")
                return
            try:
                if path == "/click":
                    result = marshaller.call_on_ui_thread(
                        lambda app: click(
                            app,
                            key=body.get("key"),
                            label=body.get("label"),
                            x=body.get("x"),
                            y=body.get("y"),
                            button=body.get("button"),
                        )
                    )
                elif path == "/scroll":
                    result = marshaller.call_on_ui_thread(
                        lambda app: scroll(
                            app,
                            key=body.get("key"),
                            label=body.get("label"),
                            x=body.get("x"),
                            y=body.get("y"),
                            dx=body.get("dx", 0.0),
                            dy=body.get("dy", 0.0),
                        )
                    )
                elif path == "/scroll_into_view":
                    result = marshaller.call_on_ui_thread(
                        lambda app: scroll_into_view(
                            app,
                            key=body.get("key"),
                            label=body.get("label"),
                            align=body.get("align", "nearest"),
                        )
                    )
                elif path == "/type":
                    result = marshaller.call_on_ui_thread(
                        lambda app: type_text(app, body.get("text", ""))
                    )
                elif path == "/key":
                    result = marshaller.call_on_ui_thread(
                        lambda app: press_key(app, body.get("key", ""), body.get("modifiers", 0))
                    )
                elif path == "/wait_for":
                    # Its own worker-thread poll loop; it marshals each poll onto
                    # the UI thread rather than running as one UI-thread job.
                    result = _run_wait_for(marshaller, body)
                elif path == "/runtime_log/verbose":
                    # A process-wide de-dup toggle -- no UI-thread hop, no app
                    # state touched. Absent when the bridge runs without capture
                    # (e.g. tests), reported as unsupported rather than silently
                    # ignored so a client is not misled about the mode.
                    if runtime_capture is None:
                        self._fail(404, "runtime log capture is not enabled")
                        return
                    enabled = bool(body.get("enabled", False))
                    result = {"verbose": runtime_capture.set_verbose(enabled)}
                else:
                    self._fail(404, f"unknown endpoint: {path}")
                    return
            except TimeoutError as exc:
                self._fail(504, str(exc))
            except TargetNotFoundError as exc:
                self._fail(404, str(exc))
            except (ValueError, KeyError) as exc:
                self._fail(400, f"{type(exc).__name__}: {exc}")
            except Exception as exc:
                logger.debug("dev bridge: action failed", exc_info=True)
                self._fail(500, f"{type(exc).__name__}: {exc}")
            else:
                self._send_json(200, result)

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            raw_path, _, query = self.path.partition("?")
            path = raw_path.rstrip("/")
            try:
                if path in ("", "/health"):
                    self._send_json(200, {"status": "ok"})
                elif path == "/status":
                    # A cheap liveness/health roll-up: title + blank-frame probe
                    # (one UI-thread hop) plus the reload/runtime journals. The
                    # positively-named alternative to a screenshot for "is it up
                    # and healthy?" (#420).
                    self._send_json(
                        200, _build_status(marshaller, journal, runtime_journal, selection)
                    )
                elif path == "/describe_tree":
                    tree = marshaller.call_on_ui_thread(lambda app: describe_tree(app.root))
                    self._send_json(200, {"tree": tree})
                elif path == "/describe_state":
                    # ``include_animations`` opts the per-frame ``Animatable``
                    # channels back in; they are filtered out by default because
                    # they dominated the payload (#418).
                    include_animations = _parse_flag(query, "include_animations")
                    state = marshaller.call_on_ui_thread(
                        lambda app: describe_state(
                            app.root, include_animations=include_animations
                        )
                    )
                    self._send_json(200, {"state": state})
                elif path == "/describe_selection":
                    # What the *human* pointed at, the mirror of describe_tree /
                    # describe_state. Read on the UI thread: the payload carries
                    # each member's live rect plus a scoped tree/state dump
                    # (#591).
                    self._send_json(
                        200,
                        marshaller.call_on_ui_thread(
                            lambda app: describe_selection(app.root, selection)
                        ),
                    )
                elif path == "/screenshot":
                    png = marshaller.call_on_ui_thread(lambda app: app._render_to_png_bytes())
                    self._send_png(png)
                elif path == "/reload_log":
                    # A plain buffer read -- no UI-thread hop needed; the journal
                    # is its own lock. Absent when the bridge runs without a
                    # controller (e.g. tests), which reads as an empty log.
                    events = (
                        journal.recent(_parse_limit(query)) if journal is not None else []
                    )
                    self._send_json(200, {"events": [event.to_dict() for event in events]})
                elif path == "/interaction_log":
                    # Like ``/reload_log``: a plain buffer read, no UI-thread hop.
                    # Absent when the bridge runs without a recorder (e.g. tests),
                    # which reads as an empty log.
                    actions = (
                        interaction_journal.recent(_parse_limit(query))
                        if interaction_journal is not None
                        else []
                    )
                    self._send_json(200, {"events": [action.to_dict() for action in actions]})
                elif path == "/runtime_log":
                    # Like ``/reload_log``: a plain buffer read, no UI-thread hop.
                    # Absent when the bridge runs without capture (e.g. tests),
                    # which reads as an empty log.
                    runtime_events = (
                        runtime_journal.recent(_parse_limit(query))
                        if runtime_journal is not None
                        else []
                    )
                    self._send_json(
                        200, {"events": [event.to_dict() for event in runtime_events]}
                    )
                elif path == "/runtime_log/verbose":
                    verbose = runtime_capture.is_verbose() if runtime_capture is not None else False
                    self._send_json(200, {"verbose": verbose})
                else:
                    self._fail(404, f"unknown endpoint: {path}")
            except TimeoutError as exc:
                self._fail(504, str(exc))
            except Exception as exc:
                logger.debug("dev bridge: request failed", exc_info=True)
                self._fail(500, f"{type(exc).__name__}: {exc}")

    return _Handler


class DevBridge:
    """The localhost control channel for one running dev app.

    Lifecycle mirrors :class:`~nuiitivet.dev.controller.HotReloadController`:
    :meth:`install` (register the UI-thread drain) then :meth:`start` before the
    event loop runs, and :meth:`shutdown` after it exits.
    """

    def __init__(
        self,
        app: "App",
        project_root: Path,
        *,
        host: str = "127.0.0.1",
        journal: Optional[ReloadJournal] = None,
        interaction_journal: Optional[InteractionJournal] = None,
        runtime_journal: Optional[RuntimeJournal] = None,
        runtime_capture: Optional[RuntimeLogCapture] = None,
        selection: Optional[Selection] = None,
    ) -> None:
        self._app = app
        self._project_root = project_root.resolve()
        self._host = host
        # Shared with the hot-reload controller, which records reload outcomes
        # into it; the bridge serves them at ``/reload_log`` (#388).
        self._journal = journal
        # Shared with the app's ``InteractionRecorder``, which records the human's
        # coarse UI actions into it; the bridge serves them at
        # ``/interaction_log`` (#390).
        self._interaction_journal = interaction_journal
        # Written by the runtime-log capture taps (log records + uncaught
        # exceptions); the bridge serves them at ``/runtime_log`` and toggles
        # verbose capture via the capture handle at ``/runtime_log/verbose`` (#409).
        self._runtime_journal = runtime_journal
        self._runtime_capture = runtime_capture
        # Written by the app's inspect mode when the human designates a widget;
        # the bridge serves it at ``/describe_selection`` (#591).
        self._selection = selection
        self._marshaller = _UIThreadMarshaller(app)
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._discovery_path: Optional[Path] = None

    @property
    def port(self) -> Optional[int]:
        """The bound port, or ``None`` before :meth:`start`."""
        if self._server is None:
            return None
        return int(self._server.server_address[1])

    def install(self) -> None:
        """Register the UI-thread drain (call before the event loop runs)."""
        self._marshaller.install()

    def start(self) -> None:
        """Bind the HTTP server and start serving on a background thread.

        Refuses to start outside a dev session -- the bridge is never opened in
        production.
        """
        if current_dev_session() is None:
            raise RuntimeError("DevBridge may only start under an active dev session")
        if self._server is not None:
            return

        handler = _make_handler(
            self._marshaller,
            self._journal,
            self._interaction_journal,
            self._runtime_journal,
            self._runtime_capture,
            self._selection,
        )
        self._server = ThreadingHTTPServer((self._host, 0), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="nuiitivet-dev-bridge",
            daemon=True,
        )
        self._thread.start()
        self._write_discovery()

    def _write_discovery(self) -> None:
        """Publish the bound port so CLI clients can find this app."""
        port = self.port
        if port is None:
            return
        directory = self._project_root / DISCOVERY_DIRNAME
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / DISCOVERY_FILENAME
            # ``pid`` lets clients detect a stale file left by a crashed app
            # (abnormal exit skips :meth:`shutdown`, so the file survives).
            payload = {"host": self._host, "port": port, "pid": os.getpid()}
            path.write_text(json.dumps(payload), encoding="utf-8")
            self._discovery_path = path
        except OSError:
            logger.debug("dev bridge: failed to write discovery file", exc_info=True)

    def shutdown(self) -> None:
        """Stop serving, remove the discovery file, and release the drain."""
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                logger.debug("dev bridge: server shutdown raised", exc_info=True)
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._discovery_path is not None:
            try:
                self._discovery_path.unlink(missing_ok=True)
            except OSError:
                logger.debug("dev bridge: failed to remove discovery file", exc_info=True)
            self._discovery_path = None
        self._marshaller.shutdown()
