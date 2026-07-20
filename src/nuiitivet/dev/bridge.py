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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from .action import TargetNotFoundError, click, press_key, type_text
from .interaction import InteractionJournal
from .journal import ReloadJournal
from .perception import describe_state, describe_tree
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


def _make_handler(
    marshaller: _UIThreadMarshaller,
    journal: Optional[ReloadJournal],
    interaction_journal: Optional[InteractionJournal],
    runtime_journal: Optional[RuntimeJournal],
    runtime_capture: Optional[RuntimeLogCapture],
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
                elif path == "/type":
                    result = marshaller.call_on_ui_thread(
                        lambda app: type_text(app, body.get("text", ""))
                    )
                elif path == "/key":
                    result = marshaller.call_on_ui_thread(
                        lambda app: press_key(app, body.get("key", ""), body.get("modifiers", 0))
                    )
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
                elif path == "/describe_tree":
                    tree = marshaller.call_on_ui_thread(lambda app: describe_tree(app.root))
                    self._send_json(200, {"tree": tree})
                elif path == "/describe_state":
                    state = marshaller.call_on_ui_thread(lambda app: describe_state(app.root))
                    self._send_json(200, {"state": state})
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
