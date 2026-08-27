"""Per-App menu bar state: the registered model and the rendering slots.

The :class:`MenuBarController` is created by ``App`` and is the single place
that knows which model is registered and which slot widget currently renders
it. Slot widgets (the default one the App inserts below the chrome, and any
user-placed :class:`~nuiitivet.menubar.MenuBarArea`) register themselves on
mount; a mounted user area suppresses the default slot, so the model's pixels
move without the model itself going anywhere. See ``docs/design/MENU_BAR.md``.
"""

from __future__ import annotations

import logging
import weakref
from typing import TYPE_CHECKING, List, Optional

from nuiitivet.common.logging_once import exception_once, warning_once
from nuiitivet.runtime.intents import (
    CloseWindowIntent,
    ExitAppIntent,
    FullScreenIntent,
    MaximizeWindowIntent,
    MinimizeWindowIntent,
    RestoreWindowIntent,
)

from .model import MenuBar, MenuBarItem, MenuBarRole

if TYPE_CHECKING:
    from nuiitivet.runtime.app import App

    from .nsmenu import NSMenuBridge
    from .slots import MenuBarSlotBase

logger = logging.getLogger(__name__)

#: Intent factory per standard-item role. Activation goes through
#: ``App.dispatch`` even where the OS could act directly (Stage 2: NSMenu),
#: so app exit paths and window management stay on the one code path.
_ROLE_INTENTS = {
    MenuBarRole.QUIT: ExitAppIntent,
    MenuBarRole.CLOSE_WINDOW: CloseWindowIntent,
    MenuBarRole.MINIMIZE: MinimizeWindowIntent,
    MenuBarRole.MAXIMIZE: MaximizeWindowIntent,
    MenuBarRole.RESTORE: RestoreWindowIntent,
    MenuBarRole.FULL_SCREEN: FullScreenIntent,
}


class MenuBarController:
    """Owns the registered :class:`MenuBar` model and the slot registry.

    Framework-internal: apps interact through ``App(menu=...)`` and
    ``app.menu``; slot widgets register here on mount.
    """

    def __init__(self, app: "App", model: Optional[MenuBar] = None) -> None:
        self._app = weakref.ref(app)
        self._model = model
        self._areas: List["MenuBarSlotBase"] = []
        self._defaults: List["MenuBarSlotBase"] = []
        # NSMenuBridge on macOS; None everywhere else.
        self._bridge: Optional["NSMenuBridge"] = None

    # ---- Model -----------------------------------------------------------

    @property
    def model(self) -> Optional[MenuBar]:
        """The registered menu model, or ``None``."""
        return self._model

    def set_model(self, model: Optional[MenuBar]) -> None:
        """Replace the model wholesale and rebuild the active surface."""
        if model is not None and not isinstance(model, MenuBar):
            raise TypeError("app.menu must be a MenuBar or None.")
        self._model = model
        if self._bridge is not None:
            try:
                self._bridge.install(model)
            except Exception:
                exception_once(logger, "menubar_bridge_reinstall_exc", "NSMenu bridge reinstall raised")
        self._notify()

    # ---- Platform bridge -----------------------------------------------------

    def install_platform_bridge(self) -> None:
        """Hand the menu to the platform's native surface where one exists.

        Called by the App once the backend window is up. On macOS this
        installs the :class:`~nuiitivet.menubar.nsmenu.NSMenuBridge` (the
        global menu bar) and the in-app slots collapse; elsewhere it is a
        no-op and the in-app bar keeps rendering.
        """
        if self._bridge is not None or self._model is None:
            return
        from .nsmenu import NSMenuBridge

        if not NSMenuBridge.is_supported():
            return
        app = self._app()
        app_name = None
        if app is not None:
            title = getattr(app, "_title_value", None)
            value = getattr(title, "value", title)
            if value:
                app_name = str(value)
        try:
            bridge = NSMenuBridge(self, app_name=app_name or "App")
            bridge.install(self._model)
        except Exception:
            exception_once(logger, "menubar_bridge_install_exc", "NSMenu bridge install raised")
            return
        self._bridge = bridge
        # The native bar took over: every in-app slot collapses.
        self._notify()

    @property
    def native(self) -> bool:
        """True while a platform bridge renders the menu (no in-app bar)."""
        return self._bridge is not None

    # ---- Slot registry -----------------------------------------------------

    def register_slot(self, slot: "MenuBarSlotBase") -> None:
        """A slot widget mounted. User areas take over from the default slot."""
        registry = self._areas if slot.is_user_area else self._defaults
        if slot in registry:
            return
        if slot.is_user_area and self._areas:
            # Two mounted MenuBarAreas is an authoring error. Raising here
            # would break the mount of an otherwise valid tree (and hot
            # reload with it), so the extra area is inert instead.
            warning_once(
                logger,
                "menubar_duplicate_area",
                "Multiple MenuBarArea widgets are mounted; only the first renders the menu bar.",
            )
        registry.append(slot)
        self._notify()

    def unregister_slot(self, slot: "MenuBarSlotBase") -> None:
        """A slot widget unmounted."""
        for registry in (self._areas, self._defaults):
            if slot in registry:
                registry.remove(slot)
        self._notify()

    def active_slot(self) -> Optional["MenuBarSlotBase"]:
        """The slot that should render the bar: the first mounted user area,
        else the most recently mounted default slot (hot reload mounts the new
        tree's slot while the old one is torn down). ``None`` while a platform
        bridge renders the menu natively."""
        if self._bridge is not None:
            return None
        if self._areas:
            return self._areas[0]
        if self._defaults:
            return self._defaults[-1]
        return None

    def _notify(self) -> None:
        active = self.active_slot()
        for registry in (self._areas, self._defaults):
            for slot in registry:
                slot.menubar_changed(active=slot is active, model=self._model)

    # ---- Activation ---------------------------------------------------------

    def activate(self, item: "MenuBarItem") -> None:
        """Run an action item's command: toggle ``checked``, then act.

        The single activation path shared by every rendering surface — the
        in-app bar's popups and shortcuts, and the macOS ``NSMenu`` bridge —
        so checkable toggling and standard-item dispatch behave identically
        everywhere.
        """
        if item.checked is not None:
            item.checked.value = not bool(item.checked.value)
        if item.role is not MenuBarRole.NONE:
            self.dispatch_role(item.role)
        elif item.on_select is not None:
            from nuiitivet.widgeting.callbacks import invoke_event_handler

            invoke_event_handler(
                item.on_select,
                error_key="menubar_on_select",
                error_msg="MenuBarItem on_select raised",
                owner_name="MenuBarItem",
            )

    def dispatch_role(self, role: MenuBarRole) -> None:
        """Dispatch the built-in intent mapped to a standard-item role."""
        factory = _ROLE_INTENTS.get(role)
        if factory is None:
            return
        app = self._app()
        if app is not None:
            app.dispatch(factory())
