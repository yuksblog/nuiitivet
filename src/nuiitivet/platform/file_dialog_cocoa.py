"""In-process Cocoa file dialogs (macOS).

Opens ``NSOpenPanel`` / ``NSSavePanel`` inside the running process via pyglet's
bundled ObjC bridge, instead of spawning an ``osascript`` helper per call. The
panel's content is served by a per-process remote view service whose session
setup costs ~1s; creating each panel once and reusing it keeps that session
warm, so the first dialog pays that cost once and later ones appear
near-instantly. (Startup-time prewarming was tried and rejected: it froze
every app's launch for a feature many never use.)

AppKit is main-thread-only, so this backend runs on the UI thread
(``runs_on_ui_thread = True``); ``runModal`` blocks the event loop while the
dialog is up, which gives app-modal behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence

from pyglet.libs.darwin import cocoapy

from .file_dialog import FileDialogBackend

_OK = 1  # NSModalResponseOK


class CocoaFileDialogBackend(FileDialogBackend):
    """macOS dialogs via in-process ``NSOpenPanel`` / ``NSSavePanel``."""

    runs_on_ui_thread = True

    def __init__(self) -> None:
        # Resolve the classes eagerly so construction fails (and the caller
        # falls back to the osascript backend) when AppKit is unavailable.
        self._NSOpenPanel = cocoapy.ObjCClass("NSOpenPanel")
        self._NSSavePanel = cocoapy.ObjCClass("NSSavePanel")
        self._NSURL = cocoapy.ObjCClass("NSURL")
        self._NSMutableArray = cocoapy.ObjCClass("NSMutableArray")
        self._open_panel: Any = None
        self._save_panel: Any = None

    # --- panel cache ------------------------------------------------------

    def _get_open_panel(self) -> Any:
        if self._open_panel is None:
            panel = self._NSOpenPanel.openPanel()
            panel.retain()
            self._open_panel = panel
        return self._open_panel

    def _get_save_panel(self) -> Any:
        if self._save_panel is None:
            panel = self._NSSavePanel.savePanel()
            panel.retain()
            self._save_panel = panel
        return self._save_panel

    # --- configuration helpers -------------------------------------------

    def _set_common(
        self,
        panel: Any,
        title: Optional[str],
        initial_dir: Optional[Path],
    ) -> None:
        panel.setMessage_(cocoapy.get_NSString(title or ""))
        if initial_dir is not None:
            url = self._NSURL.fileURLWithPath_(cocoapy.get_NSString(str(initial_dir)))
            panel.setDirectoryURL_(url)

    def _set_file_types(self, panel: Any, file_types: Optional[Sequence[str]]) -> None:
        # setAllowedFileTypes: is deprecated; guard so a future macOS that
        # drops the selector degrades to "no filter" instead of aborting.
        if not panel.respondsToSelector_(cocoapy.get_selector("setAllowedFileTypes:")):
            return
        if not file_types:
            panel.setAllowedFileTypes_(None)
            return
        types = self._NSMutableArray.array()
        for ext in file_types:
            types.addObject_(cocoapy.get_NSString(ext))
        panel.setAllowedFileTypes_(types)

    @staticmethod
    def _panel_paths(panel: Any) -> list[Path]:
        urls = panel.URLs()
        return [
            Path(cocoapy.cfstring_to_string(urls.objectAtIndex_(i).path()))
            for i in range(urls.count())
        ]

    def _run_open(
        self,
        *,
        title: Optional[str],
        initial_dir: Optional[Path],
        file_types: Optional[Sequence[str]],
        multiple: bool,
        directories: bool,
    ) -> list[Path]:
        panel = self._get_open_panel()
        self._set_common(panel, title, initial_dir)
        panel.setCanChooseFiles_(not directories)
        panel.setCanChooseDirectories_(directories)
        panel.setAllowsMultipleSelection_(multiple)
        self._set_file_types(panel, None if directories else file_types)
        if panel.runModal() != _OK:
            return []
        return self._panel_paths(panel)

    # --- FileDialogBackend ------------------------------------------------

    def open_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        selected = self._run_open(
            title=title,
            initial_dir=initial_dir,
            file_types=file_types,
            multiple=False,
            directories=False,
        )
        return selected[0] if selected else None

    def open_files(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> list[Path]:
        return self._run_open(
            title=title,
            initial_dir=initial_dir,
            file_types=file_types,
            multiple=True,
            directories=False,
        )

    def save_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        default_name: Optional[str] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        panel = self._get_save_panel()
        self._set_common(panel, title, initial_dir)
        panel.setNameFieldStringValue_(cocoapy.get_NSString(default_name or ""))
        self._set_file_types(panel, file_types)
        if panel.runModal() != _OK:
            return None
        return Path(cocoapy.cfstring_to_string(panel.URL().path()))

    def open_directory(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        selected = self._run_open(
            title=title,
            initial_dir=initial_dir,
            file_types=None,
            multiple=False,
            directories=True,
        )
        return selected[0] if selected else None
