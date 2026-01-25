"""Platform-specific integrations.

This package provides OS-level services that do not depend on the rendering or
windowing backend.
"""

from .clipboard import Clipboard, get_system_clipboard
from .ime import IMEManager, IMECursorInfo

__all__ = [
    "Clipboard",
    "get_system_clipboard",
    "IMEManager",
    "IMECursorInfo",
]
