"""Tests for the subprocess-backed desktop notifications.

The fallback backends shell out to OS helpers (osascript / notify-send /
PowerShell); tests fake ``subprocess.Popen`` so no real notification is ever
raised and every platform's command construction is exercised on any host.
The in-process backends (Cocoa, Win32) need their native platform and are
covered by the backend-selection fallback tests only.
"""

from __future__ import annotations

import threading

import pytest

import nuiitivet.platform.notification as pn
from nuiitivet.platform.desktop import Desktop
from nuiitivet.platform.notification import (
    DummyNotificationBackend,
    LinuxNotificationBackend,
    MacNotificationBackend,
    NotificationBackend,
    NotificationError,
    WindowsNotificationBackend,
    _applescript_quote,
    notify,
)


class FakePopen:
    """Replaces ``subprocess.Popen``; records commands and failures to raise."""

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.commands: list[list[str]] = []

    def __call__(self, cmd, **kwargs):
        self.commands.append(list(cmd))
        if self.error is not None:
            raise self.error
        return object()


@pytest.fixture
def fake_popen(monkeypatch):
    def install(error: Exception | None = None) -> FakePopen:
        fake = FakePopen(error)
        monkeypatch.setattr(pn.subprocess, "Popen", fake)
        return fake

    return install


# --- AppleScript quoting ----------------------------------------------------


def test_applescript_quote_escapes_quotes_and_backslashes():
    assert _applescript_quote('say "hi" \\ now') == '("say \\"hi\\" \\\\ now")'


def test_applescript_quote_emits_linefeed_for_newlines():
    assert _applescript_quote("a\nb") == '("a" & linefeed & "b")'
    assert _applescript_quote("a\r\nb") == '("a" & linefeed & "b")'


# --- macOS ------------------------------------------------------------------


class TestMacBackend:
    def test_notify_builds_display_notification_script(self, fake_popen):
        fake = fake_popen()
        MacNotificationBackend().notify("Import done", 'All "rows" written')
        [cmd] = fake.commands
        assert cmd[:2] == ["osascript", "-e"]
        assert cmd[2] == (
            'display notification ("All \\"rows\\" written")'
            ' with title ("Import done")'
        )

    def test_launch_failure_raises(self, fake_popen):
        fake_popen(OSError("no osascript"))
        with pytest.raises(NotificationError):
            MacNotificationBackend().notify("t", "b")


# --- Linux ------------------------------------------------------------------


class TestLinuxBackend:
    def test_notify_builds_notify_send_command(self, fake_popen):
        fake = fake_popen()
        LinuxNotificationBackend().notify("-Title", "Body text")
        # ``--`` keeps a leading-dash title from being read as an option.
        assert fake.commands == [["notify-send", "--", "-Title", "Body text"]]

    def test_empty_body_is_omitted(self, fake_popen):
        fake = fake_popen()
        LinuxNotificationBackend().notify("Title", "")
        assert fake.commands == [["notify-send", "--", "Title"]]

    def test_missing_helper_raises(self, fake_popen):
        fake_popen(FileNotFoundError("notify-send"))
        with pytest.raises(NotificationError, match="libnotify"):
            LinuxNotificationBackend().notify("t", "b")


# --- Windows ----------------------------------------------------------------


class TestWindowsBackend:
    def test_notify_builds_winrt_toast_script(self, fake_popen):
        fake = fake_popen()
        WindowsNotificationBackend().notify("Import done", "It's finished")
        [cmd] = fake.commands
        assert cmd[:3] == ["powershell", "-NoProfile", "-Command"]
        script = cmd[3]
        assert "ToastNotificationManager" in script
        assert "$xml.CreateTextNode('Import done')" in script
        assert "$xml.CreateTextNode('It''s finished')" in script
        assert "WindowsPowerShell" in script  # borrowed AUMID

    def test_launch_failure_raises(self, fake_popen):
        fake_popen(OSError("no powershell"))
        with pytest.raises(NotificationError):
            WindowsNotificationBackend().notify("t", "b")


# --- Dummy ------------------------------------------------------------------


def test_dummy_backend_is_a_noop(fake_popen):
    fake = fake_popen()
    DummyNotificationBackend().notify("t", "b")
    assert fake.commands == []


# --- backend selection ------------------------------------------------------


class TestBackendSelection:
    def test_darwin_falls_back_to_osascript_without_a_bundle(self, monkeypatch):
        # On macOS the in-process backend refuses to construct without a
        # bundle identifier; elsewhere the module does not even import. Both
        # land on the osascript backend.
        monkeypatch.setattr(pn.sys, "platform", "darwin")
        assert isinstance(pn._create_backend(), MacNotificationBackend)

    def test_linux_uses_notify_send(self, monkeypatch):
        monkeypatch.setattr(pn.sys, "platform", "linux")
        assert isinstance(pn._create_backend(), LinuxNotificationBackend)

    def test_win32_falls_back_to_powershell_off_windows(self, monkeypatch):
        monkeypatch.setattr(pn.sys, "platform", "win32")
        assert isinstance(pn._create_backend(), WindowsNotificationBackend)

    def test_unknown_platform_gets_dummy(self, monkeypatch):
        monkeypatch.setattr(pn.sys, "platform", "beos")
        assert isinstance(pn._create_backend(), DummyNotificationBackend)

    def test_backend_is_created_once(self, monkeypatch):
        monkeypatch.setattr(pn, "_backend", None)
        first = pn.get_system_notification_backend()
        assert pn.get_system_notification_backend() is first


# --- facade -----------------------------------------------------------------


class RecordingBackend(NotificationBackend):
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[tuple[str, str]] = []
        self.thread: threading.Thread | None = None

    def notify(self, title: str, body: str) -> None:
        self.calls.append((title, body))
        self.thread = threading.current_thread()
        if self.error is not None:
            raise self.error


def test_notify_forwards_title_and_body(monkeypatch):
    backend = RecordingBackend()
    monkeypatch.setattr(pn, "get_system_notification_backend", lambda: backend)
    notify("Import done", "1000 rows written")
    assert backend.calls == [("Import done", "1000 rows written")]


def test_notify_defaults_body_to_empty(monkeypatch):
    backend = RecordingBackend()
    monkeypatch.setattr(pn, "get_system_notification_backend", lambda: backend)
    notify("Just a title")
    assert backend.calls == [("Just a title", "")]


def test_notify_never_raises(monkeypatch):
    backend = RecordingBackend(NotificationError("platform refused"))
    monkeypatch.setattr(pn, "get_system_notification_backend", lambda: backend)
    notify("t", "b")  # must not raise
    assert backend.calls == [("t", "b")]


def test_desktop_namespace_delegates_to_notify(monkeypatch):
    backend = RecordingBackend()
    monkeypatch.setattr(pn, "get_system_notification_backend", lambda: backend)
    Desktop.notify("Import done", "1,000 rows written")
    Desktop.notify("Just a title")
    assert backend.calls == [
        ("Import done", "1,000 rows written"),
        ("Just a title", ""),
    ]


def test_notify_is_callable_from_a_worker_thread(monkeypatch):
    backend = RecordingBackend()
    monkeypatch.setattr(pn, "get_system_notification_backend", lambda: backend)
    worker = threading.Thread(target=lambda: notify("from worker"))
    worker.start()
    worker.join()
    assert backend.calls == [("from worker", "")]
    assert backend.thread is worker
