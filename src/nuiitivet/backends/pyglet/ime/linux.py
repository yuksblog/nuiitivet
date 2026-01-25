import ctypes
import logging
import sys

from nuiitivet.common.logging_once import exception_once


_logger = logging.getLogger(__name__)

if sys.platform == "linux":
    try:
        xlib = ctypes.cdll.LoadLibrary("libX11.so.6")
    except OSError:
        exception_once(_logger, "ime_linux_xlib_load_exc", "Failed to load libX11.so.6")
        xlib = None

    if xlib:
        # Define types
        XIM = ctypes.c_void_p
        XIC = ctypes.c_void_p
        XID = ctypes.c_ulong
        Window = XID

        # Constants
        XIMPreeditArea = 0x0001
        XIMPreeditCallbacks = 0x0002
        XIMPreeditPosition = 0x0004
        XIMPreeditNothing = 0x0008
        XIMPreeditNone = 0x0010

        XIMStatusArea = 0x0100
        XIMStatusCallbacks = 0x0200
        XIMStatusNothing = 0x0400
        XIMStatusNone = 0x0800

        XNInputStyle = b"inputStyle"
        XNClientWindow = b"clientWindow"
        XNFocusWindow = b"focusWindow"
        XNPreeditAttributes = b"preeditAttributes"

        XNPreeditStartCallback = b"preeditStartCallback"
        XNPreeditDoneCallback = b"preeditDoneCallback"
        XNPreeditDrawCallback = b"preeditDrawCallback"
        XNPreeditCaretCallback = b"preeditCaretCallback"

        # Structures
        class XIMCallback(ctypes.Structure):
            _fields_ = [("client_data", ctypes.c_void_p), ("callback", ctypes.c_void_p)]  # function pointer

        class XVaNestedList(ctypes.Structure):
            pass  # Opaque

        class XIMPreeditDrawCallbackStruct(ctypes.Structure):
            _fields_ = [
                ("caret", ctypes.c_int),
                ("chg_first", ctypes.c_int),
                ("chg_length", ctypes.c_int),
                ("text", ctypes.c_void_p),  # XIMText *
            ]

        class XIMText(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ushort),
                ("feedback", ctypes.c_void_p),
                ("encoding_is_wchar", ctypes.c_int),
                ("string", ctypes.c_void_p),  # char* or wchar_t*
            ]

        class XIMPreeditCaretCallbackStruct(ctypes.Structure):
            _fields_ = [("position", ctypes.c_int), ("direction", ctypes.c_int), ("style", ctypes.c_int)]

        # Function prototypes
        xlib.XDestroyIC.argtypes = [XIC]
        xlib.XDestroyIC.restype = None

        xlib.XVaCreateNestedList.restype = ctypes.POINTER(XVaNestedList)
        # We define argtypes dynamically or use cast, but here we define for our specific usage
        xlib.XVaCreateNestedList.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(XIMCallback),
            ctypes.c_char_p,
            ctypes.POINTER(XIMCallback),
            ctypes.c_char_p,
            ctypes.POINTER(XIMCallback),
            ctypes.c_char_p,
            ctypes.POINTER(XIMCallback),
            ctypes.c_void_p,
        ]

        xlib.XCreateIC.restype = XIC
        xlib.XCreateIC.argtypes = [
            XIM,
            ctypes.c_char_p,
            ctypes.c_long,  # InputStyle
            ctypes.c_char_p,
            Window,  # ClientWindow
            ctypes.c_char_p,
            Window,  # FocusWindow
            ctypes.c_char_p,
            ctypes.POINTER(XVaNestedList),  # PreeditAttributes
            ctypes.c_void_p,
        ]

        # Callbacks
        CALLBACK_TYPE_START = ctypes.CFUNCTYPE(ctypes.c_int, XIC, ctypes.c_void_p, ctypes.c_void_p)
        CALLBACK_TYPE_DONE = ctypes.CFUNCTYPE(None, XIC, ctypes.c_void_p, ctypes.c_void_p)
        CALLBACK_TYPE_DRAW = ctypes.CFUNCTYPE(None, XIC, ctypes.c_void_p, ctypes.POINTER(XIMPreeditDrawCallbackStruct))
        CALLBACK_TYPE_CARET = ctypes.CFUNCTYPE(
            None, XIC, ctypes.c_void_p, ctypes.POINTER(XIMPreeditCaretCallbackStruct)
        )

        # Global references
        _callbacks = []
        _ic_map = {}  # XIC -> Window
        _composition_state = {}  # Window -> {text: str, cursor: int}

        def _preedit_start(ic, client_data, call_data):
            return -1  # No limit

        def _preedit_done(ic, client_data, call_data):
            window = _ic_map.get(ic.value if hasattr(ic, "value") else ic)
            if window:
                _composition_state[window] = {"text": "", "cursor": 0}
                try:
                    window.dispatch_event("on_ime_composition", "", 0, 0)
                except Exception:
                    exception_once(_logger, "ime_linux_preedit_done_dispatch_exc", "IME composition dispatch raised")
            return 0

        def _preedit_draw(ic, client_data, call_data):
            if not call_data:
                return
            data = call_data.contents
            window = _ic_map.get(ic.value if hasattr(ic, "value") else ic)
            if not window:
                return

            state = _composition_state.setdefault(window, {"text": "", "cursor": 0})
            current_text = state["text"]

            start = data.chg_first
            end = start + data.chg_length

            new_part = ""
            if data.text:
                xim_text = ctypes.cast(data.text, ctypes.POINTER(XIMText)).contents
                if xim_text.string:
                    if xim_text.encoding_is_wchar:
                        # wchar_t is usually 4 bytes on Linux (UCS-4)
                        new_part = ctypes.wstring_at(xim_text.string, xim_text.length)
                    else:
                        # char string
                        new_part = ctypes.string_at(xim_text.string).decode("utf-8", "ignore")

            # Update state
            # Handle bounds safely
            if start < 0:
                start = 0
            if end > len(current_text):
                end = len(current_text)

            prefix = current_text[:start]
            suffix = current_text[end:]
            new_text = prefix + new_part + suffix

            state["text"] = new_text
            state["cursor"] = data.caret

            try:
                window.dispatch_event("on_ime_composition", new_text, data.caret, 0)
            except Exception:
                exception_once(_logger, "ime_linux_preedit_draw_dispatch_exc", "IME composition dispatch raised")

        def _preedit_caret(ic, client_data, call_data):
            if not call_data:
                return
            data = call_data.contents
            window = _ic_map.get(ic.value if hasattr(ic, "value") else ic)
            if not window:
                return

            state = _composition_state.setdefault(window, {"text": "", "cursor": 0})
            state["cursor"] = data.position

            try:
                window.dispatch_event("on_ime_composition", state["text"], data.position, 0)
            except Exception:
                exception_once(_logger, "ime_linux_preedit_caret_dispatch_exc", "IME composition dispatch raised")

        def install_patch(window):
            if not xlib:
                return
            if not hasattr(window, "_x_display"):
                return

            try:
                window.register_event_type("on_ime_composition")
            except Exception:
                exception_once(
                    _logger,
                    "ime_linux_register_event_type_exc",
                    "register_event_type(on_ime_composition) raised",
                )

            # Pyglet stores IM on the display object
            im = getattr(window.display, "_x_im", None)
            win_handle = window._window

            if not im:
                return

            # Destroy existing IC if any
            if getattr(window, "_x_ic", None):
                xlib.XDestroyIC(window._x_ic)
                window._x_ic = None

            # Create callbacks
            cb_start = CALLBACK_TYPE_START(_preedit_start)
            cb_done = CALLBACK_TYPE_DONE(_preedit_done)
            cb_draw = CALLBACK_TYPE_DRAW(_preedit_draw)
            cb_caret = CALLBACK_TYPE_CARET(_preedit_caret)

            _callbacks.extend([cb_start, cb_done, cb_draw, cb_caret])

            # Create XIMCallback structs
            s_start = XIMCallback(None, ctypes.cast(cb_start, ctypes.c_void_p))
            s_done = XIMCallback(None, ctypes.cast(cb_done, ctypes.c_void_p))
            s_draw = XIMCallback(None, ctypes.cast(cb_draw, ctypes.c_void_p))
            s_caret = XIMCallback(None, ctypes.cast(cb_caret, ctypes.c_void_p))

            # Create NestedList
            preedit_attr = xlib.XVaCreateNestedList(
                0,
                XNPreeditStartCallback,
                ctypes.pointer(s_start),
                XNPreeditDoneCallback,
                ctypes.pointer(s_done),
                XNPreeditDrawCallback,
                ctypes.pointer(s_draw),
                XNPreeditCaretCallback,
                ctypes.pointer(s_caret),
                None,
            )

            # Create IC
            # Try XIMPreeditCallbacks | XIMStatusNothing
            style = XIMPreeditCallbacks | XIMStatusNothing

            ic = xlib.XCreateIC(
                im,
                XNInputStyle,
                style,
                XNClientWindow,
                win_handle,
                XNFocusWindow,
                win_handle,
                XNPreeditAttributes,
                preedit_attr,
                None,
            )

            if ic:
                window._x_ic = ic
                _ic_map[ic] = window
            else:
                # Fallback to default if failed
                # Pyglet's default usually works for basic input but no inline IME
                pass

    else:

        def install_patch(window):
            pass

else:

    def install_patch(window):
        pass
