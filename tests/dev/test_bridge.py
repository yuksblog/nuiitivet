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
from nuiitivet.dev.interaction import InteractionJournal
from nuiitivet.dev.journal import ReloadJournal
from nuiitivet.dev.runtime_journal import RuntimeJournal


class _FakeNode:
    def __init__(self, **identity: Any) -> None:
        self.children: list[_FakeNode] = []
        self.built_child = None
        self.global_layout_rect = (0, 0, 10, 10)
        for name, value in identity.items():
            setattr(self, name, value)

    def layout(self, width: int, height: int) -> None:
        pass

    def clear_needs_layout(self) -> None:
        pass


class _FakeApp:
    """Stand-in App: exposes ``.root`` and a cheap ``_render_to_png_bytes``."""

    _PNG = b"\x89PNG\r\n\x1a\n-fake-image-bytes"

    def __init__(self) -> None:
        self.root = _FakeNode(key="submit", label="increment")
        self.width = 100
        self.height = 100
        self.title = "Counter"
        self.blank = False
        self.presses: list[tuple] = []
        self.texts: list[str] = []
        self.key_presses: list[tuple] = []

    def _render_to_png_bytes(self) -> bytes:
        return self._PNG

    def _frame_is_blank(self) -> bool:
        return self.blank

    def _dispatch_mouse_press(self, x: int, y: int, *, button: Any = None) -> None:
        self.presses.append((x, y, button))

    def _dispatch_mouse_release(self, x: int, y: int, *, button: Any = None) -> None:
        pass

    def _dispatch_text(self, text: str) -> bool:
        self.texts.append(text)
        return True

    def _dispatch_key_press(self, key: str, modifiers: int) -> bool:
        self.key_presses.append((key, modifiers))
        return True

    def _dispatch_key_release(self, key: str, modifiers: int) -> bool:
        return False

    def invalidate(self) -> None:
        pass


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


def test_bridge_describe_state(tmp_path: Path, dev_run: None) -> None:
    from nuiitivet.observable.value import Observable

    app: Any = _FakeApp()
    app.root._obs_count = Observable(7)
    bridge = DevBridge(app, tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            state = client.describe_state()
            assert state["type"] == "_FakeNode"
            assert state["state"] == {"count": 7}
    finally:
        bridge.shutdown()


def test_bridge_describe_state_include_animations(tmp_path: Path, dev_run: None) -> None:
    from nuiitivet.animation.animatable import Animatable
    from nuiitivet.observable.value import Observable

    app: Any = _FakeApp()
    app.root._obs_count = Observable(7)
    app.root._fade_anim = Animatable(0.5)
    bridge = DevBridge(app, tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            # The default filters the animation channel out...
            assert client.describe_state()["state"] == {"count": 7}
            # ...and the query argument carries the opt-in through the endpoint.
            state = client.describe_state(include_animations=True)
            assert state["state"] == {
                "count": 7,
                "fade_anim": {"value": 0.5, "kind": "computed"},
            }
    finally:
        bridge.shutdown()


def test_bridge_status_aggregates_signals(tmp_path: Path, dev_run: None) -> None:
    journal = ReloadJournal()
    journal.record_success(["pkg.a"])
    journal.record_error("Traceback...\nValueError: boom")
    runtime = RuntimeJournal()
    runtime.record(level="WARNING", source="logging", thread="t", message="noise")
    runtime.record(level="ERROR", source="thread", thread="w", message="RuntimeError: x")
    runtime.record(level="CRITICAL", source="excepthook", thread="MainThread", message="dead")

    app: Any = _FakeApp()
    app.blank = True
    bridge = DevBridge(app, tmp_path, journal=journal, runtime_journal=runtime)
    bridge.start()
    try:
        with _Pump(bridge):  # title + blank probe hop the UI thread
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            status = client.status()
            assert status["running"] is True
            assert status["title"] == "Counter"
            assert status["blank"] is True
            # Newest reload only, as {seq, outcome}; the failed save is latest.
            assert status["last_reload"] == {"seq": 2, "outcome": "error"}
            # ERROR + CRITICAL count; the WARNING is excluded as noise.
            assert status["error_count"] == 2
    finally:
        bridge.shutdown()


def test_bridge_status_defaults_without_journals(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            status = client.status()
            assert status["running"] is True
            assert status["last_reload"] is None
            assert status["error_count"] == 0
            assert status["blank"] is False
    finally:
        bridge.shutdown()


def test_bridge_reload_log_serves_journal(tmp_path: Path, dev_run: None) -> None:
    journal = ReloadJournal()
    journal.record_success(["pkg.a", "pkg.b"], changed=["pkg.a"])
    journal.record_error("Traceback...\nValueError: boom")

    bridge = DevBridge(_fake_app(), tmp_path, journal=journal)
    bridge.start()
    try:
        # /reload_log does not touch the UI thread, so no pump is needed.
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        events = client.reload_log()
        assert [e["outcome"] for e in events] == ["success", "error"]
        assert events[0]["modules"] == ["pkg.a", "pkg.b"]
        assert events[0]["changed"] == ["pkg.a"]
        assert "ValueError: boom" in events[1]["error"]
        assert events[0]["seq"] < events[1]["seq"]
    finally:
        bridge.shutdown()


def test_bridge_reload_log_respects_limit(tmp_path: Path, dev_run: None) -> None:
    journal = ReloadJournal()
    for i in range(4):
        journal.record_success([f"m{i}"])

    bridge = DevBridge(_fake_app(), tmp_path, journal=journal)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        events = client.reload_log(limit=2)
        assert [e["seq"] for e in events] == [3, 4]
    finally:
        bridge.shutdown()


def test_bridge_reload_log_empty_without_journal(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        assert client.reload_log() == []
    finally:
        bridge.shutdown()


def test_bridge_interaction_log_serves_journal(tmp_path: Path, dev_run: None) -> None:
    interaction = InteractionJournal()
    interaction.record_click({"type": "Button", "label": "increment"})
    interaction.record_key("s", ("ctrl",))
    interaction.record_text()

    bridge = DevBridge(_fake_app(), tmp_path, interaction_journal=interaction)
    bridge.start()
    try:
        # /interaction_log does not touch the UI thread, so no pump is needed.
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        events = client.interaction_log()
        assert [e["kind"] for e in events] == ["click", "key", "text"]
        assert events[0]["target"] == {"type": "Button", "label": "increment"}
        assert events[1]["key"] == "s" and events[1]["modifiers"] == ["ctrl"]
        assert "target" not in events[2] and "key" not in events[2]
        assert events[0]["seq"] < events[2]["seq"]
    finally:
        bridge.shutdown()


def test_bridge_interaction_log_respects_limit(tmp_path: Path, dev_run: None) -> None:
    interaction = InteractionJournal()
    for _ in range(4):
        interaction.record_text()

    bridge = DevBridge(_fake_app(), tmp_path, interaction_journal=interaction)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        events = client.interaction_log(limit=2)
        assert [e["seq"] for e in events] == [3, 4]
    finally:
        bridge.shutdown()


def test_bridge_interaction_log_empty_without_journal(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        assert client.interaction_log() == []
    finally:
        bridge.shutdown()


class _FakeCapture:
    """Stand-in for RuntimeLogCapture: records verbose toggles without globals."""

    def __init__(self, verbose: bool = False) -> None:
        self._verbose = verbose

    def set_verbose(self, enabled: bool) -> bool:
        self._verbose = bool(enabled)
        return self._verbose

    def is_verbose(self) -> bool:
        return self._verbose


def test_bridge_runtime_log_serves_journal(tmp_path: Path, dev_run: None) -> None:
    runtime = RuntimeJournal()
    runtime.record(level="WARNING", source="logging", thread="MainThread", message="heads up")
    runtime.record(
        level="ERROR",
        source="thread",
        thread="worker",
        message="RuntimeError: boom",
        exc_type="RuntimeError",
        traceback="Traceback...\nRuntimeError: boom",
    )

    bridge = DevBridge(_fake_app(), tmp_path, runtime_journal=runtime)
    bridge.start()
    try:
        # /runtime_log does not touch the UI thread, so no pump is needed.
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        events = client.runtime_log()
        assert [e["source"] for e in events] == ["logging", "thread"]
        assert events[0]["message"] == "heads up"
        assert events[1]["exc_type"] == "RuntimeError"
        assert "RuntimeError: boom" in events[1]["traceback"]
        assert events[0]["seq"] < events[1]["seq"]
    finally:
        bridge.shutdown()


def test_bridge_runtime_log_respects_limit(tmp_path: Path, dev_run: None) -> None:
    runtime = RuntimeJournal()
    for i in range(4):
        runtime.record(level="WARNING", source="logging", thread="t", message=f"m{i}")

    bridge = DevBridge(_fake_app(), tmp_path, runtime_journal=runtime)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        events = client.runtime_log(limit=2)
        assert [e["seq"] for e in events] == [3, 4]
    finally:
        bridge.shutdown()


def test_bridge_runtime_log_empty_without_journal(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        assert client.runtime_log() == []
    finally:
        bridge.shutdown()


def test_bridge_runtime_log_verbose_roundtrips(tmp_path: Path, dev_run: None) -> None:
    capture: Any = _FakeCapture()
    bridge = DevBridge(_fake_app(), tmp_path, runtime_capture=capture)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        assert client.runtime_log_verbose() is False
        assert client.set_runtime_log_verbose(True) is True
        assert client.runtime_log_verbose() is True
        assert client.set_runtime_log_verbose(False) is False
    finally:
        bridge.shutdown()


def test_bridge_runtime_log_verbose_without_capture_is_404(
    tmp_path: Path, dev_run: None
) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        # No capture wired: reading state is a benign False...
        assert client.runtime_log_verbose() is False
        # ...but attempting to set it is refused rather than silently ignored.
        with pytest.raises(RuntimeError, match="not enabled"):
            client.set_runtime_log_verbose(True)
    finally:
        bridge.shutdown()


def test_bridge_click_by_key(tmp_path: Path, dev_run: None) -> None:
    app: Any = _FakeApp()
    bridge = DevBridge(app, tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            result = client.click(key="submit")
            # Center of the root's (0, 0, 10, 10) rect is (5, 5).
            assert result["x"] == 5 and result["y"] == 5
            assert result["clicked"]["key"] == "submit"
            assert app.presses == [(5, 5, None)]
    finally:
        bridge.shutdown()


def test_bridge_type_and_key(tmp_path: Path, dev_run: None) -> None:
    app: Any = _FakeApp()
    bridge = DevBridge(app, tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            assert client.type_text("hi")["typed"] == "hi"
            assert app.texts == ["hi"]

            result = client.key("enter", modifiers=["accel"])
            assert result["handled"] is True
            assert app.key_presses and app.key_presses[0][0] == "enter"
            assert app.key_presses[0][1] != 0  # a modifier mask was applied
    finally:
        bridge.shutdown()


def test_bridge_click_missing_target_is_404(tmp_path: Path, dev_run: None) -> None:
    app: Any = _FakeApp()
    bridge = DevBridge(app, tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            with pytest.raises(RuntimeError, match="no widget matched"):
                client.click(key="does-not-exist")
    finally:
        bridge.shutdown()


def test_bridge_wait_for_satisfied_immediately(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            result = client.wait_for(label="increment", timeout=1.0)
            assert result["satisfied"] is True
            assert result["timed_out"] is False
            assert result["condition"] == {"present": True, "label": "increment"}
    finally:
        bridge.shutdown()


def test_bridge_wait_for_times_out(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            result = client.wait_for(label="never", timeout=0.15, interval=0.02)
            assert result["satisfied"] is False
            assert result["timed_out"] is True
            assert result["polls"] >= 1
    finally:
        bridge.shutdown()


def test_bridge_wait_for_becomes_present(tmp_path: Path, dev_run: None) -> None:
    app: Any = _FakeApp()
    bridge = DevBridge(app, tmp_path)
    bridge.start()

    def add_later() -> None:
        time.sleep(0.1)
        app.root.children.append(_FakeNode(label="Loaded"))

    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            worker = threading.Thread(target=add_later)
            worker.start()
            result = client.wait_for(label="Loaded", timeout=2.0, interval=0.02)
            worker.join()
            assert result["satisfied"] is True
            assert result["polls"] >= 2  # it did not pass on the first poll
    finally:
        bridge.shutdown()


def test_bridge_wait_for_absent(tmp_path: Path, dev_run: None) -> None:
    app: Any = _FakeApp()
    app.root.children.append(_FakeNode(key="spinner"))
    bridge = DevBridge(app, tmp_path)
    bridge.start()

    def clear_later() -> None:
        time.sleep(0.1)
        app.root.children.clear()

    try:
        with _Pump(bridge):
            client = BridgeClient("127.0.0.1", _port_of(bridge))
            worker = threading.Thread(target=clear_later)
            worker.start()
            result = client.wait_for(key="spinner", present=False, timeout=2.0, interval=0.02)
            worker.join()
            assert result["satisfied"] is True
            assert result["condition"] == {"present": False, "key": "spinner"}
    finally:
        bridge.shutdown()


def test_bridge_wait_for_empty_condition_is_400(tmp_path: Path, dev_run: None) -> None:
    bridge = DevBridge(_fake_app(), tmp_path)
    bridge.start()
    try:
        client = BridgeClient("127.0.0.1", _port_of(bridge))
        # No key/label/text: the bridge rejects it before touching the UI thread.
        with pytest.raises(RuntimeError, match="one of"):
            client.wait_for()
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
