"""Linux: install an AccessKit adapter beside a pyglet window, on AT-SPI."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Callable

if sys.platform != "linux":  # pragma: no cover - guards Linux-only use
    raise ImportError("accessibility_linux is only available on Linux")

import accesskit

if TYPE_CHECKING:
    from .accessibility import AccessKitBridge


class _Adapter:
    """The Unix adapter, with the view-focus call the bridge makes.

    The Unix adapter raises its events itself: its calls return nothing.
    """

    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter

    def update_if_active(self, update_factory: Callable[[], Any]) -> Any:
        return self._adapter.update_if_active(update_factory)

    def update_view_focus_state(self, is_focused: bool) -> Any:
        return self._adapter.update_window_focus_state(is_focused)

    def set_window_bounds(self, x: int, y: int, width: int, height: int) -> None:
        """Hand the adapter the window's client area, in screen pixels."""
        rect = accesskit.Rect(float(x), float(y), float(x + width), float(y + height))
        self._adapter.set_root_window_bounds(rect, rect)


def _deactivation_handler() -> None:
    """The adapter's notice that no assistive technology listens any more."""


def install(window: Any, bridge: "AccessKitBridge") -> None:
    """Create the AT-SPI adapter with ``bridge``'s callbacks and attach it.

    The adapter has no window of its own: the window's client area is handed
    to it when the window shows, resizes or moves.

    Args:
        window: The pyglet Xlib window.
        bridge: The bridge whose callbacks the adapter calls, from another
            thread.
    """
    adapter = _Adapter(accesskit.unix.Adapter(bridge.activation_handler, bridge.action_handler, _deactivation_handler))

    def bounds(*args: Any) -> None:
        x, y = window.get_location()
        width, height = window.get_framebuffer_size()
        adapter.set_window_bounds(x, y, width, height)

    window.push_handlers(on_show=bounds, on_resize=bounds, on_move=bounds)
    bridge.attach(adapter)


__all__ = ["install"]
