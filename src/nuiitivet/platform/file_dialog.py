"""Native file dialogs (open file / save file / open directory).

This module is OS-dependent but backend-agnostic. Each platform shells out to
an OS helper process (``osascript`` on macOS, ``zenity``/``kdialog`` on Linux,
PowerShell on Windows) instead of hosting a second GUI toolkit in-process:
tkinter's Tk mainloop cannot coexist with the pyglet-owned ``NSApplication``
on macOS.

The backend methods block until the dialog is dismissed. Applications use the
async :class:`FileDialog` facade, which runs the blocking call in a worker
thread so the UI keeps painting.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional, Sequence, TypeVar, Union

from nuiitivet.common.logging_once import exception_once


logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class FileDialogError(RuntimeError):
    """A dialog could not be shown (helper missing or helper failed).

    Distinct from cancellation: the user cancelling a dialog returns ``None``,
    never raises.
    """


class FileDialogBackend(ABC):
    """Blocking per-platform dialog implementation.

    All methods return the selected path, or ``None`` if the user cancelled,
    and raise :class:`FileDialogError` when the dialog could not be shown.

    ``runs_on_ui_thread`` declares where the blocking call must run: ``False``
    for subprocess backends (the facade offloads them to a worker thread so
    the UI keeps painting), ``True`` for in-process native backends whose
    toolkit is main-thread-only (the facade calls them directly; the native
    modal loop then owns the thread while the dialog is up).
    """

    runs_on_ui_thread: bool = False

    @abstractmethod
    def open_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        raise NotImplementedError

    @abstractmethod
    def open_files(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> list[Path]:
        """Like :meth:`open_file` with multiple selection; cancel is ``[]``."""
        raise NotImplementedError

    @abstractmethod
    def save_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        default_name: Optional[str] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        raise NotImplementedError

    @abstractmethod
    def open_directory(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        raise NotImplementedError


def _applescript_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


class MacFileDialogBackend(FileDialogBackend):
    """macOS dialogs via ``osascript`` (AppleScript ``choose file`` family)."""

    def open_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        return self._run(self._choose_file_expr(title, initial_dir, file_types))

    def open_files(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> list[Path]:
        expr = self._choose_file_expr(title, initial_dir, file_types)
        expr += " with multiple selections allowed"
        # ``choose file`` returns an AppleScript list here; emit one POSIX
        # path per line so parsing never fights commas in file names.
        script = (
            f"set fs to {expr}\n"
            'set out to ""\n'
            "repeat with f in fs\n"
            "    set out to out & POSIX path of f & linefeed\n"
            "end repeat\n"
            "out"
        )
        out = self._run_script(script)
        if out is None:
            return []
        return [Path(line) for line in out.splitlines() if line]

    @staticmethod
    def _choose_file_expr(
        title: Optional[str],
        initial_dir: Optional[Path],
        file_types: Optional[Sequence[str]],
    ) -> str:
        script = "choose file"
        if title:
            script += f" with prompt {_applescript_quote(title)}"
        if file_types:
            types = ", ".join(_applescript_quote(ext) for ext in file_types)
            script += f" of type {{{types}}}"
        if initial_dir:
            script += f" default location (POSIX file {_applescript_quote(str(initial_dir))})"
        return script

    def save_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        default_name: Optional[str] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        # AppleScript's ``choose file name`` has no type filter; ``file_types``
        # has no effect on macOS.
        script = "choose file name"
        if title:
            script += f" with prompt {_applescript_quote(title)}"
        if default_name:
            script += f" default name {_applescript_quote(default_name)}"
        if initial_dir:
            script += f" default location (POSIX file {_applescript_quote(str(initial_dir))})"
        return self._run(script)

    def open_directory(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        script = "choose folder"
        if title:
            script += f" with prompt {_applescript_quote(title)}"
        if initial_dir:
            script += f" default location (POSIX file {_applescript_quote(str(initial_dir))})"
        return self._run(script)

    def _run(self, choose_expr: str) -> Optional[Path]:
        out = self._run_script(f"POSIX path of ({choose_expr})")
        return Path(out.strip()) if out is not None else None

    def _run_script(self, script: str) -> Optional[str]:
        """Run an AppleScript; ``None`` means the user cancelled."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise FileDialogError(f"osascript could not be launched: {exc}") from exc
        if result.returncode == 0:
            return result.stdout
        # AppleScript reports user cancellation as error -128; the message text
        # is localized, so match the error number, not the words.
        if "-128" in result.stderr:
            return None
        raise FileDialogError(f"osascript failed: {result.stderr.strip()}")


class LinuxFileDialogBackend(FileDialogBackend):
    """Linux dialogs via ``zenity``, falling back to ``kdialog``."""

    def open_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        patterns = [f"*.{ext}" for ext in file_types] if file_types else None
        zenity = ["zenity", "--file-selection"]
        if title:
            zenity.append(f"--title={title}")
        if initial_dir:
            zenity.append(f"--filename={initial_dir}/")
        if patterns:
            zenity.append(f"--file-filter={' '.join(patterns)}")
            zenity.append("--file-filter=All files | *")
        kdialog = ["kdialog", "--getopenfilename", str(initial_dir or Path.home())]
        if patterns:
            kdialog.append(" ".join(patterns))
        if title:
            kdialog += ["--title", title]
        return self._run(zenity, kdialog)

    def open_files(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> list[Path]:
        patterns = [f"*.{ext}" for ext in file_types] if file_types else None
        zenity = ["zenity", "--file-selection", "--multiple", "--separator=\n"]
        if title:
            zenity.append(f"--title={title}")
        if initial_dir:
            zenity.append(f"--filename={initial_dir}/")
        if patterns:
            zenity.append(f"--file-filter={' '.join(patterns)}")
            zenity.append("--file-filter=All files | *")
        kdialog = ["kdialog", "--getopenfilename", str(initial_dir or Path.home())]
        if patterns:
            kdialog.append(" ".join(patterns))
        kdialog += ["--multiple", "--separate-output"]
        if title:
            kdialog += ["--title", title]
        out = self._run_raw(zenity, kdialog)
        if out is None:
            return []
        return [Path(line) for line in out.splitlines() if line]

    def save_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        default_name: Optional[str] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        patterns = [f"*.{ext}" for ext in file_types] if file_types else None
        zenity = ["zenity", "--file-selection", "--save"]
        if title:
            zenity.append(f"--title={title}")
        if initial_dir or default_name:
            start = Path(initial_dir or Path.home()) / (default_name or "")
            zenity.append(f"--filename={start}")
        if patterns:
            zenity.append(f"--file-filter={' '.join(patterns)}")
            zenity.append("--file-filter=All files | *")
        kdialog_start = Path(initial_dir or Path.home()) / (default_name or "")
        kdialog = ["kdialog", "--getsavefilename", str(kdialog_start)]
        if patterns:
            kdialog.append(" ".join(patterns))
        if title:
            kdialog += ["--title", title]
        return self._run(zenity, kdialog)

    def open_directory(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        zenity = ["zenity", "--file-selection", "--directory"]
        if title:
            zenity.append(f"--title={title}")
        if initial_dir:
            zenity.append(f"--filename={initial_dir}/")
        kdialog = ["kdialog", "--getexistingdirectory", str(initial_dir or Path.home())]
        if title:
            kdialog += ["--title", title]
        return self._run(zenity, kdialog)

    def _run(self, zenity_cmd: list[str], kdialog_cmd: list[str]) -> Optional[Path]:
        out = self._run_raw(zenity_cmd, kdialog_cmd)
        if out is None:
            return None
        selected = out.strip()
        return Path(selected) if selected else None

    def _run_raw(self, zenity_cmd: list[str], kdialog_cmd: list[str]) -> Optional[str]:
        """Run the first available helper; ``None`` means the user cancelled."""
        for cmd in (zenity_cmd, kdialog_cmd):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise FileDialogError(f"{cmd[0]} could not be launched: {exc}") from exc
            if result.returncode == 0:
                return result.stdout
            if result.returncode == 1:
                return None  # both zenity and kdialog use 1 for "cancelled"
            raise FileDialogError(
                f"{cmd[0]} failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        raise FileDialogError(
            "no dialog helper found: install 'zenity' (GNOME) or 'kdialog' (KDE)"
        )


def _powershell_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


class WindowsFileDialogBackend(FileDialogBackend):
    """Windows dialogs via PowerShell + System.Windows.Forms."""

    def open_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        lines = self._open_dialog_lines(title, initial_dir, file_types)
        lines.append("if ($d.ShowDialog() -eq 'OK') { Write-Output $d.FileName }")
        return self._run(lines)

    def open_files(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> list[Path]:
        lines = self._open_dialog_lines(title, initial_dir, file_types)
        lines.append("$d.Multiselect = $true")
        lines.append("if ($d.ShowDialog() -eq 'OK') { $d.FileNames | Write-Output }")
        out = self._run_script(lines)
        return [Path(line) for line in out.splitlines() if line.strip()]

    @staticmethod
    def _open_dialog_lines(
        title: Optional[str],
        initial_dir: Optional[Path],
        file_types: Optional[Sequence[str]],
    ) -> list[str]:
        lines = ["$d = New-Object System.Windows.Forms.OpenFileDialog"]
        if title:
            lines.append(f"$d.Title = {_powershell_quote(title)}")
        if initial_dir:
            lines.append(f"$d.InitialDirectory = {_powershell_quote(str(initial_dir))}")
        if file_types:
            patterns = ";".join(f"*.{ext}" for ext in file_types)
            filter_spec = f"Files ({patterns})|{patterns}|All files (*.*)|*.*"
            lines.append(f"$d.Filter = {_powershell_quote(filter_spec)}")
        return lines

    def save_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        default_name: Optional[str] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        lines = ["$d = New-Object System.Windows.Forms.SaveFileDialog"]
        if title:
            lines.append(f"$d.Title = {_powershell_quote(title)}")
        if initial_dir:
            lines.append(f"$d.InitialDirectory = {_powershell_quote(str(initial_dir))}")
        if default_name:
            lines.append(f"$d.FileName = {_powershell_quote(default_name)}")
        if file_types:
            patterns = ";".join(f"*.{ext}" for ext in file_types)
            filter_spec = f"Files ({patterns})|{patterns}|All files (*.*)|*.*"
            lines.append(f"$d.Filter = {_powershell_quote(filter_spec)}")
        lines.append("if ($d.ShowDialog() -eq 'OK') { Write-Output $d.FileName }")
        return self._run(lines)

    def open_directory(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        lines = ["$d = New-Object System.Windows.Forms.FolderBrowserDialog"]
        if title:
            lines.append(f"$d.Description = {_powershell_quote(title)}")
        if initial_dir:
            lines.append(f"$d.SelectedPath = {_powershell_quote(str(initial_dir))}")
        lines.append("if ($d.ShowDialog() -eq 'OK') { Write-Output $d.SelectedPath }")
        return self._run(lines)

    def _run(self, script_lines: list[str]) -> Optional[Path]:
        selected = self._run_script(script_lines).strip()
        return Path(selected) if selected else None

    def _run_script(self, script_lines: list[str]) -> str:
        """Run a WinForms dialog script; empty output means cancelled."""
        script = "Add-Type -AssemblyName System.Windows.Forms; " + "; ".join(script_lines)
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", script],
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise FileDialogError(f"PowerShell could not be launched: {exc}") from exc
        if result.returncode != 0:
            raise FileDialogError(f"PowerShell dialog failed: {result.stderr.strip()}")
        return result.stdout


class DummyFileDialogBackend(FileDialogBackend):
    """Fallback for unsupported platforms: every request is 'cancelled'."""

    def open_file(self, **kwargs: object) -> Optional[Path]:
        return None

    def open_files(self, **kwargs: object) -> list[Path]:
        return []

    def save_file(self, **kwargs: object) -> Optional[Path]:
        return None

    def open_directory(self, **kwargs: object) -> Optional[Path]:
        return None


_backend: Optional[FileDialogBackend] = None


def _create_backend() -> FileDialogBackend:
    if sys.platform == "darwin":
        # Prefer the in-process Cocoa panels: near-instant once warm, correct
        # focus, app-modal. Fall back to the osascript helper when the bridge
        # is unavailable.
        try:
            from .file_dialog_cocoa import CocoaFileDialogBackend

            return CocoaFileDialogBackend()
        except Exception:
            exception_once(
                logger,
                "file_dialog_cocoa_unavailable",
                "in-process Cocoa file dialogs unavailable; falling back to osascript",
            )
            return MacFileDialogBackend()
    if sys.platform == "linux":
        return LinuxFileDialogBackend()
    if sys.platform == "win32":
        # Prefer the in-process common-item dialog (no PowerShell spawn per
        # call); fall back to PowerShell when COM cannot be initialized.
        try:
            from .file_dialog_win32 import Win32FileDialogBackend

            return Win32FileDialogBackend()
        except Exception:
            exception_once(
                logger,
                "file_dialog_win32_unavailable",
                "in-process IFileDialog unavailable; falling back to PowerShell",
            )
            return WindowsFileDialogBackend()
    return DummyFileDialogBackend()


def get_system_file_dialog_backend() -> FileDialogBackend:
    """Return the dialog backend for the current platform (one per process).

    The instance is cached: in-process backends keep their native panels —
    and the panels' remote-view sessions — alive between calls, which is what
    makes dialogs after the first appear instantly.
    """
    global _backend
    if _backend is None:
        _backend = _create_backend()
    return _backend


def _normalize_dir(initial_dir: Union[Path, str, None]) -> Optional[Path]:
    if initial_dir is None:
        return None
    return Path(initial_dir).expanduser()


# One dialog at a time: without this, a double-click (easy while a slow
# backend's dialog is still appearing) stacks two identical dialogs exactly on
# top of each other, and closing one leaves a confusing twin behind.
_dialog_lock = asyncio.Lock()


async def _run_backend(call: Callable[[FileDialogBackend], _T]) -> _T:
    async with _dialog_lock:
        backend = get_system_file_dialog_backend()
        if backend.runs_on_ui_thread:
            return call(backend)
        return await asyncio.to_thread(lambda: call(backend))


class FileDialog:
    """Native open-file / save-file / open-directory dialogs.

    All methods are coroutines: the dialog runs in an OS helper process and is
    awaited from a worker thread, so the UI keeps painting while it is open.
    Call them from an async event handler::

        class Editor(nv.ComposableWidget):
            async def _open(self) -> None:
                path = await nv.FileDialog.open_file(file_types=["txt", "md"])
                if path is None:
                    return  # cancelled
                self.text.value = path.read_text()

    Each method returns the selected :class:`~pathlib.Path`, or ``None`` when
    the user cancelled. :class:`FileDialogError` is raised when the dialog
    cannot be shown at all (e.g. no ``zenity``/``kdialog`` on Linux).
    """

    @staticmethod
    async def open_file(
        *,
        title: Optional[str] = None,
        initial_dir: Union[Path, str, None] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        """Pick an existing file to open.

        ``file_types`` restricts the picker to extensions given without the
        leading dot (e.g. ``["png", "jpg"]``); ``None`` allows any file.
        A leading ``~`` in ``initial_dir`` is expanded to the home directory.
        """
        return await _run_backend(
            lambda backend: backend.open_file(
                title=title,
                initial_dir=_normalize_dir(initial_dir),
                file_types=file_types,
            )
        )

    @staticmethod
    async def open_files(
        *,
        title: Optional[str] = None,
        initial_dir: Union[Path, str, None] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> list[Path]:
        """Pick one or more existing files to open.

        Like :meth:`open_file` with multiple selection. Cancelling returns an
        empty list — the dialog cannot return zero selections otherwise.
        """
        return await _run_backend(
            lambda backend: backend.open_files(
                title=title,
                initial_dir=_normalize_dir(initial_dir),
                file_types=file_types,
            )
        )

    @staticmethod
    async def save_file(
        *,
        title: Optional[str] = None,
        initial_dir: Union[Path, str, None] = None,
        default_name: Optional[str] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        """Pick a destination path to save to.

        The returned path may not exist yet; writing the file is the caller's
        job. The native dialog asks for overwrite confirmation where the
        platform does so. ``file_types`` restricts the saved name's extension
        where the platform's save dialog supports it; the macOS ``osascript``
        fallback has no type filter and ignores it.
        """
        return await _run_backend(
            lambda backend: backend.save_file(
                title=title,
                initial_dir=_normalize_dir(initial_dir),
                default_name=default_name,
                file_types=file_types,
            )
        )

    @staticmethod
    async def open_directory(
        *,
        title: Optional[str] = None,
        initial_dir: Union[Path, str, None] = None,
    ) -> Optional[Path]:
        """Pick an existing directory."""
        return await _run_backend(
            lambda backend: backend.open_directory(
                title=title,
                initial_dir=_normalize_dir(initial_dir),
            )
        )
