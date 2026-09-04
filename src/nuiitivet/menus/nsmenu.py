"""Shared :class:`MenuEntry` → ``NSMenu`` translation.

Builds native ``NSMenu`` trees from the surface-neutral menu model through
pyglet's bundled ``cocoapy`` (ctypes Objective-C bridge) — no new dependency.
Both native menu surfaces use it: the macOS global menu bar bridge
(``nuiitivet.menubar.nsmenu``) and the tray icon menu
(``nuiitivet.platform.tray_cocoa``), so every native surface renders the
model identically. ``key_equivalent`` is pure and imported and tested on
every platform; :class:`NSMenuBuilder`'s Objective-C imports happen lazily
and only on macOS.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT, resolve_modifiers
from nuiitivet.input.shortcut import Shortcut
from nuiitivet.observable import ObservableBase, runtime

from .model import MenuEntry

logger = logging.getLogger(__name__)

# NSEvent modifier flags (stable Cocoa ABI values).
_NS_SHIFT = 1 << 17
_NS_CONTROL = 1 << 18
_NS_OPTION = 1 << 19
_NS_COMMAND = 1 << 20

#: Keys whose NSMenuItem key equivalent is a function-key code point.
_FUNCTION_KEY_CODEPOINTS: Dict[str, int] = {
    "up": 0xF700,
    "down": 0xF701,
    "left": 0xF702,
    "right": 0xF703,
    "home": 0xF729,
    "end": 0xF72B,
    "pageup": 0xF72C,
    "pagedown": 0xF72D,
    "delete": 0xF728,
}

#: Keys whose key equivalent is a control character.
_CONTROL_CHARACTERS: Dict[str, str] = {
    "escape": "\x1b",
    "enter": "\r",
    "tab": "\t",
    "space": " ",
    "backspace": "\x08",
}


def key_equivalent(shortcut: Shortcut) -> Tuple[str, int]:
    """Translate a :class:`Shortcut` to an ``NSMenuItem`` key equivalent.

    Returns:
        ``(key_equivalent, modifier_mask)`` — an empty key equivalent means
        the gesture has no macOS representation and the item gets no
        accelerator.
    """
    mods = resolve_modifiers(shortcut.modifiers)
    mask = 0
    if mods & MOD_SHIFT:
        mask |= _NS_SHIFT
    if mods & MOD_CTRL:
        mask |= _NS_CONTROL
    if mods & MOD_ALT:
        mask |= _NS_OPTION
    if mods & MOD_META:
        mask |= _NS_COMMAND

    key = shortcut.key
    if len(key) == 1:
        return key.lower(), mask
    if key.startswith("f") and key[1:].isdigit():
        number = int(key[1:])
        if 1 <= number <= 12:
            return chr(0xF704 + number - 1), mask
        return "", 0
    codepoint = _FUNCTION_KEY_CODEPOINTS.get(key)
    if codepoint is not None:
        return chr(codepoint), mask
    character = _CONTROL_CHARACTERS.get(key)
    if character is not None:
        return character, mask
    return "", 0


class NSMenuBuilder:
    """Builds native ``NSMenu`` trees from :class:`MenuEntry` entries.

    Owns everything a native menu needs beyond the model: the Objective-C
    action target, Python-side references keeping AppKit objects alive, and
    the subscriptions syncing Observable ``label`` / ``enabled`` / ``checked``
    changes into the items. Shared by the global menu bar bridge and the tray
    icon so every native surface renders the model identically. ``activate``
    receives the :class:`MenuEntry` whose ``NSMenuItem`` fired, on the main
    thread.
    """

    def __init__(self, activate: Callable[[MenuEntry], None]) -> None:
        self._activate = activate
        self._actions: List[MenuEntry] = []
        self._subscriptions: List[Any] = []
        #: Python-side references to every ObjC object we created, so nothing
        #: is collected while AppKit still points at it.
        self._retained: List[Any] = []
        self._target: Any = None

    def new_menu(self, title: str, entries: Sequence[MenuEntry]) -> Any:
        """Create an ``NSMenu`` titled ``title`` holding ``entries``."""
        from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString

        NSMenu = ObjCClass("NSMenu")
        menu = NSMenu.alloc().initWithTitle_(get_NSString(title))
        menu.setAutoenablesItems_(False)
        self._retained.append(menu)
        self.fill_menu(menu, entries)
        return menu

    def retain(self, *objs: Any) -> None:
        """Keep Python-side references alive for the builder's lifetime."""
        self._retained.extend(objs)

    def dispose(self) -> None:
        """Drop subscriptions and references; menus stay until replaced."""
        subscriptions, self._subscriptions = self._subscriptions, []
        for subscription in subscriptions:
            dispose = getattr(subscription, "dispose", None)
            if callable(dispose):
                dispose()
        self._actions = []
        self._retained = []
        self._target = None

    def _activated(self, tag: int) -> None:
        """An ``NSMenuItem`` fired (click or key equivalent)."""
        if 0 <= tag < len(self._actions):
            self._activate(self._actions[tag])

    def fill_menu(self, ns_menu: Any, entries: Sequence[MenuEntry]) -> None:
        """Append ``entries`` (actions, separators, nested submenus) to ``ns_menu``."""
        from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString, get_selector

        NSMenu = ObjCClass("NSMenu")
        NSMenuItem = ObjCClass("NSMenuItem")

        for entry in entries:
            if entry.is_separator:
                ns_menu.addItem_(NSMenuItem.separatorItem())
                continue

            if entry.submenu is not None:
                holder = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    get_NSString(entry.resolved_label()), None, get_NSString("")
                )
                nested = NSMenu.alloc().initWithTitle_(get_NSString(entry.resolved_label()))
                nested.setAutoenablesItems_(False)
                self._retained.extend((holder, nested))
                holder.setEnabled_(entry.resolved_enabled())
                self.fill_menu(nested, entry.submenu)
                holder.setSubmenu_(nested)
                ns_menu.addItem_(holder)
                self._observe(entry, holder)
                continue

            key, mask = ("", 0)
            if entry.shortcut is not None:
                key, mask = key_equivalent(entry.shortcut)
            ns_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                get_NSString(entry.resolved_label()),
                get_selector("nuiitivetMenuAction:"),
                get_NSString(key),
            )
            self._retained.append(ns_item)
            if mask:
                ns_item.setKeyEquivalentModifierMask_(mask)
            ns_item.setTarget_(self._ensure_target())
            ns_item.setTag_(len(self._actions))
            self._actions.append(entry)
            ns_item.setEnabled_(entry.resolved_enabled())
            if entry.checked is not None:
                ns_item.setState_(1 if bool(entry.checked.value) else 0)
            ns_menu.addItem_(ns_item)
            self._observe(entry, ns_item)

    def _observe(self, entry: MenuEntry, ns_item: Any) -> None:
        """Wire the entry's Observable properties to the NSMenuItem's setters.

        Observables may fire off the UI thread; the setter is applied on the
        next clock tick, which runs on the main thread.
        """

        def apply(_dt: float = 0.0) -> None:
            from pyglet.libs.darwin.cocoapy import get_NSString

            try:
                ns_item.setTitle_(get_NSString(entry.resolved_label()))
                ns_item.setEnabled_(entry.resolved_enabled())
                if entry.checked is not None:
                    ns_item.setState_(1 if bool(entry.checked.value) else 0)
            except Exception:
                logger.debug("NSMenu item sync failed", exc_info=True)

        def on_change(_value: Any) -> None:
            runtime.clock.schedule_once(apply, 0.0)

        for prop in (entry.label, entry.enabled, entry.checked):
            if isinstance(prop, ObservableBase):
                self._subscriptions.append(prop.subscribe(on_change))

    def _ensure_target(self) -> Any:
        if self._target is None:
            target_class = _menu_target_class()
            self._target = target_class.alloc().init()
            self._target._builder = self  # read by nuiitivetMenuAction_
            self._retained.append(self._target)
        return self._target


_MENU_TARGET_CLASS: Any = None
# The implementation class MUST stay referenced for the lifetime of the
# process: the ObjCSubclass it holds owns the ctypes trampolines behind the
# registered IMPs, and letting it be collected leaves the Objective-C class
# pointing at freed function pointers (a segfault on the first menu click).
_MENU_TARGET_IMPLEMENTATION: Any = None


def _menu_target_class() -> Any:
    """Define (once) the Objective-C class receiving menu item actions."""
    global _MENU_TARGET_CLASS, _MENU_TARGET_IMPLEMENTATION
    if _MENU_TARGET_CLASS is not None:
        return _MENU_TARGET_CLASS

    from pyglet.libs.darwin.cocoapy import ObjCClass, ObjCSubclass

    class _Implementation:
        NuiitivetMenuTarget = ObjCSubclass("NSObject", "NuiitivetMenuTarget")

        @NuiitivetMenuTarget.method("v@")
        def nuiitivetMenuAction_(self, sender: Any) -> None:
            # cocoapy hands '@' arguments in as ObjCInstance already.
            builder: Optional[NSMenuBuilder] = getattr(self, "_builder", None)
            if builder is not None:
                builder._activated(int(sender.tag()))

    _MENU_TARGET_IMPLEMENTATION = _Implementation
    _MENU_TARGET_CLASS = ObjCClass("NuiitivetMenuTarget")
    return _MENU_TARGET_CLASS
