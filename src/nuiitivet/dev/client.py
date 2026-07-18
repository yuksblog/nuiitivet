"""Client side of the dev bridge: discover a running app and call it.

The CLI subcommands (``python -m nuiitivet.dev screenshot`` /
``describe-tree``) run in a *separate* process from the app. They locate the
running bridge by reading the discovery file the app wrote
(``<project_root>/.nuiitivet/dev-bridge.json``), then issue plain HTTP GETs.
Kept dependency-free (``urllib``) so the CLI has no runtime requirements beyond
the standard library.

A crashed app exits without running :meth:`DevBridge.shutdown`, leaving a stale
discovery file behind. Clients defend against this two ways: the file records
the app's ``pid`` and is ignored (and removed) when that process is gone, and a
connection refused at request time is likewise treated as a dead bridge and
cleans the file up.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .bridge import DISCOVERY_DIRNAME, DISCOVERY_FILENAME


class BridgeNotFoundError(RuntimeError):
    """No running dev bridge could be discovered (or it is no longer alive)."""


_NOT_RUNNING_HINT = (
    "No running nuiitivet dev app found. Start one with "
    "'python -m nuiitivet.dev <app.py>' first."
)


def _pid_alive_windows(pid: int) -> bool:
    """Windows process-existence probe.

    ``os.kill(pid, 0)`` must never be used here: on Windows CPython maps
    ``os.kill`` to ``TerminateProcess``, so signal 0 would *kill* a live process
    rather than probe it. Instead open the process for ``SYNCHRONIZE`` and ask
    whether its handle is signaled -- a running process is not signaled
    (``WAIT_TIMEOUT``); an exited one is.
    """
    if sys.platform != "win32":  # pragma: no cover - narrows platform for mypy
        return True
    import ctypes
    from ctypes import wintypes

    PROCESS_SYNCHRONIZE = 0x00100000
    ERROR_ACCESS_DENIED = 5
    WAIT_TIMEOUT = 0x00000102

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

    handle = kernel32.OpenProcess(PROCESS_SYNCHRONIZE, False, pid)
    if not handle:
        # No handle: the pid is gone, unless we were merely denied access (the
        # process exists but is owned by another user) -- treat that as alive.
        return kernel32.GetLastError() == ERROR_ACCESS_DENIED
    try:
        return kernel32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)


def _pid_alive(pid: int) -> bool:
    """Return whether a process with ``pid`` currently exists (cross-platform).

    POSIX (macOS/Linux) uses ``os.kill(pid, 0)``, which sends no signal and only
    probes existence; a ``PermissionError`` means the process exists but is owned
    by someone else, which still counts as alive. Windows uses a non-destructive
    handle probe (see :func:`_pid_alive_windows`).
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            return _pid_alive_windows(pid)
        except OSError:
            # If the probe itself fails, assume alive so a valid discovery file
            # is never deleted out from under a running app.
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def find_discovery_file(start: Optional[Path] = None) -> Optional[Path]:
    """Search ``start`` and its parents for the bridge discovery file.

    Args:
        start: Directory to begin the upward search from (defaults to cwd).

    Returns:
        The path to the discovery file, or ``None`` if none was found.
    """
    directory = (start or Path.cwd()).resolve()
    for candidate in (directory, *directory.parents):
        path = candidate / DISCOVERY_DIRNAME / DISCOVERY_FILENAME
        if path.is_file():
            return path
    return None


def _unlink_quietly(path: Optional[Path]) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _extract_error(exc: URLError) -> str:
    """Pull the server's ``{"error": ...}`` message out of a failed response.

    HTTP error responses still carry a body; the bridge puts a human-readable
    reason there. Fall back to the raw exception text if it cannot be decoded.
    """
    body = getattr(exc, "read", None)
    if callable(body):
        try:
            payload = json.loads(exc.read().decode("utf-8"))  # type: ignore[attr-defined]
            if isinstance(payload, dict) and payload.get("error"):
                return str(payload["error"])
        except Exception:
            pass
    return str(exc)


class BridgeClient:
    """A thin HTTP client for one discovered dev bridge."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        timeout: float = 10.0,
        discovery_path: Optional[Path] = None,
    ) -> None:
        self._base = f"http://{host}:{port}"
        self._timeout = timeout
        # Set when discovered from a file, so a dead bridge can be cleaned up.
        self._discovery_path = discovery_path

    @classmethod
    def discover(cls, start: Optional[Path] = None, *, timeout: float = 10.0) -> "BridgeClient":
        """Locate the running bridge via its discovery file.

        A file whose recorded ``pid`` no longer exists is treated as stale: it is
        removed and discovery fails as if no app were running.

        Raises:
            BridgeNotFoundError: If no live discovery file could be found.
        """
        path = find_discovery_file(start)
        if path is None:
            raise BridgeNotFoundError(_NOT_RUNNING_HINT)
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
            host = str(info["host"])
            port = int(info["port"])
            pid = int(info.get("pid", 0))
        except (OSError, ValueError, KeyError) as exc:
            raise BridgeNotFoundError(f"Bridge discovery file is invalid: {path} ({exc})") from exc

        if pid and not _pid_alive(pid):
            _unlink_quietly(path)
            raise BridgeNotFoundError(
                f"The dev app (pid {pid}) that wrote {path} is no longer running. "
                "Start one with 'python -m nuiitivet.dev <app.py>'."
            )

        return cls(host, port, timeout=timeout, discovery_path=path)

    def _get(self, endpoint: str) -> tuple[bytes, str]:
        """GET ``endpoint``; return ``(body, content_type)``.

        A connection refused means the bridge is gone (crashed without cleanup);
        the stale discovery file is removed and :class:`BridgeNotFoundError` is
        raised.
        """
        try:
            with urlopen(f"{self._base}{endpoint}", timeout=self._timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                return response.read(), content_type
        except URLError as exc:
            if isinstance(exc.reason, ConnectionError):
                _unlink_quietly(self._discovery_path)
                raise BridgeNotFoundError(_NOT_RUNNING_HINT) from exc
            raise

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST ``payload`` as JSON to ``endpoint``; return the decoded response.

        A connection refused is treated as a dead bridge (see :meth:`_get`). An
        error status carries the server's ``{"error": ...}`` message through as a
        :class:`RuntimeError` so the CLI can print something actionable.
        """
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self._base}{endpoint}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            if isinstance(exc.reason, ConnectionError):
                _unlink_quietly(self._discovery_path)
                raise BridgeNotFoundError(_NOT_RUNNING_HINT) from exc
            message = _extract_error(exc)
            raise RuntimeError(message) from exc

    def describe_tree(self) -> dict[str, Any]:
        """Fetch the structural tree description from the running app."""
        body, _ = self._get("/describe_tree")
        payload = json.loads(body.decode("utf-8"))
        return payload.get("tree", {})

    def reload_log(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """Fetch recent hot-reload events from the running app (#388).

        Each event is ``{"seq", "timestamp", "outcome", optional "modules",
        "changed", optional "error"}``, oldest-first. ``changed`` lists the
        modules whose source actually changed (empty for a no-op save). ``limit``
        caps the result to the newest ``limit`` events; ``None`` returns all
        retained events.
        """
        endpoint = "/reload_log" if limit is None else f"/reload_log?limit={int(limit)}"
        body, _ = self._get(endpoint)
        payload = json.loads(body.decode("utf-8"))
        return payload.get("events", [])

    def screenshot(self) -> bytes:
        """Fetch a PNG screenshot of the running app's current frame."""
        body, content_type = self._get("/screenshot")
        if "image/png" not in content_type:
            raise RuntimeError(f"expected image/png, got {content_type!r}: {body[:200]!r}")
        return body

    def click(
        self,
        *,
        key: Optional[str] = None,
        label: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        button: Optional[int] = None,
    ) -> dict[str, Any]:
        """Click a widget by ``key`` / ``label`` (or raw ``x`` / ``y``)."""
        payload: dict[str, Any] = {}
        if key is not None:
            payload["key"] = key
        if label is not None:
            payload["label"] = label
        if x is not None:
            payload["x"] = x
        if y is not None:
            payload["y"] = y
        if button is not None:
            payload["button"] = button
        return self._post("/click", payload)

    def type_text(self, text: str) -> dict[str, Any]:
        """Type ``text`` into the running app's focused widget."""
        return self._post("/type", {"text": text})

    def key(self, name: str, modifiers: Optional[list[str]] = None) -> dict[str, Any]:
        """Press a key ``name`` with optional modifier names (e.g. ``["accel"]``)."""
        payload: dict[str, Any] = {"key": name}
        if modifiers:
            payload["modifiers"] = modifiers
        return self._post("/key", payload)
