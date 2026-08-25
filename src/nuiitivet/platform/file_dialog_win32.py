"""In-process Windows file dialogs via ``ctypes`` + ``IFileDialog`` COM.

Replaces the PowerShell-spawning backend on Windows: the common-item dialog
(`IFileOpenDialog` / `IFileSaveDialog`) opens inside the running process, so
there is no interpreter spawn or WinForms assembly load per call.

The dialog must run on an STA thread with a message pump, so this backend runs
on the UI thread (``runs_on_ui_thread = True``); the modal dialog pumps the
thread's message queue itself, so the app window keeps painting while it is
up. Construction performs COM initialization and a real ``CoCreateInstance``,
so environments where that cannot work fail fast and the caller falls back to
the PowerShell backend.
"""

from __future__ import annotations

import sys

if sys.platform != "win32":  # pragma: no cover - guards Windows-only ctypes use
    raise ImportError("file_dialog_win32 is only available on Windows")

import ctypes
from ctypes import POINTER, byref, c_uint, c_void_p, c_wchar_p
from pathlib import Path
from typing import Any, Optional, Sequence

from .file_dialog import FileDialogBackend, FileDialogError

_ole32 = ctypes.oledll.ole32
_shell32 = ctypes.oledll.shell32

# HRESULT of ERROR_CANCELLED as the OSError.winerror ctypes raises for it.
_HRESULT_CANCELLED = -2147023673  # 0x800704C7

_COINIT_APARTMENTTHREADED = 0x2
_CLSCTX_INPROC_SERVER = 0x1

_SIGDN_FILESYSPATH = 0x80058000

_FOS_FORCEFILESYSTEM = 0x40
_FOS_ALLOWMULTISELECT = 0x200
_FOS_PICKFOLDERS = 0x20


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __init__(self, text: str) -> None:
        super().__init__()
        _ole32.CLSIDFromString(c_wchar_p(text), byref(self))


_CLSID_FileOpenDialog = "{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}"
_CLSID_FileSaveDialog = "{C0B4E2F3-BA21-4773-8DBA-335EC946EB8B}"
_IID_IFileOpenDialog = "{D57C7288-D4AD-4768-BE02-9D969532D960}"
_IID_IFileSaveDialog = "{84BCCD23-5FDE-4CDB-AEA4-AF64B83D78AB}"
_IID_IShellItem = "{43826D1E-E718-42EE-BC55-A1E261C37BFE}"


class _COMDLG_FILTERSPEC(ctypes.Structure):
    _fields_ = [("pszName", c_wchar_p), ("pszSpec", c_wchar_p)]


def _com_call(obj: c_void_p, index: int, *args: Any, argtypes: Sequence[Any]) -> int:
    """Call the vtable slot ``index`` on COM object ``obj``.

    The prototype's ``HRESULT`` restype makes ctypes raise ``OSError`` for
    failed calls, with the HRESULT in ``winerror``.
    """
    vtable = ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents
    proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *argtypes)
    return proto(vtable[index])(obj, *args)


def _release(obj: c_void_p) -> None:
    if obj:
        vtable = ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents
        proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)
        proto(vtable[2])(obj)  # IUnknown::Release


# --- IFileDialog vtable slots (IUnknown 0-2, IModalWindow 3) ---------------
_SHOW = 3
_SET_FILE_TYPES = 4
_SET_OPTIONS = 9
_GET_OPTIONS = 10
_SET_FOLDER = 12
_SET_FILE_NAME = 15
_SET_TITLE = 17
_GET_RESULT = 20
_SET_DEFAULT_EXTENSION = 22
_GET_RESULTS = 27  # IFileOpenDialog only

# --- IShellItem / IShellItemArray vtable slots -----------------------------
_GET_DISPLAY_NAME = 5  # IShellItem
_ARRAY_GET_COUNT = 7  # IShellItemArray
_ARRAY_GET_ITEM_AT = 8  # IShellItemArray


def _shell_item_path(item: c_void_p) -> Path:
    buffer = c_wchar_p()
    _com_call(
        item,
        _GET_DISPLAY_NAME,
        _SIGDN_FILESYSPATH,
        byref(buffer),
        argtypes=[c_uint, POINTER(c_wchar_p)],
    )
    try:
        return Path(buffer.value or "")
    finally:
        _ole32.CoTaskMemFree(buffer)


def _shell_item_from_path(path: Path) -> c_void_p:
    item = c_void_p()
    _shell32.SHCreateItemFromParsingName(
        c_wchar_p(str(path)), None, byref(_GUID(_IID_IShellItem)), byref(item)
    )
    return item


class Win32FileDialogBackend(FileDialogBackend):
    """Windows dialogs via the in-process common-item dialog (COM)."""

    runs_on_ui_thread = True

    def __init__(self) -> None:
        # S_OK / S_FALSE both mean COM is usable; RPC_E_CHANGED_MODE (the
        # thread is already MTA) raises, and the caller falls back.
        _ole32.CoInitializeEx(None, _COINIT_APARTMENTTHREADED)
        # Fail fast if dialog objects cannot be created at all.
        dialog = self._create(_CLSID_FileOpenDialog, _IID_IFileOpenDialog)
        _release(dialog)

    @staticmethod
    def _create(clsid: str, iid: str) -> c_void_p:
        dialog = c_void_p()
        _ole32.CoCreateInstance(
            byref(_GUID(clsid)),
            None,
            _CLSCTX_INPROC_SERVER,
            byref(_GUID(iid)),
            byref(dialog),
        )
        return dialog

    # --- configuration helpers -------------------------------------------

    @staticmethod
    def _configure(
        dialog: c_void_p,
        *,
        title: Optional[str],
        initial_dir: Optional[Path],
        file_types: Optional[Sequence[str]],
        extra_options: int,
    ) -> list[object]:
        """Apply common settings; returns objects that must stay alive."""
        keepalive: list[object] = []
        options = c_uint()
        _com_call(dialog, _GET_OPTIONS, byref(options), argtypes=[POINTER(c_uint)])
        _com_call(
            dialog,
            _SET_OPTIONS,
            options.value | _FOS_FORCEFILESYSTEM | extra_options,
            argtypes=[c_uint],
        )
        if title:
            _com_call(dialog, _SET_TITLE, c_wchar_p(title), argtypes=[c_wchar_p])
        if initial_dir is not None:
            folder = _shell_item_from_path(initial_dir)
            try:
                _com_call(dialog, _SET_FOLDER, folder, argtypes=[c_void_p])
            finally:
                _release(folder)
        if file_types:
            patterns = ";".join(f"*.{ext}" for ext in file_types)
            specs = (_COMDLG_FILTERSPEC * 2)(
                (f"Files ({patterns})", patterns),
                ("All files (*.*)", "*.*"),
            )
            keepalive.append(specs)
            _com_call(
                dialog,
                _SET_FILE_TYPES,
                2,
                specs,
                argtypes=[c_uint, POINTER(_COMDLG_FILTERSPEC)],
            )
        return keepalive

    @staticmethod
    def _show(dialog: c_void_p) -> bool:
        """Run the modal dialog; ``False`` means the user cancelled."""
        try:
            _com_call(dialog, _SHOW, None, argtypes=[c_void_p])
        except OSError as exc:
            if exc.winerror == _HRESULT_CANCELLED:
                return False
            raise FileDialogError(f"IFileDialog.Show failed: {exc}") from exc
        return True

    def _run_open(
        self,
        *,
        title: Optional[str],
        initial_dir: Optional[Path],
        file_types: Optional[Sequence[str]],
        extra_options: int,
        multiple: bool,
    ) -> list[Path]:
        dialog = self._create(_CLSID_FileOpenDialog, _IID_IFileOpenDialog)
        try:
            keepalive = self._configure(
                dialog,
                title=title,
                initial_dir=initial_dir,
                file_types=file_types,
                extra_options=extra_options,
            )
            if not self._show(dialog):
                return []
            del keepalive
            if not multiple:
                item = c_void_p()
                _com_call(dialog, _GET_RESULT, byref(item), argtypes=[POINTER(c_void_p)])
                try:
                    return [_shell_item_path(item)]
                finally:
                    _release(item)
            items = c_void_p()
            _com_call(dialog, _GET_RESULTS, byref(items), argtypes=[POINTER(c_void_p)])
            try:
                count = c_uint()
                _com_call(items, _ARRAY_GET_COUNT, byref(count), argtypes=[POINTER(c_uint)])
                selected: list[Path] = []
                for i in range(count.value):
                    item = c_void_p()
                    _com_call(
                        items,
                        _ARRAY_GET_ITEM_AT,
                        i,
                        byref(item),
                        argtypes=[c_uint, POINTER(c_void_p)],
                    )
                    try:
                        selected.append(_shell_item_path(item))
                    finally:
                        _release(item)
                return selected
            finally:
                _release(items)
        finally:
            _release(dialog)

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
            extra_options=0,
            multiple=False,
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
            extra_options=_FOS_ALLOWMULTISELECT,
            multiple=True,
        )

    def save_file(
        self,
        *,
        title: Optional[str] = None,
        initial_dir: Optional[Path] = None,
        default_name: Optional[str] = None,
        file_types: Optional[Sequence[str]] = None,
    ) -> Optional[Path]:
        dialog = self._create(_CLSID_FileSaveDialog, _IID_IFileSaveDialog)
        try:
            keepalive = self._configure(
                dialog,
                title=title,
                initial_dir=initial_dir,
                file_types=file_types,
                extra_options=0,
            )
            if default_name:
                _com_call(
                    dialog, _SET_FILE_NAME, c_wchar_p(default_name), argtypes=[c_wchar_p]
                )
            if file_types:
                _com_call(
                    dialog,
                    _SET_DEFAULT_EXTENSION,
                    c_wchar_p(file_types[0]),
                    argtypes=[c_wchar_p],
                )
            if not self._show(dialog):
                return None
            del keepalive
            item = c_void_p()
            _com_call(dialog, _GET_RESULT, byref(item), argtypes=[POINTER(c_void_p)])
            try:
                return _shell_item_path(item)
            finally:
                _release(item)
        finally:
            _release(dialog)

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
            extra_options=_FOS_PICKFOLDERS,
            multiple=False,
        )
        return selected[0] if selected else None
