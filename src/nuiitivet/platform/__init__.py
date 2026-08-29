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
from .desktop import Desktop
from .notification import (
    NotificationBackend,
    NotificationError,
    get_system_notification_backend,
)

__all__ = [
    "Clipboard",
    "get_system_clipboard",
    "Desktop",
    "FileDialog",
    "FileDialogBackend",
    "FileDialogError",
    "get_system_file_dialog_backend",
    "IMEManager",
    "IMECursorInfo",
    "NotificationBackend",
    "NotificationError",
    "get_system_notification_backend",
]
