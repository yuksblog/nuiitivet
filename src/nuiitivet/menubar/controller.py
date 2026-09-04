"""Per-window menu bar state: the registered model and the rendering slots.

The :class:`MenuBarController` is created by ``Window`` and is the single place
that knows which model is registered and which slot widget currently renders
it. Slot widgets (the default one the App inserts below the chrome, and any
user-placed :class:`~nuiitivet.menubar.MenuBarArea`) register themselves on
mount; a mounted user area suppresses the default slot, so the model's pixels
move without the model itself going anywhere.
"""

from __future__ import annotations

import logging
import weakref
from typing import TYPE_CHECKING, Callable, List, Optional

from nuiitivet.common.logging_once import exception_once, warning_once

from nuiitivet.menus import MenuEntry, MenuRole

from .model import MenuBar

if TYPE_CHECKING:
    from nuiitivet.runtime.window import Window

    from .focus import MenuBarFocusCoordinator
    from .slots import MenuBarSlotBase

logger = logging.getLogger(__name__)

#: Window method per standard-item role. Activation goes through the owning
#: window (the app-scoped ``QUIT`` role through its App) even where the OS
#: could act directly (Stage 2: NSMenu), so app exit paths and window
#: management stay on the one code path.
_ROLE_ACTIONS: dict[MenuRole, "Callable[[Window], None]"] = {
    MenuRole.QUIT: lambda window: window.app.exit(),
    MenuRole.CLOSE_WINDOW: lambda window: window.close(),
    MenuRole.MINIMIZE: lambda window: window.minimize(),
    MenuRole.MAXIMIZE: lambda window: window.maximize(),
    MenuRole.RESTORE: lambda window: window.restore(),
    MenuRole.FULL_SCREEN: lambda window: window.full_screen(),
}


class MenuBarController:
    """Owns the registered :class:`MenuBar` model and the slot registry.

    Framework-internal: apps interact through ``Window(menu=...)`` and
    ``window.menu``; slot widgets register here on mount.
    """

    def __init__(self, window: "Window", model: Optional[MenuBar] = None) -> None:
        self._window = weakref.ref(window)
        self._model = model
        self._areas: List["MenuBarSlotBase"] = []
        self._defaults: List["MenuBarSlotBase"] = []
        # The App-wide focus coordinator on macOS (owns the NSMenu bridge and
        # keeps the global bar on the focused window's model); None everywhere
        # else.
        self._coordinator: Optional["MenuBarFocusCoordinator"] = None

    # ---- Model -----------------------------------------------------------

    @property
    def model(self) -> Optional[MenuBar]:
        """The registered menu model, or ``None``."""
        return self._model

    def set_model(self, model: Optional[MenuBar]) -> None:
        """Replace the model wholesale and rebuild the active surface."""
        if model is not None and not isinstance(model, MenuBar):
            raise TypeError("window.menu must be a MenuBar or None.")
        self._model = model
        if self._coordinator is not None:
            window = self._window()
            if window is not None:
                self._coordinator.model_changed(window)
        self._notify()

    # ---- Platform bridge -----------------------------------------------------

    def install_platform_bridge(self) -> None:
        """Hand the menu to the platform's native surface where one exists.

        Called by the Window once the backend window is up. On macOS every
        window — with or without its own menu — attaches to the App-wide
        :class:`~nuiitivet.menubar.focus.MenuBarFocusCoordinator`, which keeps
        the global menu bar on the focused window's model (the main window's
        standing in for ``menu=None``), and the in-app slots collapse.
        Elsewhere it is a no-op and the in-app bar keeps rendering.
        """
        if self._coordinator is not None:
            return
        from .nsmenu import NSMenuBridge

        if not NSMenuBridge.is_supported():
            return
        window = self._window()
        if window is None:
            return
        from .focus import MenuBarFocusCoordinator

        try:
            coordinator = MenuBarFocusCoordinator.attach(window.app)
        except Exception:
            exception_once(logger, "menubar_bridge_install_exc", "Menu bar coordinator attach raised")
            return
        self._coordinator = coordinator
        coordinator.window_created(window)
        # The native bar took over: every in-app slot collapses.
        self._notify()

    def os_focus_changed(self, active: bool) -> None:
        """Backend hook: this window gained or lost the OS focus."""
        if self._coordinator is None:
            return
        window = self._window()
        if window is not None:
            self._coordinator.focus_changed(window, active)

    def window_closed(self) -> None:
        """The owning window closed; release the global bar if it holds it."""
        if self._coordinator is None:
            return
        window = self._window()
        if window is not None:
            self._coordinator.window_closed(window)

    @property
    def native(self) -> bool:
        """True while the platform's native surface renders the menu (no
        in-app bar) — on macOS, for every window once attached: an unfocused
        window's menu waits for focus rather than rendering in-app."""
        return self._coordinator is not None

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
        if self._coordinator is not None:
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

    def activate(self, item: "MenuEntry") -> None:
        """Run an action item's command: toggle ``checked``, then act.

        The single activation path shared by every rendering surface — the
        in-app bar's popups and shortcuts, and the macOS ``NSMenu`` bridge —
        so checkable toggling and standard-item dispatch behave identically
        everywhere.
        """
        if item.checked is not None:
            item.checked.value = not bool(item.checked.value)
        if item.role is not MenuRole.NONE:
            self.dispatch_role(item.role)
        elif item.on_select is not None:
            from nuiitivet.widgeting.callbacks import invoke_event_handler

            invoke_event_handler(
                item.on_select,
                error_key="menubar_on_select",
                error_msg="MenuEntry on_select raised",
                owner_name="MenuEntry",
            )

    def dispatch_role(self, role: MenuRole) -> None:
        """Run the window method mapped to a standard-item role.

        Window-scoped roles call the owning window; the app-scoped ``QUIT``
        role calls that window's App.
        """
        action = _ROLE_ACTIONS.get(role)
        if action is None:
            return
        window = self._window()
        if window is None:
            return
        try:
            action(window)
        except Exception:
            exception_once(logger, "menubar_role_action_exc", f"Standard-item role {role.name} raised")
