import ctypes
import logging
import sys
from typing import Any

from nuiitivet.common.logging_once import exception_once, warning_once


_logger = logging.getLogger(__name__)

# Only run on macOS
if sys.platform != "darwin":

    def install_patch(window: Any, win: Any) -> None:
        pass

    def discard_conversation(window: Any) -> None:
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

    # Maps keyed by PygletTextView pointer: the pyglet window composition
    # events are dispatched to, and the per-window IMEManager the candidate
    # window is positioned from. One entry per OS window.
    _ptr_to_window: dict[int, Any] = {}
    _ptr_to_ime: dict[int, Any] = {}

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
        # Default rect (0,0,0,0)
        rect = NSRect(NSPoint(0, 0), NSSize(0, 0))

        # This view's window owns the geometry being asked about, so read that
        # window's IMEManager — never another window's.
        ime = _ptr_to_ime.get(self)
        if ime is None:
            if result_ptr:
                ctypes.memmove(result_ptr, ctypes.byref(rect), ctypes.sizeof(NSRect))
            return

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
            if frame is None:
                warning_once(_logger, "ime_macos_screen_frame_none", "Screen frame is unavailable; using default rect")
            else:
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

    def _find_text_view(window: Any) -> Any:
        """Return the PygletTextView instance of ``window``, or ``None``.

        pyglet keeps its text view in a Python-side associated-objects dict
        that cannot be reached from a fresh ObjCInstance wrapper, so the view
        is found by scanning the content view's subviews instead.
        """
        PygletTextView = ObjCClass("PygletTextView")
        ns_window = window._nswindow
        content_view = ns_window.contentView()
        subviews = content_view.subviews()
        count = subviews.count()
        for i in range(count):
            view = subviews.objectAtIndex_(i)
            if view.isKindOfClass_(PygletTextView):
                return view
        return None

    def install_patch(window: Any, win: Any) -> None:
        """Install the IME hook on ``window``'s text view.

        ``window`` is the pyglet window (composition events are dispatched to
        it), ``win`` the nuiitivet Window model whose per-window ``ime`` state
        positions the candidate window.
        """
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

        try:
            view = _find_text_view(window)
            if view is not None:
                ptr = view.ptr.value if hasattr(view, "ptr") else view.value
                _ptr_to_window[ptr] = window
                _ptr_to_ime[ptr] = win.ime
        except Exception:
            exception_once(_logger, "ime_macos_install_patch_exc", "Failed to install IME patch")

    def discard_conversation(window: Any) -> None:
        """Drop the input method's conversation for ``window``.

        Called when the window loses the OS focus, after the model side
        committed the pending composition: ``discardMarkedText`` resets the
        input context without inserting or removing any text, so refocusing
        the window later starts a clean composition.
        """
        try:
            view = _find_text_view(window)
            if view is None:
                return
            input_context = view.inputContext()
            if input_context is not None:
                input_context.discardMarkedText()
        except Exception:
            exception_once(_logger, "ime_macos_discard_conversation_exc", "discardMarkedText raised")
