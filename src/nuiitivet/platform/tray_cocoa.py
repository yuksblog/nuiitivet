"""macOS tray icon: ``TrayIcon`` model → ``NSStatusItem``.

Talks to AppKit through pyglet's bundled cocoapy, exactly like the global
menu bar bridge — no extra dependency, no extra thread, and the pumped event
loop hosts it as-is (verified by ``scripts/investigation/spike_tray_nsstatusitem.py``).
The menu is built by :class:`~nuiitivet.menubar.nsmenu.NSMenuBuilder`, so the
tray renders the same ``MenuBarItem`` model, with the same live Observable
sync, as every other native menu surface. Cocoa delivers both menu actions
and the status-button click on the main thread, so no marshalling is needed.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any, List, Optional

if sys.platform != "darwin":  # pragma: no cover - guards Darwin-only ObjC use
    raise ImportError("tray_cocoa is only available on macOS")

from nuiitivet.menubar.model import read_value
from nuiitivet.menubar.nsmenu import NSMenuBuilder
from nuiitivet.observable import ObservableBase, runtime

if TYPE_CHECKING:
    from .tray import TrayIcon

logger = logging.getLogger(__name__)

#: NSApplicationActivationPolicy values (stable Cocoa ABI).
_ACTIVATION_POLICY_REGULAR = 0
_ACTIVATION_POLICY_ACCESSORY = 1

#: Status-bar images render at menu-bar height; AppKit scales to this size.
_STATUS_IMAGE_POINTS = 18.0

_TRAY_TARGET_CLASS: Any = None
# Must stay referenced for the process lifetime — the ObjCSubclass owns the
# ctypes trampolines behind the registered IMPs (see nsmenu._menu_target_class).
_TRAY_TARGET_IMPLEMENTATION: Any = None


def _tray_target_class() -> Any:
    """Define (once) the Objective-C class receiving the status-button click."""
    global _TRAY_TARGET_CLASS, _TRAY_TARGET_IMPLEMENTATION
    if _TRAY_TARGET_CLASS is not None:
        return _TRAY_TARGET_CLASS

    from pyglet.libs.darwin.cocoapy import ObjCClass, ObjCSubclass

    class _Implementation:
        NuiitivetTrayTarget = ObjCSubclass("NSObject", "NuiitivetTrayTarget")

        @NuiitivetTrayTarget.method("v@")
        def nuiitivetTrayActivate_(self, sender: Any) -> None:
            tray: Optional["TrayIcon"] = getattr(self, "_tray", None)
            if tray is not None:
                tray._fire_activate()

    _TRAY_TARGET_IMPLEMENTATION = _Implementation
    _TRAY_TARGET_CLASS = ObjCClass("NuiitivetTrayTarget")
    return _TRAY_TARGET_CLASS


class TrayCocoaBridge:
    """Installs a :class:`TrayIcon` as an ``NSStatusItem``. Framework-internal."""

    def __init__(self, tray: "TrayIcon") -> None:
        self._tray = tray
        self._builder: Optional[NSMenuBuilder] = None
        self._item: Any = None
        self._subscriptions: List[Any] = []
        self._retained: List[Any] = []

    def install(self) -> None:
        """Create the status item; raises on failure (the model logs it)."""
        from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString, get_selector

        tray = self._tray
        NSStatusBar = ObjCClass("NSStatusBar")

        # NSVariableStatusItemLength == -1.0. The bar does not retain through
        # cocoapy, so retain explicitly or the item vanishes immediately.
        item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1.0)
        item.retain()
        self._item = item

        button = item.button()
        image = self._load_image()
        if image is not None:
            button.setImage_(image)
            self._retained.append(image)
        else:
            button.setTitle_(get_NSString(str(read_value(tray.tooltip) or "App")))
        self._sync_tooltip(button)

        if tray.menu:
            self._builder = NSMenuBuilder(tray._activate_item)
            item.setMenu_(self._builder.new_menu("Tray", tray.menu))
        elif tray._on_activate is not None:
            target = _tray_target_class().alloc().init()
            target._tray = tray  # read by nuiitivetTrayActivate_
            button.setTarget_(target)
            button.setAction_(get_selector("nuiitivetTrayActivate:"))
            self._retained.append(target)

        # "never" is applied once here; "auto" is driven by the App through
        # ``TrayIcon._refresh_dock`` → :meth:`set_dock_visible` as windows
        # show and hide.
        if tray.dock_visibility == "never":
            self.set_dock_visible(False)

    def uninstall(self) -> None:
        """Remove the status item and drop every reference."""
        from pyglet.libs.darwin.cocoapy import ObjCClass

        subscriptions, self._subscriptions = self._subscriptions, []
        for subscription in subscriptions:
            dispose = getattr(subscription, "dispose", None)
            if callable(dispose):
                dispose()
        if self._builder is not None:
            self._builder.dispose()
            self._builder = None

        item, self._item = self._item, None
        self._retained = []
        if item is not None:
            ObjCClass("NSStatusBar").systemStatusBar().removeStatusItem_(item)
            item.release()

    def set_dock_visible(self, visible: bool) -> None:
        """Switch the app between the regular (Dock) and accessory policies."""
        from pyglet.libs.darwin.cocoapy import ObjCClass

        policy = _ACTIVATION_POLICY_REGULAR if visible else _ACTIVATION_POLICY_ACCESSORY
        try:
            ObjCClass("NSApplication").sharedApplication().setActivationPolicy_(policy)
        except Exception:
            logger.debug("setActivationPolicy failed", exc_info=True)

    # ---- Pieces ------------------------------------------------------------

    def _load_image(self) -> Any:
        path = self._tray.icon_path
        if path is None:
            return None
        from pyglet.libs.darwin.cocoapy import NSMakeSize, ObjCClass, get_NSString

        NSImage = ObjCClass("NSImage")
        image = NSImage.alloc().initWithContentsOfFile_(get_NSString(str(path)))
        if image is None or not getattr(image, "ptr", None):
            logger.warning("Tray icon image failed to load: %s", path)
            return None
        image.setSize_(NSMakeSize(_STATUS_IMAGE_POINTS, _STATUS_IMAGE_POINTS))
        if path.stem.endswith("Template"):
            image.setTemplate_(True)
        return image

    def _sync_tooltip(self, button: Any) -> None:
        tray = self._tray

        def apply(_dt: float = 0.0) -> None:
            from pyglet.libs.darwin.cocoapy import get_NSString

            try:
                button.setToolTip_(get_NSString(str(read_value(tray.tooltip) or "")))
            except Exception:
                logger.debug("Tray tooltip sync failed", exc_info=True)

        apply()
        tooltip = tray.tooltip
        if isinstance(tooltip, ObservableBase):

            def on_change(_value: Any) -> None:
                runtime.clock.schedule_once(apply, 0.0)

            self._subscriptions.append(tooltip.subscribe(on_change))
