"""In-process macOS notifications via ``UNUserNotificationCenter``.

Posts through the UserNotifications framework with pyglet's bundled ObjC
bridge, so a delivered notification carries the app's own name and icon and
appears with no helper-process latency.

The framework is only usable from a process with a bundle identifier — i.e. a
packaged ``.app``, not a plain ``python app.py`` run. Touching
``currentNotificationCenter`` without one does not fail politely: it aborts
with an uncatchable ObjC exception. Construction therefore checks the main
bundle first and raises, so the caller falls back to the osascript backend.

Authorization is requested once at construction; its completion handler is an
ObjC block, which ctypes cannot express directly, so a global-block literal is
assembled by hand (ABI: isa / flags / reserved / invoke / descriptor).
"""

from __future__ import annotations

import ctypes
import logging
import sys
import uuid

if sys.platform != "darwin":  # pragma: no cover - guards Darwin-only ObjC use
    raise ImportError("notification_cocoa is only available on macOS")

from pyglet.libs.darwin import cocoapy

from nuiitivet.common.logging_once import warning_once
from .notification import NotificationBackend, NotificationError


logger = logging.getLogger(__name__)

# Load the UserNotifications framework so its classes are registered with the
# ObjC runtime; nothing else in the process links it.
ctypes.CDLL("/System/Library/Frameworks/UserNotifications.framework/UserNotifications")

_UN_AUTHORIZATION_OPTION_SOUND = 1 << 1
_UN_AUTHORIZATION_OPTION_ALERT = 1 << 2


class _BlockDescriptor(ctypes.Structure):
    _fields_ = [("reserved", ctypes.c_ulong), ("size", ctypes.c_ulong)]


class _BlockLiteral(ctypes.Structure):
    _fields_ = [
        ("isa", ctypes.c_void_p),
        ("flags", ctypes.c_int32),
        ("reserved", ctypes.c_int32),
        ("invoke", ctypes.c_void_p),
        ("descriptor", ctypes.POINTER(_BlockDescriptor)),
    ]


_BLOCK_IS_GLOBAL = 1 << 28

# void (^)(BOOL granted, NSError *error); the leading pointer is the block.
_AUTH_HANDLER_FUNC = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_bool, ctypes.c_void_p
)


def _on_authorization(_block: int, granted: bool, _error: int) -> None:
    if not granted:
        warning_once(
            logger,
            "notification_authorization_denied",
            "notification authorization was denied; notifications will not "
            "be shown until enabled in System Settings > Notifications",
        )


# Everything referenced by the block literal must outlive it; keep module refs.
_auth_callback = _AUTH_HANDLER_FUNC(_on_authorization)
_auth_descriptor = _BlockDescriptor(0, ctypes.sizeof(_BlockLiteral))
_auth_block = _BlockLiteral(
    ctypes.addressof(ctypes.c_void_p.in_dll(ctypes.CDLL(None), "_NSConcreteGlobalBlock")),
    _BLOCK_IS_GLOBAL,
    0,
    ctypes.cast(_auth_callback, ctypes.c_void_p),
    ctypes.pointer(_auth_descriptor),
)


def _objc_str_or_none(instance: object) -> str | None:
    if instance is None:
        return None
    ptr = getattr(instance, "ptr", None)
    if ptr is None or not ptr.value:
        return None
    return cocoapy.cfstring_to_string(instance)


class CocoaNotificationBackend(NotificationBackend):
    """macOS notifications via in-process ``UNUserNotificationCenter``."""

    def __init__(self) -> None:
        bundle = cocoapy.ObjCClass("NSBundle").mainBundle()
        identifier = _objc_str_or_none(bundle.bundleIdentifier() if bundle else None)
        if not identifier:
            raise NotificationError(
                "process has no bundle identifier; "
                "UNUserNotificationCenter requires an app bundle"
            )
        self._pool_cls = cocoapy.ObjCClass("NSAutoreleasePool")
        self._content_cls = cocoapy.ObjCClass("UNMutableNotificationContent")
        self._request_cls = cocoapy.ObjCClass("UNNotificationRequest")
        center = cocoapy.ObjCClass("UNUserNotificationCenter").currentNotificationCenter()
        if center is None or not center.ptr.value:
            raise NotificationError("UNUserNotificationCenter is unavailable")
        center.retain()
        self._center = center
        # First call shows the system permission prompt; later calls resolve
        # from the recorded choice without UI. The block parameter defeats
        # cocoapy's argtype introspection, so every argument must be an
        # explicit ctypes object (a bare int would be truncated to c_int).
        self._center.requestAuthorizationWithOptions_completionHandler_(
            ctypes.c_ulonglong(
                _UN_AUTHORIZATION_OPTION_ALERT | _UN_AUTHORIZATION_OPTION_SOUND
            ),
            ctypes.c_void_p(ctypes.addressof(_auth_block)),
        )

    def notify(self, title: str, body: str) -> None:
        # A pool per call: get_NSString autoreleases, and worker threads have
        # no pool of their own.
        pool = self._pool_cls.alloc().init()
        try:
            content = self._content_cls.alloc().init()
            content.setTitle_(cocoapy.get_NSString(title))
            if body:
                content.setBody_(cocoapy.get_NSString(body))
            request = self._request_cls.requestWithIdentifier_content_trigger_(
                cocoapy.get_NSString(str(uuid.uuid4())), content, None
            )
            # nil trigger = deliver immediately; nil handler = fire-and-forget.
            self._center.addNotificationRequest_withCompletionHandler_(request, None)
            content.release()
        finally:
            pool.drain()
