"""Windows/Linux tray icon: ``TrayIcon`` model → pystray.

pystray is a regular dependency on these platforms (platform-marked in
``pyproject.toml``; macOS goes through ``tray_cocoa`` instead and never
installs it). It runs the tray on its own thread (``run_detached()``),
which coexists with the pyglet loop; its
callbacks therefore arrive **off** the UI thread, so every activation is
hopped onto the UI thread through the runtime clock before it touches the
model — after the hop, checkable toggling, roles, and ``on_select`` behave
exactly as on macOS.

Best-effort by design, especially on Linux: whether an icon actually shows
depends on the desktop (SNI/AppIndicator host, GNOME extension, Wayland).
An install failure raises here and the ``TrayIcon`` model turns it into a
logged no-op with ``installed`` staying ``False``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from nuiitivet.common.logging_once import warning_once
from nuiitivet.menus import MenuEntry, read_value
from nuiitivet.observable import ObservableBase, runtime

if TYPE_CHECKING:
    from .tray import TrayIcon

logger = logging.getLogger(__name__)


class TrayPystrayBridge:
    """Installs a :class:`TrayIcon` through pystray. Framework-internal."""

    def __init__(self, tray: "TrayIcon") -> None:
        self._tray = tray
        self._icon: Any = None
        self._subscriptions: List[Any] = []

    def install(self) -> None:
        """Start the detached pystray icon; raises when pystray is unusable."""
        import pystray

        tray = self._tray
        if tray.menu and not getattr(pystray.Icon, "HAS_MENU", True):
            # An icon whose menu cannot open would still read as installed,
            # steering the resident-app recipe (close_action bound to
            # ``installed``) toward locking the user out. Fail instead:
            # ``installed`` stays False and the app adapts.
            raise RuntimeError(
                "This tray backend (pystray xorg) cannot show a menu; "
                "refusing to install a menu-carrying tray icon."
            )
        icon = pystray.Icon(
            "nuiitivet",
            self._load_image(),
            title=str(read_value(tray.tooltip) or ""),
            menu=self._build_menu(pystray),
        )
        self._icon = icon
        self._sync_menu(icon)

        tooltip = tray.tooltip
        if isinstance(tooltip, ObservableBase):

            def on_change(_value: Any) -> None:
                try:
                    icon.title = str(read_value(tray.tooltip) or "")
                except Exception:
                    logger.debug("Tray tooltip sync failed", exc_info=True)

            self._subscriptions.append(tooltip.subscribe(on_change))

        icon.run_detached()

    def uninstall(self) -> None:
        subscriptions, self._subscriptions = self._subscriptions, []
        for subscription in subscriptions:
            dispose = getattr(subscription, "dispose", None)
            if callable(dispose):
                dispose()
        icon, self._icon = self._icon, None
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                logger.debug("pystray icon stop raised", exc_info=True)

    # ---- Pieces ------------------------------------------------------------

    def _load_image(self) -> Any:
        from PIL import Image

        path = self._tray.icon_path
        if path is not None:
            try:
                return Image.open(str(path))
            except Exception:
                logger.warning("Tray icon image failed to load: %s", path)
        # pystray requires an image; a neutral square beats no tray at all.
        return Image.new("RGBA", (16, 16), (128, 128, 128, 255))

    def _marshal(self, fn: Callable[[], None]) -> Callable[[Any, Any], None]:
        """Wrap ``fn`` so a pystray-thread callback runs on the UI thread."""

        def handler(_icon: Any, _item: Any) -> None:
            runtime.clock.schedule_once(lambda _dt: fn(), 0.0)

        return handler

    def _build_menu(self, pystray: Any) -> Optional[Any]:
        tray = self._tray
        items = [self._to_pystray(pystray, entry) for entry in tray.menu]
        if tray._on_activate is not None:
            if getattr(pystray.Icon, "HAS_DEFAULT", True):
                # The invisible default item is pystray's idiom for the icon's
                # activate gesture (double-click on Windows).
                items.insert(
                    0,
                    pystray.MenuItem(
                        "Activate", self._marshal(tray._fire_activate), default=True, visible=False
                    ),
                )
            else:
                warning_once(
                    logger,
                    "tray_no_default_action",
                    "This tray backend cannot deliver on_activate (no default "
                    "action); provide an equivalent menu entry.",
                )
        if not items:
            return None
        return pystray.Menu(*items)

    def _sync_menu(self, icon: Any) -> None:
        """Refresh the native menu when a menu Observable changes.

        pystray re-evaluates the item callables when it (re)builds the menu,
        but not every backend rebuilds on display — an external change
        requires ``Icon.update_menu()`` (per the pystray docs), so every
        Observable ``label`` / ``enabled`` / ``checked`` in the tree triggers
        one.
        """

        def on_change(_value: Any) -> None:
            try:
                icon.update_menu()
            except Exception:
                logger.debug("pystray update_menu failed", exc_info=True)

        def walk(entries: Any) -> None:
            for entry in entries:
                for prop in (entry.label, entry.enabled, entry.checked):
                    if isinstance(prop, ObservableBase):
                        self._subscriptions.append(prop.subscribe(on_change))
                if entry.submenu is not None:
                    walk(entry.submenu)

        walk(self._tray.menu)

    def _to_pystray(self, pystray: Any, entry: MenuEntry) -> Any:
        if entry.is_separator:
            return pystray.Menu.SEPARATOR

        def text(_item: Any, entry: MenuEntry = entry) -> str:
            return str(entry.resolved_label())

        def enabled(_item: Any, entry: MenuEntry = entry) -> bool:
            return bool(entry.resolved_enabled())

        if entry.submenu is not None:
            children = [self._to_pystray(pystray, child) for child in entry.submenu]
            return pystray.MenuItem(text, pystray.Menu(*children), enabled=enabled)

        checked: Optional[Callable[[Any], bool]] = None
        if entry.checked is not None:

            def is_checked(_item: Any, entry: MenuEntry = entry) -> bool:
                assert entry.checked is not None
                return bool(entry.checked.value)

            checked = is_checked

        tray = self._tray

        def run(entry: MenuEntry = entry) -> None:
            tray._activate_item(entry)

        return pystray.MenuItem(text, self._marshal(run), checked=checked, enabled=enabled)
