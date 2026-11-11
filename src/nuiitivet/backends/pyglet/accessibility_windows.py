"""Windows: install an AccessKit adapter on a pyglet window."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Callable

if sys.platform != "win32":  # pragma: no cover - guards Win32-only use
    raise ImportError("accessibility_windows is only available on Windows")

import accesskit

if TYPE_CHECKING:
    from .accessibility import AccessKitBridge


class _Adapter:
    """The subclassing adapter, with the view-focus call the bridge makes.

    The subclass sees ``WM_SETFOCUS`` and ``WM_KILLFOCUS`` itself, so the
    bridge's report of the window's activation has nothing to add.
    """

    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter

    def update_if_active(self, update_factory: Callable[[], Any]) -> Any:
        return self._adapter.update_if_active(update_factory)

    def update_view_focus_state(self, is_focused: bool) -> Any:
        return None


def install(window: Any, bridge: "AccessKitBridge") -> None:
    """Subclass ``window``'s HWND with AccessKit and attach it to ``bridge``.

    The window must not have been shown yet: the adapter refuses a visible
    window.

    Args:
        window: The pyglet Win32 window (has ``_hwnd``).
        bridge: The bridge whose callbacks the adapter calls.
    """
    adapter = accesskit.windows.SubclassingAdapter(window._hwnd, bridge.activation_handler, bridge.action_handler)
    bridge.attach(_Adapter(adapter))


__all__ = ["install"]
