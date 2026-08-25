"""Tests for the subprocess-backed native file dialogs.

The backends shell out to OS helpers (osascript / zenity / kdialog /
PowerShell); tests fake ``subprocess.run`` so no real dialog ever opens and
every platform's command construction and result parsing is exercised on any
host.
"""

from __future__ import annotations

import asyncio
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import pytest

import nuiitivet.platform.file_dialog as fd
from nuiitivet.platform.file_dialog import (
    DummyFileDialogBackend,
    FileDialog,
    FileDialogError,
    LinuxFileDialogBackend,
    MacFileDialogBackend,
    WindowsFileDialogBackend,
)


class FakeRun:
    """Replaces ``subprocess.run``; records commands and plays back results."""

    def __init__(self, results):
        self.results = list(results)
        self.commands: list[list[str]] = []

    def __call__(self, cmd, capture_output=True, text=True):
        self.commands.append(list(cmd))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        returncode, stdout, stderr = result
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)


@pytest.fixture
def fake_run(monkeypatch):
    def install(*results) -> FakeRun:
        fake = FakeRun(results)
        monkeypatch.setattr(fd.subprocess, "run", fake)
        return fake

    return install


# --- macOS ------------------------------------------------------------------


class TestMacBackend:
    def test_open_file_returns_selected_path(self, fake_run):
        fake = fake_run((0, "/Users/me/pic.png\n", ""))
        selected = MacFileDialogBackend().open_file(
            title='Pick "one"', initial_dir=Path("/Users/me"), file_types=["png", "jpg"]
        )
        assert selected == Path("/Users/me/pic.png")
        [cmd] = fake.commands
        assert cmd[0] == "osascript"
        script = cmd[2]
        assert script.startswith("POSIX path of (choose file")
        assert 'with prompt "Pick \\"one\\""' in script
        assert 'of type {"png", "jpg"}' in script
        assert 'default location (POSIX file "/Users/me")' in script

    def test_cancel_is_none_even_with_localized_message(self, fake_run):
        fake_run((1, "", "execution error: ユーザによってキャンセルされました。 (-128)\n"))
        assert MacFileDialogBackend().open_file() is None

    def test_other_failure_raises(self, fake_run):
        fake_run((1, "", "execution error: some real problem (-1712)\n"))
        with pytest.raises(FileDialogError):
            MacFileDialogBackend().open_file()

    def test_open_files_parses_one_path_per_line(self, fake_run):
        fake = fake_run((0, "/Users/me/a, b.png\n/Users/me/c.png\n", ""))
        selected = MacFileDialogBackend().open_files(file_types=["png"])
        assert selected == [Path("/Users/me/a, b.png"), Path("/Users/me/c.png")]
        script = fake.commands[0][2]
        assert "with multiple selections allowed" in script
        assert 'of type {"png"}' in script

    def test_open_files_cancel_is_empty(self, fake_run):
        fake_run((1, "", "execution error: User canceled. (-128)\n"))
        assert MacFileDialogBackend().open_files() == []

    def test_save_file_builds_choose_file_name(self, fake_run):
        fake = fake_run((0, "/Users/me/out.txt\n", ""))
        selected = MacFileDialogBackend().save_file(default_name="out.txt")
        assert selected == Path("/Users/me/out.txt")
        assert 'choose file name default name "out.txt"' in fake.commands[0][2]

    def test_save_file_ignores_file_types(self, fake_run):
        fake = fake_run((0, "/Users/me/out.txt\n", ""))
        MacFileDialogBackend().save_file(default_name="out.txt", file_types=["txt"])
        assert "of type" not in fake.commands[0][2]

    def test_open_directory_builds_choose_folder(self, fake_run):
        fake = fake_run((0, "/Users/me/dir/\n", ""))
        selected = MacFileDialogBackend().open_directory()
        assert selected == Path("/Users/me/dir")
        assert "choose folder" in fake.commands[0][2]


# --- Linux ------------------------------------------------------------------


class TestLinuxBackend:
    def test_open_file_uses_zenity(self, fake_run):
        fake = fake_run((0, "/home/me/pic.png\n", ""))
        selected = LinuxFileDialogBackend().open_file(
            title="Pick", initial_dir=Path("/home/me"), file_types=["png"]
        )
        assert selected == Path("/home/me/pic.png")
        [cmd] = fake.commands
        assert cmd[:2] == ["zenity", "--file-selection"]
        assert "--title=Pick" in cmd
        assert "--filename=/home/me/" in cmd
        assert "--file-filter=*.png" in cmd

    def test_cancel_is_none(self, fake_run):
        fake_run((1, "", ""))
        assert LinuxFileDialogBackend().open_file() is None

    def test_missing_zenity_falls_back_to_kdialog(self, fake_run):
        fake = fake_run(FileNotFoundError("zenity"), (0, "/home/me/pic.png\n", ""))
        selected = LinuxFileDialogBackend().open_file()
        assert selected == Path("/home/me/pic.png")
        assert fake.commands[1][0] == "kdialog"
        assert fake.commands[1][1] == "--getopenfilename"

    def test_both_helpers_missing_raises(self, fake_run):
        fake_run(FileNotFoundError("zenity"), FileNotFoundError("kdialog"))
        with pytest.raises(FileDialogError, match="zenity"):
            LinuxFileDialogBackend().open_file()

    def test_helper_error_raises(self, fake_run):
        fake_run((255, "", "cannot open display\n"))
        with pytest.raises(FileDialogError, match="cannot open display"):
            LinuxFileDialogBackend().open_file()

    def test_open_files_uses_multiple_flag(self, fake_run):
        fake = fake_run((0, "/home/me/a.png\n/home/me/b.png\n", ""))
        selected = LinuxFileDialogBackend().open_files()
        assert selected == [Path("/home/me/a.png"), Path("/home/me/b.png")]
        assert "--multiple" in fake.commands[0]
        assert "--separator=\n" in fake.commands[0]

    def test_open_files_cancel_is_empty(self, fake_run):
        fake_run((1, "", ""))
        assert LinuxFileDialogBackend().open_files() == []

    def test_open_files_kdialog_fallback_separates_output(self, fake_run):
        fake = fake_run(FileNotFoundError("zenity"), (0, "/home/me/a.png\n", ""))
        selected = LinuxFileDialogBackend().open_files()
        assert selected == [Path("/home/me/a.png")]
        assert "--multiple" in fake.commands[1]
        assert "--separate-output" in fake.commands[1]

    def test_save_file_seeds_default_name(self, fake_run):
        fake = fake_run((0, "/home/me/out.txt\n", ""))
        LinuxFileDialogBackend().save_file(
            initial_dir=Path("/home/me"), default_name="out.txt"
        )
        assert "--save" in fake.commands[0]
        assert "--filename=/home/me/out.txt" in fake.commands[0]

    def test_save_file_filters_by_type(self, fake_run):
        fake = fake_run((0, "/home/me/out.csv\n", ""))
        LinuxFileDialogBackend().save_file(file_types=["csv"])
        assert "--file-filter=*.csv" in fake.commands[0]

    def test_open_directory_uses_directory_flag(self, fake_run):
        fake = fake_run((0, "/home/me/dir\n", ""))
        selected = LinuxFileDialogBackend().open_directory()
        assert selected == Path("/home/me/dir")
        assert "--directory" in fake.commands[0]


# --- Windows ----------------------------------------------------------------


class TestWindowsBackend:
    def test_open_file_builds_winforms_script(self, fake_run):
        fake = fake_run((0, "C:\\Users\\me\\pic.png\n", ""))
        selected = WindowsFileDialogBackend().open_file(
            title="Pick 'one'", initial_dir=Path("C:/Users/me"), file_types=["png", "jpg"]
        )
        assert selected == Path("C:\\Users\\me\\pic.png")
        [cmd] = fake.commands
        assert cmd[0] == "powershell"
        assert "-STA" in cmd
        script = cmd[-1]
        assert "OpenFileDialog" in script
        assert "$d.Title = 'Pick ''one'''" in script
        assert "$d.Filter = 'Files (*.png;*.jpg)|*.png;*.jpg|All files (*.*)|*.*'" in script

    def test_cancel_is_none(self, fake_run):
        fake_run((0, "", ""))
        assert WindowsFileDialogBackend().open_file() is None

    def test_failure_raises(self, fake_run):
        fake_run((1, "", "Add-Type : cannot load\n"))
        with pytest.raises(FileDialogError):
            WindowsFileDialogBackend().open_file()

    def test_open_files_sets_multiselect(self, fake_run):
        fake = fake_run((0, "C:\\Users\\me\\a.png\nC:\\Users\\me\\b.png\n", ""))
        selected = WindowsFileDialogBackend().open_files()
        assert selected == [Path("C:\\Users\\me\\a.png"), Path("C:\\Users\\me\\b.png")]
        script = fake.commands[0][-1]
        assert "$d.Multiselect = $true" in script
        assert "$d.FileNames | Write-Output" in script

    def test_open_files_cancel_is_empty(self, fake_run):
        fake_run((0, "", ""))
        assert WindowsFileDialogBackend().open_files() == []

    def test_save_file_uses_save_dialog(self, fake_run):
        fake = fake_run((0, "C:\\Users\\me\\out.txt\n", ""))
        WindowsFileDialogBackend().save_file(default_name="out.txt", file_types=["txt"])
        script = fake.commands[0][-1]
        assert "SaveFileDialog" in script
        assert "$d.FileName = 'out.txt'" in script
        assert "$d.Filter = 'Files (*.txt)|*.txt|All files (*.*)|*.*'" in script

    def test_open_directory_uses_folder_browser(self, fake_run):
        fake = fake_run((0, "C:\\Users\\me\n", ""))
        WindowsFileDialogBackend().open_directory(title="Where?")
        script = fake.commands[0][-1]
        assert "FolderBrowserDialog" in script
        assert "$d.Description = 'Where?'" in script


# --- Dummy & facade ---------------------------------------------------------


def test_dummy_backend_always_cancels():
    backend = DummyFileDialogBackend()
    assert backend.open_file() is None
    assert backend.open_files() == []
    assert backend.save_file() is None
    assert backend.open_directory() is None


class RecordingBackend(DummyFileDialogBackend):
    def __init__(self, result: Optional[Path]):
        self.result = result
        self.calls: list[tuple] = []

    def open_file(self, **kwargs):
        self.calls.append(("open_file", kwargs))
        return self.result

    def open_files(self, **kwargs):
        self.calls.append(("open_files", kwargs))
        return [self.result] if self.result else []

    def save_file(self, **kwargs):
        self.calls.append(("save_file", kwargs))
        return self.result

    def open_directory(self, **kwargs):
        self.calls.append(("open_directory", kwargs))
        return self.result


@pytest.mark.asyncio
async def test_facade_runs_backend_off_the_event_loop(monkeypatch):
    backend = RecordingBackend(Path("/picked/file.txt"))
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    selected = await FileDialog.open_file(
        title="Open", initial_dir="/somewhere", file_types=["txt"]
    )

    assert selected == Path("/picked/file.txt")
    assert backend.calls == [
        (
            "open_file",
            {
                "title": "Open",
                "initial_dir": Path("/somewhere"),
                "file_types": ["txt"],
            },
        )
    ]


@pytest.mark.asyncio
async def test_facade_open_files_returns_list(monkeypatch):
    backend = RecordingBackend(Path("/picked/a.png"))
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    selected = await FileDialog.open_files(file_types=["png"])

    assert selected == [Path("/picked/a.png")]
    [(name, kwargs)] = backend.calls
    assert name == "open_files"
    assert kwargs["file_types"] == ["png"]


@pytest.mark.asyncio
async def test_facade_open_files_cancel_is_empty(monkeypatch):
    backend = RecordingBackend(None)
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    assert await FileDialog.open_files() == []


@pytest.mark.asyncio
async def test_facade_expands_home_in_initial_dir(monkeypatch):
    backend = RecordingBackend(None)
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    await FileDialog.open_file(initial_dir="~/Pictures")

    [(_, kwargs)] = backend.calls
    assert kwargs["initial_dir"] == Path.home() / "Pictures"


@pytest.mark.asyncio
async def test_facade_forwards_save_file_types(monkeypatch):
    backend = RecordingBackend(Path("/saved/out.csv"))
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    selected = await FileDialog.save_file(default_name="out.csv", file_types=["csv"])

    assert selected == Path("/saved/out.csv")
    [(_, kwargs)] = backend.calls
    assert kwargs["file_types"] == ["csv"]


@pytest.mark.asyncio
async def test_facade_reports_cancel_as_none(monkeypatch):
    backend = RecordingBackend(None)
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    assert await FileDialog.save_file(default_name="a.txt") is None
    assert await FileDialog.open_directory() is None
    assert [name for name, _ in backend.calls] == ["save_file", "open_directory"]


class ThreadRecordingBackend(RecordingBackend):
    def open_file(self, **kwargs):
        self.thread = threading.current_thread()
        return super().open_file(**kwargs)


@pytest.mark.asyncio
async def test_facade_offloads_subprocess_backend_to_worker_thread(monkeypatch):
    backend = ThreadRecordingBackend(Path("/a"))
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    await FileDialog.open_file()

    assert backend.thread is not threading.current_thread()


@pytest.mark.asyncio
async def test_facade_runs_ui_thread_backend_on_the_calling_thread(monkeypatch):
    backend = ThreadRecordingBackend(Path("/a"))
    backend.runs_on_ui_thread = True
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    await FileDialog.open_file()

    assert backend.thread is threading.current_thread()


class OverlapProbeBackend(DummyFileDialogBackend):
    def __init__(self):
        self.active = 0
        self.overlapped = False

    def open_file(self, **kwargs):
        self.active += 1
        if self.active > 1:
            self.overlapped = True
        time.sleep(0.05)
        self.active -= 1
        return None


@pytest.mark.asyncio
async def test_facade_serializes_concurrent_dialogs(monkeypatch):
    backend = OverlapProbeBackend()
    monkeypatch.setattr(fd, "get_system_file_dialog_backend", lambda: backend)

    await asyncio.gather(FileDialog.open_file(), FileDialog.open_file())

    assert backend.overlapped is False


def test_backend_is_created_once(monkeypatch):
    monkeypatch.setattr(fd, "_backend", None)
    first = fd.get_system_file_dialog_backend()
    assert fd.get_system_file_dialog_backend() is first
