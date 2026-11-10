"""macOS: install an AccessKit adapter on a pyglet window."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

if sys.platform != "darwin":  # pragma: no cover - guards Darwin-only ObjC use
    raise ImportError("accessibility_macos is only available on macOS")

from ctypes import c_void_p

import accesskit

from pyglet.libs.darwin.cocoapy import ObjCInstance, cfstring_to_string, send_message

if TYPE_CHECKING:
    from .accessibility import AccessKitBridge

# The NSWindow classes already given the focus forwarder.
_FORWARDED: set[str] = set()


def install(window: Any, bridge: "AccessKitBridge") -> None:
    """Subclass ``window``'s content view with AccessKit and attach it to ``bridge``.

    pyglet's first responder is a text view beneath the content view, which
    is not in the tree. The NSWindow is made to ask the content view for the
    focused element, and the text view is hidden from assistive technology.

    Args:
        window: The pyglet Cocoa window (has ``_nswindow``).
        bridge: The bridge whose callbacks the adapter calls.
    """
    nswindow = window._nswindow
    name_ptr = send_message(nswindow, "className", restype=c_void_p, argtypes=[])
    address = name_ptr.value if isinstance(name_ptr, c_void_p) else name_ptr
    class_name = cfstring_to_string(ObjCInstance(int(address or 0)))
    if class_name not in _FORWARDED:
        accesskit.macos.add_focus_forwarder_to_window_class(class_name)
        _FORWARDED.add(class_name)

    subviews = nswindow.contentView().subviews()
    for index in range(subviews.count()):
        subviews.objectAtIndex_(index).setAccessibilityElement_(False)

    adapter = accesskit.macos.SubclassingAdapter.for_window(
        nswindow.ptr.value, bridge.activation_handler, bridge.action_handler
    )
    bridge.attach(adapter)
