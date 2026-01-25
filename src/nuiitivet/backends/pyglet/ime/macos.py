import ctypes
import logging
import sys
from typing import Any

from nuiitivet.common.logging_once import exception_once


_logger = logging.getLogger(__name__)

# Only run on macOS
if sys.platform != "darwin":

    def install_patch(window: Any) -> None:
        pass

else:
    from pyglet.libs.darwin import cocoapy
    from pyglet.libs.darwin.cocoapy import ObjCClass, ObjCInstance, get_selector

    libobjc = cocoapy.objc

    # Define NSRange structure
    class NSRange(ctypes.Structure):
        _fields_ = [("location", ctypes.c_ulonglong), ("length", ctypes.c_ulonglong)]

    class NSPoint(ctypes.Structure):
        _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

    class NSSize(ctypes.Structure):
        _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]

    class NSRect(ctypes.Structure):
        _fields_ = [("origin", NSPoint), ("size", NSSize)]

    # Global map to store window references keyed by PygletTextView pointer
    _ptr_to_window: dict[int, Any] = {}

    # Callback function for setMarkedText:selectedRange:replacementRange:
    # void (*IMP)(id, SEL, id, NSRange, NSRange)
    IMP_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, NSRange, NSRange)

    # Callback for firstRectForCharacterRange:actualRange:
    # On x86_64/arm64, large struct return (NSRect) is handled via a hidden first argument (pointer to result).
    # void (*)(NSRect *, id, SEL, NSRange, NSRangePointer)
    IMP_TYPE_RECT = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, NSRange, ctypes.c_void_p)

    def setMarkedText_impl(self, cmd, text, selectedRange, replacementRange):
        # self is the pointer to the PygletTextView instance
        window = _ptr_to_window.get(self)
        if not window:
            return

        # Convert text (id) to string
        text_obj = ObjCInstance(text)
        if text_obj.isKindOfClass_(ObjCClass("NSAttributedString")):
            text_obj = text_obj.string()

        text_str = cocoapy.cfstring_to_string(text_obj)

        try:
            window.dispatch_event("on_ime_composition", text_str, selectedRange.location, selectedRange.length)
        except Exception:
            exception_once(_logger, "ime_macos_dispatch_on_ime_composition_exc", "IME composition dispatch raised")

    def firstRectForCharacterRange_impl(result_ptr, self, cmd, range, actualRange):
        from nuiitivet.platform import IMEManager

        ime = IMEManager.get()

        # Default rect (0,0,0,0)
        rect = NSRect(NSPoint(0, 0), NSSize(0, 0))

        # Get window info
        wx, wy = ime.window_location
        # ww, wh = ime.window_size

        # Get cursor info
        cx = ime.cursor_rect.x
        cy = ime.cursor_rect.y
        cw = ime.cursor_rect.width
        ch = ime.cursor_rect.height

        # Get screen height
        try:
            # Get window object from self (PygletTextView)
            view = ObjCInstance(self)
            window = view.window()
            screen = window.screen()

            # frame() returns NSRect
            frame = cocoapy.send_message(screen, "frame", restype=NSRect)
            screen_height = frame.size.height

            # Calculate screen coordinates (Cocoa: bottom-left origin)
            # Pyglet Window (wx, wy) is top-left of window content area in screen coords (top-left origin).

            # NSRect origin is bottom-left of the rect.
            origin_y = (screen_height - wy) - cy - ch
            origin_x = wx + cx

            rect = NSRect(NSPoint(origin_x, origin_y), NSSize(cw, ch))

        except Exception:
            exception_once(_logger, "ime_macos_first_rect_exc", "firstRectForCharacterRange failed")

        # Write result to pointer
        if result_ptr:
            ctypes.memmove(result_ptr, ctypes.byref(rect), ctypes.sizeof(NSRect))

    # Create the IMPs
    imp = IMP_TYPE(setMarkedText_impl)
    imp_ptr = ctypes.cast(imp, ctypes.c_void_p)

    imp_rect = IMP_TYPE_RECT(firstRectForCharacterRange_impl)
    imp_rect_ptr = ctypes.cast(imp_rect, ctypes.c_void_p)

    # Selector and types
    sel_name = b"setMarkedText:selectedRange:replacementRange:"
    sel = get_selector(sel_name)
    types = b"v@:@{_NSRange=QQ}{_NSRange=QQ}"

    sel_rect_name = b"firstRectForCharacterRange:actualRange:"
    sel_rect = get_selector(sel_rect_name)
    # NSRect return type is struct, encoded as {name=type...}
    # On x86_64, struct return might be handled differently in encoding string?
    # Usually it's just the struct encoding.
    # {_NSRect={_NSPoint=dd}{_NSSize=dd}}
    types_rect = b"{_NSRect={_NSPoint=dd}{_NSSize=dd}}@:{_NSRange=QQ}^{_NSRange=QQ}"

    _patch_installed = False

    def install_patch(window: Any) -> None:
        global _patch_installed

        # Register event type
        try:
            window.register_event_type("on_ime_composition")
        except Exception:
            exception_once(
                _logger,
                "ime_macos_register_event_type_exc",
                "register_event_type(on_ime_composition) raised",
            )

        # Get PygletTextView class
        PygletTextView = ObjCClass("PygletTextView")

        if not _patch_installed:
            # Add methods to class
            libobjc.class_addMethod.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p]
            libobjc.class_addMethod.restype = ctypes.c_bool

            libobjc.class_addMethod(PygletTextView, sel, imp_ptr, types)
            libobjc.class_addMethod(PygletTextView, sel_rect, imp_rect_ptr, types_rect)

            _patch_installed = True

        # Find the PygletTextView instance for this window
        # window._nswindow is PygletWindow (NSWindow)
        # window._nswindow.contentView() is PygletView
        # PygletView has _textview

        try:
            ns_window = window._nswindow
            content_view = ns_window.contentView()
            # content_view is a PygletView instance (ObjCInstance)
            # We need to get the associated _textview.
            # In pyglet_view.py: self.associate("_textview", textview)
            # We can use ObjCInstance helper or just get ivar?
            # associate uses objc_setAssociatedObject.
            # We can use get_associated_object if exposed, or just access the python wrapper if available.

            # Accessing ._textview on the ObjCInstance wrapper in Python should work if it was set in Python.
            # But content_view here is a *new* wrapper created from the pointer returned by contentView().
            # It won't have the _textview attribute set in Python __init__.

            # We need to use objc_getAssociatedObject.
            # Key is "_textview".
            # But pyglet uses a specific key?
            # In runtime.py:
            # def associate(self, name, value):
            #     _associated_objects.setdefault(self, {})[name] = value
            # It uses a Python dictionary `_associated_objects`!

            # So we need to find the original Python object for content_view.
            # pyglet doesn't seem to expose a way to look up Python object from pointer easily.

            # However, we can traverse subviews.
            # [contentView subviews] -> NSArray of subviews.
            # One of them is PygletTextView.

            subviews = content_view.subviews()
            count = subviews.count()
            for i in range(count):
                view = subviews.objectAtIndex_(i)
                if view.isKindOfClass_(PygletTextView):
                    # Found it!
                    ptr = view.ptr.value if hasattr(view, "ptr") else view.value
                    _ptr_to_window[ptr] = window
                    break

        except Exception as e:
            print(f"Failed to install IME patch: {e}")
