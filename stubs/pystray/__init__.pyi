# Minimal pystray stub for mypy: only the surface nuiitivet's tray bridge uses.
# pystray ships no py.typed, and is installed only on Windows/Linux (platform
# marker), so without this stub mypy's verdict would differ per platform.

from typing import Any, Callable, Optional

class Icon:
    HAS_MENU: bool
    HAS_DEFAULT: bool
    title: str
    def __init__(
        self,
        name: str,
        icon: Any = ...,
        title: str = ...,
        menu: Optional[Menu] = ...,
    ) -> None: ...
    def run_detached(self, setup: Optional[Callable[[Icon], None]] = ...) -> None: ...
    def update_menu(self) -> None: ...
    def stop(self) -> None: ...

class Menu:
    SEPARATOR: Any
    def __init__(self, *items: Any) -> None: ...

class MenuItem:
    def __init__(
        self,
        text: Any,
        action: Any = ...,
        checked: Optional[Callable[[Any], bool]] = ...,
        enabled: Any = ...,
        default: bool = ...,
        visible: Any = ...,
    ) -> None: ...
