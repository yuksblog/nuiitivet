"""macOS global menu bar bridge: menu bar model → ``NSMenu``.

On macOS the menu bar belongs at the top of the screen, not inside the
window, so the registered :class:`~nuiitivet.menubar.MenuBar` model is
installed as the application's main menu. Activation calls back into the
:class:`~nuiitivet.menubar.controller.MenuBarController`'s shared path, so
checkable toggling and standard-item intents behave exactly as they do under
the in-app bar; Cocoa delivers menu actions on the main thread, which is the
UI thread, so no marshalling is needed.

The module separates the **pure translation** (``plan_menus`` — imported and
tested on every platform) from the **Cocoa layer** (:class:`NSMenuBridge`,
whose Objective-C imports happen lazily and only on macOS). The entry-level
``MenuEntry`` → ``NSMenu`` translation itself lives in
:mod:`nuiitivet.menus.nsmenu`, shared with the tray icon.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional, Sequence, Tuple

from nuiitivet.menus import MenuEntry, MenuRole
from nuiitivet.menus.nsmenu import NSMenuBuilder

from .model import MenuBar

if TYPE_CHECKING:
    from .controller import MenuBarController

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlanMenu:
    """One top-level menu of the translated bar: a title and its entries."""

    title: str
    entries: Tuple[MenuEntry, ...]


def _strip_dangling_separators(entries: Sequence[MenuEntry]) -> Tuple[MenuEntry, ...]:
    """Drop leading/trailing separators and collapse runs left by removals."""
    result: List[MenuEntry] = []
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
    quit_item: Optional[MenuEntry] = None
    menus: List[PlanMenu] = []

    for top in model.items:
        if top.is_separator:
            continue
        if top.submenu is not None:
            entries: List[MenuEntry] = []
            for entry in top.submenu:
                if quit_item is None and entry.role is MenuRole.QUIT:
                    quit_item = entry
                    continue
                entries.append(entry)
            menus.append(PlanMenu(top.resolved_label(), _strip_dangling_separators(entries)))
        else:
            if quit_item is None and top.role is MenuRole.QUIT:
                quit_item = top
                continue
            menus.append(PlanMenu(top.resolved_label(), (top,)))

    app_entries = (quit_item if quit_item is not None else MenuEntry.quit(),)
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
        self._builder: Optional[NSMenuBuilder] = None

    # ---- Install / teardown ----------------------------------------------

    def install(self, model: Optional[MenuBar]) -> None:
        """Replace the global menu bar with ``model`` (``None`` → app menu only)."""
        from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString

        if self._builder is not None:
            self._builder.dispose()
        self._builder = NSMenuBuilder(self._controller.activate)

        NSApplication = ObjCClass("NSApplication")
        NSMenu = ObjCClass("NSMenu")

        main_menu = NSMenu.alloc().initWithTitle_(get_NSString("MainMenu"))
        self._builder.retain(main_menu)

        plans = plan_menus(model, self._app_name) if model is not None else plan_menus(
            MenuBar([]), self._app_name
        )
        for plan in plans:
            self._add_top_menu(main_menu, plan)

        NSApplication.sharedApplication().setMainMenu_(main_menu)
        logger.debug("NSMenu bridge installed %d top-level menus", len(plans))

    def uninstall(self) -> None:
        """Drop subscriptions and references; the menu itself stays until replaced."""
        if self._builder is not None:
            self._builder.dispose()
            self._builder = None

    # ---- Translation ---------------------------------------------------------

    def _add_top_menu(self, main_menu: Any, plan: PlanMenu) -> None:
        from pyglet.libs.darwin.cocoapy import ObjCClass, get_NSString

        NSMenuItem = ObjCClass("NSMenuItem")

        assert self._builder is not None
        holder = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            get_NSString(plan.title), None, get_NSString("")
        )
        submenu = self._builder.new_menu(plan.title, plan.entries)
        self._builder.retain(holder)
        holder.setSubmenu_(submenu)
        main_menu.addItem_(holder)
