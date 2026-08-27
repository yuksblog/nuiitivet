"""macOS global menu bar bridge: menu model → ``NSMenu``.

On macOS the menu bar belongs at the top of the screen, not inside the
window, so the registered :class:`~nuiitivet.menubar.MenuBar` model is
translated to ``NSMenu`` through pyglet's bundled ``cocoapy`` (ctypes
Objective-C bridge) — no new dependency. Activation calls back into the
:class:`~nuiitivet.menubar.controller.MenuBarController`'s shared path, so
checkable toggling and standard-item intents behave exactly as they do under
the in-app bar; Cocoa delivers menu actions on the main thread, which is the
UI thread, so no marshalling is needed.

The module separates the **pure translation** (``key_equivalent``,
``plan_menus`` — imported and tested on every platform) from the **Cocoa
layer** (:class:`NSMenuBridge`, whose Objective-C imports happen lazily and
only on macOS). See ``docs/design/MENU_BAR.md``, Section 7.2.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from nuiitivet.input.codes import MOD_ALT, MOD_CTRL, MOD_META, MOD_SHIFT, resolve_modifiers
from nuiitivet.input.shortcut import Shortcut
from nuiitivet.observable import ObservableBase, runtime

from .model import MenuBar, MenuBarItem, MenuBarRole

if TYPE_CHECKING:
    from .controller import MenuBarController

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


@dataclass(frozen=True)
class PlanMenu:
    """One top-level menu of the translated bar: a title and its entries."""

    title: str
    entries: Tuple[MenuBarItem, ...]


def _strip_dangling_separators(entries: Sequence[MenuBarItem]) -> Tuple[MenuBarItem, ...]:
    """Drop leading/trailing separators and collapse runs left by removals."""
    result: List[MenuBarItem] = []
    for entry in entries:
        if entry.is_separator and (not result or result[-1].is_separator):
            continue
        result.append(entry)
    while result and result[-1].is_separator:
        result.pop()
    return tuple(result)


def plan_menus(model: MenuBar, app_name: str) -> List[PlanMenu]:
    """Arrange the model for the macOS menu bar.

    macOS requires an application menu as the first menu. A ``quit()``
    standard item found as a direct child of a top-level menu is relocated
    into it (that is its conventional place); when the model has none, one is
    synthesized. Everything else keeps the author's order. A top-level action
    item (no submenu) degrades to a menu holding that single entry, since the
    global bar has no direct-action titles.
    """
    quit_item: Optional[MenuBarItem] = None
    menus: List[PlanMenu] = []

    for top in model.items:
        if top.is_separator:
            continue
        if top.submenu is not None:
            entries: List[MenuBarItem] = []
            for entry in top.submenu:
                if quit_item is None and entry.role is MenuBarRole.QUIT:
                    quit_item = entry
                    continue
                entries.append(entry)
            menus.append(PlanMenu(top.resolved_label(), _strip_dangling_separators(entries)))
        else:
            if quit_item is None and top.role is MenuBarRole.QUIT:
                quit_item = top
                continue
            menus.append(PlanMenu(top.resolved_label(), (top,)))

    app_entries = (quit_item if quit_item is not None else MenuBarItem.quit(),)
    return [PlanMenu(app_name, app_entries), *menus]


class NSMenuBridge:
    """Installs the menu model as the macOS global menu bar.

    Created by the :class:`~nuiitivet.menubar.controller.MenuBarController`
    once the pyglet window exists; framework-internal. ``install()`` rebuilds
    the whole ``NSMenu`` tree (structure is replaced wholesale, matching the
    model contract), while Observable ``label`` / ``enabled`` / ``checked``
    changes flow through targeted setters without a rebuild.
    """

    @staticmethod
    def is_supported() -> bool:
        """True when the platform can host the bridge (macOS with cocoapy)."""
        if sys.platform != "darwin":
            return False
        try:
            import pyglet.libs.darwin.cocoapy  # noqa: F401
        except Exception:
            return False
        return True

    def __init__(self, controller: "MenuBarController", *, app_name: str) -> None:
        self._controller = controller
        self._app_name = app_name
        self._actions: List[MenuBarItem] = []
        self._subscriptions: List[Any] = []
        #: Python-side references to every ObjC object we created, so nothing
        #: is collected while AppKit still points at it.
        self._retained: List[Any] = []
        self._target: Any = None

    # ---- Install / teardown ----------------------------------------------

    def install(self, model: Optional[MenuBar]) -> None:
        """Replace the global menu bar with ``model`` (``None`` → app menu only)."""
        from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString

        self._dispose_subscriptions()
        self._actions = []
        self._retained = []

        NSApplication = ObjCClass("NSApplication")
        NSMenu = ObjCClass("NSMenu")

        main_menu = NSMenu.alloc().initWithTitle_(get_NSString("MainMenu"))
        self._retained.append(main_menu)

        plans = plan_menus(model, self._app_name) if model is not None else plan_menus(
            MenuBar([]), self._app_name
        )
        for plan in plans:
            self._add_top_menu(main_menu, plan)

        NSApplication.sharedApplication().setMainMenu_(main_menu)
        logger.debug("NSMenu bridge installed %d top-level menus", len(plans))

    def uninstall(self) -> None:
        """Drop subscriptions and references; the menu itself stays until replaced."""
        self._dispose_subscriptions()
        self._actions = []
        self._retained = []
        self._target = None

    # ---- Activation ---------------------------------------------------------

    def _activated(self, tag: int) -> None:
        """An ``NSMenuItem`` fired (click or key equivalent)."""
        if 0 <= tag < len(self._actions):
            self._controller.activate(self._actions[tag])

    # ---- Translation ---------------------------------------------------------

    def _add_top_menu(self, main_menu: Any, plan: PlanMenu) -> None:
        from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString

        NSMenu = ObjCClass("NSMenu")
        NSMenuItem = ObjCClass("NSMenuItem")

        holder = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_NSString(plan.title), None, get_NSString("")
        )
        submenu = NSMenu.alloc().initWithTitle_(get_NSString(plan.title))
        submenu.setAutoenablesItems_(False)
        self._retained.extend((holder, submenu))
        self._fill_menu(submenu, plan.entries)
        holder.setSubmenu_(submenu)
        main_menu.addItem_(holder)

    def _fill_menu(self, ns_menu: Any, entries: Sequence[MenuBarItem]) -> None:
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
                self._fill_menu(nested, entry.submenu)
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

    # ---- Live property sync ----------------------------------------------------

    def _observe(self, entry: MenuBarItem, ns_item: Any) -> None:
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

    def _dispose_subscriptions(self) -> None:
        subscriptions, self._subscriptions = self._subscriptions, []
        for subscription in subscriptions:
            dispose = getattr(subscription, "dispose", None)
            if callable(dispose):
                dispose()

    # ---- Objective-C target -------------------------------------------------

    def _ensure_target(self) -> Any:
        if self._target is None:
            target_class = _menu_target_class()
            self._target = target_class.alloc().init()
            self._target._bridge = self  # read by nuiitivetMenuAction_
            self._retained.append(self._target)
        return self._target


_MENU_TARGET_CLASS: Any = None


def _menu_target_class() -> Any:
    """Define (once) the Objective-C class receiving menu item actions."""
    global _MENU_TARGET_CLASS
    if _MENU_TARGET_CLASS is not None:
        return _MENU_TARGET_CLASS

    from pyglet.libs.darwin.cocoapy import ObjCClass, ObjCInstance, ObjCSubclass

    class _Implementation:
        NuiitivetMenuTarget = ObjCSubclass("NSObject", "NuiitivetMenuTarget")

        @NuiitivetMenuTarget.method("v@")
        def nuiitivetMenuAction_(self, sender: Any) -> None:
            bridge: Optional[NSMenuBridge] = getattr(self, "_bridge", None)
            if bridge is not None:
                bridge._activated(int(ObjCInstance(sender).tag()))

    _MENU_TARGET_CLASS = ObjCClass("NuiitivetMenuTarget")
    return _MENU_TARGET_CLASS
