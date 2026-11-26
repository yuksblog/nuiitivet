"""macOS: raise text motions for the text commands pyglet drops.

AppKit turns a key into a text command and sends it to the focused text
view. pyglet's ``PygletTextView`` raises ``on_text_motion`` for a fixed set of
commands; any other runs on pyglet's own empty view and raises nothing. This
module adds the commands of ``Ctrl+F/B/A/E`` and ``Cmd+←/→``, plain and with
Shift, to the view class through the Objective-C runtime.

No-op on other platforms.
"""

import sys
from typing import Any

from pyglet.window import key

_MOVES: dict[str, int] = {
    "moveForward": key.MOTION_RIGHT,
    "moveBackward": key.MOTION_LEFT,
    "moveToBeginningOfParagraph": key.MOTION_BEGINNING_OF_LINE,
    "moveToEndOfParagraph": key.MOTION_END_OF_LINE,
    "moveToLeftEndOfLine": key.MOTION_BEGINNING_OF_LINE,
    "moveToRightEndOfLine": key.MOTION_END_OF_LINE,
}

#: AppKit text command -> the pyglet window event it raises, and that event's motion.
COMMANDS: dict[str, tuple[str, int]] = {
    **{f"{name}:": ("on_text_motion", motion) for name, motion in _MOVES.items()},
    **{f"{name}AndModifySelection:": ("on_text_motion_select", motion) for name, motion in _MOVES.items()},
}

if sys.platform != "darwin":

    def install_patch() -> None:
        pass

else:
    import ctypes
    import logging
    from typing import Optional

    from pyglet.libs.darwin import cocoapy
    from pyglet.libs.darwin.cocoapy import ObjCClass, ObjCInstance, get_selector

    from nuiitivet.common.logging_once import exception_once

    _logger = logging.getLogger(__name__)

    libobjc = cocoapy.objc

    def _selector(name: str) -> int:
        """The selector *name* as the pointer an IMP receives."""
        return int(get_selector(name).value or 0)

    _selector_events: dict[int, tuple[str, int]] = {_selector(name): event for name, event in COMMANDS.items()}

    # Ctrl+O sends this command and then ``moveBackward:``. Raised alone, that
    # move would walk the caret back with no line break in front of it.
    _OPEN_LINE = _selector("insertNewlineIgnoringFieldEditor:")
    _MOVE_BACKWARD = _selector("moveBackward:")
    # The timestamp of the key event that last sent ``_OPEN_LINE``.
    _open_line_time: Optional[float] = None

    def _event_time() -> Optional[float]:
        """The timestamp of the event AppKit is handling, or ``None`` outside one."""
        event = ObjCClass("NSApplication").sharedApplication().currentEvent()
        return None if event is None else float(event.timestamp())

    # void (*IMP)(id, SEL, id)
    IMP_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

    def _command_impl(self: int, cmd: int, sender: Any) -> None:
        global _open_line_time
        try:
            if cmd == _OPEN_LINE:
                _open_line_time = _event_time()
                return
            if cmd == _MOVE_BACKWARD and _open_line_time is not None and _event_time() == _open_line_time:
                return
            # The view names its own window, as pyglet's commands read it: a
            # window that goes full screen gets a new view.
            window = getattr(ObjCInstance(self), "_window", None)
            if window is not None:
                window.dispatch_event(*_selector_events[cmd])
        except Exception:
            exception_once(_logger, "text_commands_macos_dispatch_exc", "Text command dispatch raised")

    _imp = IMP_TYPE(_command_impl)
    _imp_ptr = ctypes.cast(_imp, ctypes.c_void_p)
    _types = b"v@:@"

    _patch_installed = False

    def install_patch() -> None:
        """Add the commands to pyglet's text view class. Every view of every window then raises them."""
        global _patch_installed

        if _patch_installed:
            return
        try:
            text_view_class = ObjCClass("PygletTextView")
            libobjc.class_addMethod.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_char_p,
            ]
            libobjc.class_addMethod.restype = ctypes.c_bool
            for selector in (*_selector_events, _OPEN_LINE):
                libobjc.class_addMethod(text_view_class, selector, _imp_ptr, _types)
            _patch_installed = True
        except Exception:
            exception_once(_logger, "text_commands_macos_install_exc", "Failed to install the text command patch")
