"""macOS focus-follow for the global menu bar: focused window → installed menu.

The global menu bar is one per process, so with several windows someone must
decide whose model it shows. The bar follows the OS focus: the focused
window's model is installed, and a
window with ``menu=None`` falls back to the main window's model, so
single-menu apps keep their behavior with no per-window declarations.

The :class:`MenuBarFocusCoordinator` is the per-App owner of the one
:class:`~nuiitivet.menubar.nsmenu.NSMenuBridge`. Windows attach as their
backend window comes up (``MenuBarController.install_platform_bridge``);
focus changes, model replacements, and window closes funnel into an apply
coalesced onto the next clock tick — rapid focus flips cost one reinstall,
and a focus change that does not change the effective model (a ``menu=None``
window gaining focus) reinstalls nothing. The very first install runs
synchronously so the native bar takes over before a frame is drawn.

Owner selection (:meth:`MenuBarFocusCoordinator._resolve_owner`) is pure
Python and tested on every platform; only the bridge itself is Cocoa, and
tests substitute it through ``_bridge_factory``.
"""

from __future__ import annotations

import logging
import weakref
from typing import TYPE_CHECKING, Any, Callable, Optional

from nuiitivet.common.logging_once import exception_once
from nuiitivet.observable import runtime

from .model import MenuBar

if TYPE_CHECKING:
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import Window

    from .controller import MenuBarController

logger = logging.getLogger(__name__)


def _default_bridge_factory(controller: "MenuBarController", app_name: str) -> Any:
    from .nsmenu import NSMenuBridge

    return NSMenuBridge(controller, app_name=app_name)


class MenuBarFocusCoordinator:
    """Keeps the macOS global menu bar on the focused window's menu.

    One per App, created lazily by the first window whose backend window
    comes up on a platform where the ``NSMenu`` bridge is supported
    (:meth:`attach`); framework-internal. Never constructed on other
    platforms — their in-app bars are fully per-window already.
    """

    def __init__(self, app: "App") -> None:
        self._app = weakref.ref(app)
        #: The last window to gain OS focus. Kept across deactivates: while no
        #: window of ours is focused the bar keeps its current menu (macOS is
        #: showing another app's bar anyway), which also rides out the
        #: deactivate→activate gap of an ordinary window switch.
        self._focused: "weakref.ref[Window] | None" = None
        self._installed_owner: "weakref.ref[Window] | None" = None
        self._installed_model: Optional[MenuBar] = None
        self._bridge: Optional[Any] = None
        self._scheduled = False
        #: Test seam: ``(controller, app_name) -> bridge``. The default builds
        #: the real Cocoa bridge; platform-neutral tests substitute a fake.
        self._bridge_factory: Callable[["MenuBarController", str], Any] = _default_bridge_factory

    @classmethod
    def attach(cls, app: "App") -> "MenuBarFocusCoordinator":
        """Get the App's coordinator, creating it on first use."""
        coordinator = app._menubar_focus_coordinator
        if coordinator is None:
            coordinator = cls(app)
            app._menubar_focus_coordinator = coordinator
        return coordinator

    # ---- Notifications ---------------------------------------------------

    def window_created(self, window: "Window") -> None:
        """A window's backend window exists; apply synchronously.

        Synchronous so the main window's menu is on the global bar before the
        first frame, exactly as the pre-coordinator install was.
        """
        self._apply()

    def focus_changed(self, window: "Window", active: bool) -> None:
        """OS focus entered or left ``window`` (backend hook)."""
        if not active:
            # Deactivate alone changes nothing: ``_focused`` is kept, so the
            # apply would be a no-op. The paired activate reschedules.
            return
        self._focused = weakref.ref(window)
        self._schedule()

    def model_changed(self, window: "Window") -> None:
        """``window.menu`` was replaced wholesale."""
        self._schedule()

    def window_closed(self, window: "Window") -> None:
        """``window`` closed; drop it as the focus holder and re-resolve.

        The OS focuses another window right after, and that activate applies
        the final state; until it lands the main window's menu stands in.
        """
        if self._focused is not None and self._focused() is window:
            self._focused = None
        self._schedule()

    # ---- Apply -----------------------------------------------------------

    def _schedule(self) -> None:
        """Coalesce onto the next clock tick (one reinstall per burst)."""
        if self._scheduled:
            return
        self._scheduled = True

        def fire(_dt: float = 0.0) -> None:
            self._apply()

        runtime.clock.schedule_once(fire, 0.0)

    def _resolve_owner(self, app: "App") -> "Window | None":
        """The window whose model belongs on the global bar, or ``None``.

        The focused window when it declares a menu; the main window's menu
        stands in for ``menu=None`` windows (and while nothing is focused).
        Closed windows never own the bar — ``app.windows`` is the open set.
        """
        windows = app.windows
        focused = self._focused() if self._focused is not None else None
        if focused is not None and focused in windows and focused.menu is not None:
            return focused
        main = app._main_window
        if main is not None and main in windows and main.menu is not None:
            return main
        return None

    def _app_name(self, app: "App") -> str:
        """The application-menu title: the main window's title, stable across
        installs so the app menu never renames on focus changes."""
        main = app._main_window
        title = getattr(main, "_title_value", None) if main is not None else None
        value = getattr(title, "value", title)
        return str(value) if value else "App"

    def _apply(self) -> None:
        self._scheduled = False
        app = self._app()
        if app is None:
            return
        owner = self._resolve_owner(app)
        model = owner.menu if owner is not None else None
        installed_owner = self._installed_owner() if self._installed_owner is not None else None
        if self._bridge is not None and owner is installed_owner and model is self._installed_model:
            return

        if owner is None:
            if self._bridge is None:
                # Nothing was ever installed (no window declared a menu);
                # leave the default menu bar alone, as before.
                return
            # Every window with a menu is gone while the app lives on: fall
            # back to the bare app menu. The bridge stays bound to the last
            # owner's controller — its window object outlives close(), and the
            # synthesized quit() still dispatches through its App.
            try:
                self._bridge.install(None)
            except Exception:
                exception_once(logger, "menubar_focus_fallback_exc", "NSMenu bridge fallback install raised")
                return
            self._installed_owner = None
            self._installed_model = None
            return

        controller = owner._menubar_controller
        if owner is not installed_owner or self._bridge is None:
            # New bridge first, old subscriptions after: the swap is a single
            # setMainMenu_ with no intermediate state, so no flicker.
            old = self._bridge
            try:
                bridge = self._bridge_factory(controller, self._app_name(app))
                bridge.install(model)
            except Exception:
                exception_once(logger, "menubar_focus_install_exc", "NSMenu bridge install raised")
                return
            if old is not None:
                try:
                    old.uninstall()
                except Exception:
                    exception_once(logger, "menubar_focus_uninstall_exc", "NSMenu bridge uninstall raised")
            self._bridge = bridge
        else:
            # Same owner, replaced model: reinstall through the same bridge.
            try:
                self._bridge.install(model)
            except Exception:
                exception_once(logger, "menubar_focus_reinstall_exc", "NSMenu bridge reinstall raised")
                return
        self._installed_owner = weakref.ref(owner)
        self._installed_model = model
