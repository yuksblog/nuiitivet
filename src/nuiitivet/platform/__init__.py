"""Platform-specific integrations.

This package provides OS-level services that do not depend on the rendering or
windowing backend.
"""

from .clipboard import Clipboard, get_system_clipboard
from .file_dialog import (
    FileDialog,
    FileDialogBackend,
    FileDialogError,
    get_system_file_dialog_backend,
)
from .ime import IMEManager, IMECursorInfo

__all__ = [
    "Clipboard",
    "get_system_clipboard",
    "FileDialog",
    "FileDialogBackend",
    "FileDialogError",
    "get_system_file_dialog_backend",
    "IMEManager",
    "IMECursorInfo",
]
