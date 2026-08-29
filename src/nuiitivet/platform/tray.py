"""System tray icon (menu-bar extra on macOS): the ``TrayIcon`` model.

Declarative and App-owned, symmetric with the menu bar: construct a
:class:`TrayIcon` and hand it to ``App(window, tray=...)``. The running
backend installs it when the event loop starts and removes it when the app
exits — the icon lives exactly as long as the app runs and has no lifecycle
or policy of its own. It never affects the App's exit policy; a resident app
declares ``ExitPolicy.EXPLICIT`` itself.

The menu reuses :class:`~nuiitivet.menubar.model.MenuEntry`, so Observable
``label`` / ``enabled`` / ``checked`` propagate live to the native menu, the
same as the menu bar. Install success is queryable through
:attr:`TrayIcon.installed`; a failure never takes the app down (the
``Desktop.notify`` policy: log once, stay up) — apps that treat the tray as
essential read ``installed`` and decide for themselves.
"""

from __future__ import annotations

import logging
import sys
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Sequence, Tuple, Union

from nuiitivet.common.logging_once import exception_once, warning_once
from nuiitivet.menus import MenuEntry, MenuRole, ObservableStr
from nuiitivet.observable import Observable, ObservableBase
from nuiitivet.widgeting.callbacks import VoidCallback, invoke_event_handler

if TYPE_CHECKING:
    from nuiitivet.runtime.app import App

logger = logging.getLogger(__name__)

_DOCK_VISIBILITIES = ("always", "auto", "never")


class TrayIcon:
    """A system tray icon: image, tooltip, menu, and an activate callback.

    Args:
        icon: Path to the icon image file (PNG recommended). On macOS a
            filename stem ending in ``Template`` is loaded as a template
            image, so the system recolors it for light/dark menu bars.
            Without an icon the tray shows the tooltip text (macOS) or a
            neutral placeholder — real apps should always ship an icon.
        tooltip: Hover text; a plain string or an Observable one.
        menu: The tray menu as :class:`MenuEntry` entries — actions,
            separators, submenus and checkable items, exactly as in the menu
            bar. ``MenuEntry.quit()`` works (a resident app should include
            it: while no window is visible the tray menu is the only exit
            path). Window-scoped standard items (close/minimize/...) have no
            target window here and are ignored with a warning.
        on_activate: Called when the icon itself is activated the platform's
            conventional way. Support varies: on macOS only without a
            ``menu`` (a menu owns the click there); on Windows the gesture
            is a double-click; a Linux AppIndicator host cannot deliver it
            at all (a pystray limitation). Treat it as an optional shortcut
            and keep an equivalent entry in ``menu``.
        dock_visibility: macOS Dock presence: ``"always"`` (default),
            ``"auto"`` (in the Dock only while some window is visible — the
            close-to-tray convention), or ``"never"`` (a pure menu-bar-extra
            app; the process gets no Dock icon or Cmd+Tab entry). Ignored on
            Windows/Linux, where the taskbar entry follows window visibility
            by itself.
    """

    def __init__(
        self,
        *,
        icon: Optional[Union[str, Path]] = None,
        tooltip: ObservableStr = "",
        menu: Optional[Sequence[MenuEntry]] = None,
        on_activate: Optional[VoidCallback] = None,
        dock_visibility: str = "always",
    ) -> None:
        entries: Tuple[MenuEntry, ...] = tuple(menu) if menu is not None else ()
        for entry in entries:
            if not isinstance(entry, MenuEntry):
                raise TypeError("TrayIcon menu entries must be MenuEntry instances.")
        if dock_visibility not in _DOCK_VISIBILITIES:
            raise ValueError(
                f"dock_visibility must be one of {_DOCK_VISIBILITIES}, got {dock_visibility!r}."
            )
        self._icon_path: Optional[Path] = Path(icon) if icon is not None else None
        self._tooltip = tooltip
        self._menu = entries
        self._on_activate = on_activate
        self._dock_visibility = dock_visibility
        self._installed = Observable(False)
        self._bridge: Any = None
        self._app_ref: Optional["weakref.ref[App]"] = None

    # ---- Model ------------------------------------------------------------

    @property
    def icon_path(self) -> Optional[Path]:
        """Path to the icon image, or ``None``."""
        return self._icon_path

    @property
    def tooltip(self) -> ObservableStr:
        """The hover text, as given (plain or Observable)."""
        return self._tooltip

    @property
    def menu(self) -> Tuple[MenuEntry, ...]:
        """The tray menu entries (empty when no menu was given)."""
        return self._menu

    @property
    def dock_visibility(self) -> str:
        """The macOS Dock policy: ``"always"``, ``"auto"``, or ``"never"``."""
        return self._dock_visibility

    @property
    def installed(self) -> ObservableBase[bool]:
        """Whether the icon is actually showing in the system tray.

        ``False`` until the backend installs it, and again after removal or
        when the platform cannot host one (no pystray, no tray area). Apps
        adapt through this — e.g. bind a window's ``close_action`` to it, or
        exit when a tray they depend on is unavailable.
        """
        return self._installed

    # ---- Framework-internal: install / removal ----------------------------

    def _install(self, app: "App") -> None:
        """Install the platform bridge. Called by the running backend."""
        if self._bridge is not None:
            return
        self._app_ref = weakref.ref(app)
        try:
            bridge = self._create_bridge()
            bridge.install()
        except Exception:
            exception_once(
                logger, "tray_install_exc", "Tray icon install failed; continuing without one"
            )
            return
        self._bridge = bridge
        self._installed.value = True
        count = getattr(app, "_visible_window_count", None)
        if callable(count):
            self._refresh_dock(count())

    def _create_bridge(self) -> Any:
        """Pick the platform bridge (separate so tests can substitute one)."""
        if sys.platform == "darwin":
            from .tray_cocoa import TrayCocoaBridge

            return TrayCocoaBridge(self)
        from .tray_pystray import TrayPystrayBridge

        return TrayPystrayBridge(self)

    def _uninstall(self) -> None:
        """Remove the icon. Called by the backend when the loop stops."""
        bridge, self._bridge = self._bridge, None
        if bridge is None:
            return
        self._installed.value = False
        try:
            bridge.uninstall()
        except Exception:
            exception_once(logger, "tray_uninstall_exc", "Tray icon uninstall raised")

    def _refresh_dock(self, visible_windows: int) -> None:
        """Apply the ``"auto"`` Dock policy for the current visible-window count.

        Called by the App whenever a window is shown, hidden, opened, or
        closed. A no-op unless the tray is installed with
        ``dock_visibility="auto"`` and the bridge controls a dock (macOS).
        """
        if self._bridge is None or self._dock_visibility != "auto":
            return
        set_dock_visible = getattr(self._bridge, "set_dock_visible", None)
        if not callable(set_dock_visible):
            return
        try:
            set_dock_visible(visible_windows > 0)
        except Exception:
            exception_once(logger, "tray_dock_refresh_exc", "Dock visibility refresh raised")

    # ---- Framework-internal: activation ------------------------------------

    def _activate_item(self, item: MenuEntry) -> None:
        """Run a tray menu item's command; the bridges call this on the UI thread.

        Mirrors ``MenuBarController.activate`` minus the window scope: toggle
        ``checked``, dispatch ``QUIT`` through the App, run ``on_select``.
        """
        if item.checked is not None:
            item.checked.value = not bool(item.checked.value)
        if item.role is MenuRole.QUIT:
            app = self._app_ref() if self._app_ref is not None else None
            if app is not None:
                from nuiitivet.runtime.intents import ExitAppIntent

                try:
                    app.dispatch(ExitAppIntent())
                except Exception:
                    exception_once(logger, "tray_dispatch_exit_exc", "ExitAppIntent dispatch raised")
            return
        if item.role is not MenuRole.NONE:
            warning_once(
                logger,
                "tray_window_scoped_role",
                "A window-scoped standard item has no target window in a tray menu; ignored.",
            )
            return
        if item.on_select is not None:
            invoke_event_handler(
                item.on_select,
                error_key="tray_on_select",
                error_msg="TrayIcon menu on_select raised",
                owner_name="TrayIcon",
            )

    def _fire_activate(self) -> None:
        """Run ``on_activate``; the bridges call this on the UI thread."""
        if self._on_activate is None:
            return
        invoke_event_handler(
            self._on_activate,
            error_key="tray_on_activate",
            error_msg="TrayIcon on_activate raised",
            owner_name="TrayIcon",
        )
