"""macOS: deliver the first click on an inactive window.

pyglet's Cocoa view does not override ``acceptsFirstMouse:``, so it stays at
AppKit's default ``NO``: the click that activates an inactive window is
consumed by the system and no ``mouseDown`` reaches the view. This module
adds ``acceptsFirstMouse:`` to the pyglet view classes via the same
``cocoapy`` approach as the IME patch, answering per window from
``Window(accepts_first_mouse=...)``.

No-op on non-macOS platforms; Windows and Linux already deliver the
activating click.
"""

import sys
from typing import Any

if sys.platform != "darwin":

    def install_patch(window: Any, accepts: bool) -> None:
        pass

else:
    import ctypes
    import logging

    from pyglet.libs.darwin import cocoapy
    from pyglet.libs.darwin.cocoapy import ObjCClass

    from nuiitivet.common.logging_once import exception_once

    _logger = logging.getLogger(__name__)

    libobjc = cocoapy.objc

    # Per-view answer, keyed by view pointer. Unregistered views accept,
    # matching the Window default.
    _ptr_accepts: dict[int, bool] = {}

    # BOOL (*IMP)(id, SEL, NSEvent *)
    IMP_TYPE = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

    def acceptsFirstMouse_impl(self: int, cmd: Any, nsevent: Any) -> bool:
        return _ptr_accepts.get(self, True)

    _imp = IMP_TYPE(acceptsFirstMouse_impl)
    _imp_ptr = ctypes.cast(_imp, ctypes.c_void_p)
    _sel = libobjc.sel_registerName(b"acceptsFirstMouse:")
    # BOOL return encoded 'B', matching pyglet's own method encodings.
    _types = b"B@:@"

    _patch_installed = False

    def install_patch(window: Any, accepts: bool) -> None:
        """Patch the pyglet view classes and register this window's answer.

        Args:
            window: The pyglet Cocoa window (has ``_nswindow``).
            accepts: The window's ``accepts_first_mouse`` value.
        """
        global _patch_installed

        try:
            # The hit-tested view under a click is the PygletView content
            # view; PygletTextView is its (zero-frame) subview, patched too
            # so a hit on it answers the same.
            view_classes = [ObjCClass("PygletView"), ObjCClass("PygletTextView")]

            if not _patch_installed:
                libobjc.class_addMethod.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                    ctypes.c_char_p,
                ]
                libobjc.class_addMethod.restype = ctypes.c_bool
                for cls in view_classes:
                    libobjc.class_addMethod(cls, _sel, _imp_ptr, _types)
                _patch_installed = True

            content_view = window._nswindow.contentView()
            ptrs = [content_view.ptr.value if hasattr(content_view, "ptr") else content_view.value]
            subviews = content_view.subviews()
            for i in range(subviews.count()):
                view = subviews.objectAtIndex_(i)
                ptrs.append(view.ptr.value if hasattr(view, "ptr") else view.value)
            for ptr in ptrs:
                _ptr_accepts[ptr] = bool(accepts)
        except Exception:
            exception_once(
                _logger,
                "first_mouse_macos_install_exc",
                "Failed to install acceptsFirstMouse patch",
            )
