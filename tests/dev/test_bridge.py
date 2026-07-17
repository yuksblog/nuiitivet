"""Tests for the dev bridge: gating, UI-thread marshalling, HTTP + discovery."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterator

import pytest

from nuiitivet.dev import session as dev_session
from nuiitivet.dev.bridge import DISCOVERY_DIRNAME, DISCOVERY_FILENAME, DevBridge
from nuiitivet.dev.client import BridgeClient, BridgeNotFoundError, find_discovery_file


class _FakeNode:
    def __init__(self, **identity: Any) -> None:
        self.children: list[_FakeNode] = []
        self.built_child = None
        self.global_layout_rect = (0, 0, 10, 10)
        for name, value in identity.items():
            setattr(self, name, value)


class _FakeApp:
    """Stand-in App: exposes ``.root`` and a cheap ``_render_to_png_bytes``."""

    _PNG = b"\x89PNG\r\n\x1a\n-fake-image-bytes"

    def __init__(self) -> None:
        self.root = _FakeNode(label="increment")

    def _render_to_png_bytes(self) -> bytes:
        return self._PNG


def _fake_app() -> Any:
    """Return a fake app typed as ``Any`` (DevBridge is annotated for ``App``)."""
    return _FakeApp()


def _port_of(bridge: DevBridge) -> int:
    port = bridge.port
    assert port is not None
    return port


@pytest.fixture
def dev_run() -> Iterator[None]:
    """Install a dev session for the duration of a test."""
    dev_session.set_dev_session(dev_session.DevSession())
    try:
        yield
    finally:
        dev_session.set_dev_session(None)


class _Pump:
    """Drives the marshaller drain on a background thread (fakes the UI loop)."""

    def __init__(self, bridge: DevBridge) -> None:
        self._drain = bridge._marshaller._drain
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._drain(0.0)
            time.sleep(0.002)

    def __enter__(self) -> "_Pump":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)


def test_bridge_refuses_without_session(tmp_path: Path) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    with pytest.raises(RuntimeError, match="dev session"):
        bridge.start()


def test_bridge_health_and_discovery(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        discovery = tmp_path / DISCOVERY_DIRNAME / DISCOVERY_FILENAME
        assert discovery.is_file()

        client = BridgeClient("127.0.0.1", _port_of(bridge))
        # /health does not touch the UI thread, so no pump is needed.
        body, _ = client._get("/health")
        assert b"ok" in body
    finally:
        bridge.shutdown()
    assert not (tmp_path / DISCOVERY_DIRNAME / DISCOVERY_FILENAME).exists()


def test_bridge_describe_tree_and_screenshot(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            tree = client.describe_tree()
            assert tree["type"] == "_FakeNode"
            assert tree["label"] == "increment"

            png = client.screenshot()
            assert png == _FakeApp._PNG
    finally:
        bridge.shutdown()


def test_bridge_request_timeout_without_pump(tmp_path: Path, dev_run: None) -> None:
    # No pump: the UI-thread job never runs, so the request times out (504).
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge._marshaller._drain_interval = 0.0
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge), timeout=3.0)
        # Shrink the server-side UI-call timeout so the test is quick.
        from nuiitivet.dev import bridge as bridge_mod

        original = bridge_mod._UI_CALL_TIMEOUT
        bridge_mod._UI_CALL_TIMEOUT = 0.2
        try:
            body, _ = client._get("/health")  # sanity: server is up
            assert b"ok" in body
            with pytest.raises(Exception):
                # urllib raises HTTPError (504) — any error is acceptable here.
                client.describe_tree()
        finally:
            bridge_mod._UI_CALL_TIMEOUT = original
    finally:
        bridge.shutdown()


def test_find_discovery_file_searches_parents(tmp_path: Path) -> None:
    root = tmp_path
    (root / DISCOVERY_DIRNAME).mkdir()
    disco = root / DISCOVERY_DIRNAME / DISCOVERY_FILENAME
    disco.write_text('{"host": "127.0.0.1", "port": 1234}', encoding="utf-8")

    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    assert find_discovery_file(nested) == disco


def test_discover_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(BridgeNotFoundError):
        BridgeClient.discover(tmp_path / "empty")


def _write_discovery(directory: Path, *, port: int, pid: int) -> Path:
    disco_dir = directory / DISCOVERY_DIRNAME
    disco_dir.mkdir(parents=True, exist_ok=True)
    path = disco_dir / DISCOVERY_FILENAME
    path.write_text(json.dumps({"host": "127.0.0.1", "port": port, "pid": pid}), encoding="utf-8")
    return path


def _dead_pid() -> int:
    """Spawn a trivial process, wait for it, and return its now-dead pid."""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_discover_removes_stale_file_for_dead_pid(tmp_path: Path) -> None:
    path = _write_discovery(tmp_path, port=59999, pid=_dead_pid())
    with pytest.raises(BridgeNotFoundError, match="no longer running"):
        BridgeClient.discover(tmp_path)
    # The stale file is cleaned up so the next discovery is a clean "not found".
    assert not path.exists()


def test_get_cleans_up_on_connection_refused(tmp_path: Path) -> None:
    # Port 1 is not listening: the connection is refused.
    path = _write_discovery(tmp_path, port=1, pid=0)
    client = BridgeClient("127.0.0.1", 1, timeout=2.0, discovery_path=path)
    with pytest.raises(BridgeNotFoundError):
        client.describe_tree()
    assert not path.exists()
