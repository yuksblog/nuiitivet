"""File dialogs in a browser: the page's file picker, and a download in place of a save dialog."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Optional, Sequence

from nuiitivet.platform.file_dialog import FileDialogBackend, FileDialogError

try:
    from pyodide.ffi import to_js
except ImportError:  # the unit tests run on the desktop, with a fake host

    def to_js(value: Any) -> Any:
        return value


def _accept(file_types: Optional[Sequence[str]]) -> str:
    """The picker's ``accept`` attribute for the extensions."""
    return ",".join(f".{ext.lstrip('.')}" for ext in file_types) if file_types else ""


class BrowserFileDialogBackend(FileDialogBackend):
    """The browser's file picker, and a download in place of a save dialog.

    A picked file is copied into the page's memory, under a fresh directory
    and with its own name, and that path is returned. ``title`` and
    ``initial_dir`` have no effect: the picker is the browser's own.
    """

    runs_on_ui_thread = True

    def __init__(self, host: Any = None) -> None:
        """Initialize BrowserFileDialogBackend.

        Args:
            host: The page's ``NV_HOST``; the one in ``js`` when omitted.
        """
        if host is None:
            import js

            host = js.NV_HOST
        self._host = host

    async def open_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        _root, paths = await self._pick(file_types, multiple=False, directory=False)
        return paths[0] if paths else None

    async def open_files(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> list[Path]:
        _root, paths = await self._pick(file_types, multiple=True, directory=False)
        return paths

    async def save_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        default_name: Optional[str] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        """A path in the page's memory, at once; the file written there is downloaded when the calling task ends.

        The user picks nothing, so the result is never ``None``.
        """
        name = default_name or "untitled"
        if file_types and not Path(name).suffix:
            name = f"{name}.{file_types[0].lstrip('.')}"
        path = Path(tempfile.mkdtemp(prefix="nuiitivet-save-")) / name
        task = asyncio.current_task()
        if task is None:
            raise FileDialogError("save_file was called outside a task, so there is no end of it to download at")
        task.add_done_callback(lambda _task: self._download(path))
        return path

    async def open_directory(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        root, paths = await self._pick(None, multiple=True, directory=True)
        if not paths:
            return None
        return root / paths[0].relative_to(root).parts[0]

    async def _pick(
        self, file_types: Optional[Sequence[str]], *, multiple: bool, directory: bool
    ) -> tuple[Path, list[Path]]:
        """Show the picker and copy what was picked under a fresh directory; ``[]`` when cancelled."""
        if not self._host.canShowPicker():
            raise FileDialogError("a browser shows a file picker only from a click or a key press")
        files = await self._host.pickFiles(_accept(file_types), multiple, directory)
        root = Path(tempfile.mkdtemp(prefix="nuiitivet-open-"))
        paths: list[Path] = []
        for file in files:
            # A directory's files carry their path under it; a plain pick carries the name alone.
            target = root / (file.webkitRelativePath or file.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((await file.arrayBuffer()).to_bytes())
            paths.append(target)
        return root, paths

    def _download(self, path: Path) -> None:
        if path.is_file():
            self._host.download(path.name, to_js(path.read_bytes()))


__all__ = ["BrowserFileDialogBackend"]
