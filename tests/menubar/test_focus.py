"""Focus-follow for the macOS global menu bar (``menubar/focus.py``).

Owner selection and the install/reinstall choreography are pure Python, so
they run on every platform: the Cocoa bridge is substituted through the
coordinator's ``_bridge_factory`` seam, and windows are attached to the
coordinator directly (``install_platform_bridge`` would refuse off-macOS).
"""

from __future__ import annotations

from typing import Any, List, Optional

from nuiitivet.layout.container import Container
from nuiitivet.material.text import Text
from nuiitivet.menubar.controller import MenuBarController
from nuiitivet.menubar.focus import MenuBarFocusCoordinator
from nuiitivet.menubar.model import MenuBar
from nuiitivet.menus import MenuEntry
from nuiitivet.runtime.window import Window


def _model(title: str) -> MenuBar:
    return MenuBar([MenuEntry(title, submenu=[MenuEntry("Item", on_select=lambda: None)])])


class _FakeBridge:
    def __init__(self, controller: MenuBarController, app_name: str) -> None:
        self.controller = controller
        self.app_name = app_name
        self.installed: List[Optional[MenuBar]] = []
        self.uninstalled = False

    def install(self, model: Optional[MenuBar]) -> None:
        self.installed.append(model)

    def uninstall(self) -> None:
        self.uninstalled = True


class _Fixture:
    """The coordinator wired to a harness app, with the Cocoa layer faked."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.bridges: List[_FakeBridge] = []
        self.coordinator = MenuBarFocusCoordinator.attach(app.app)

        def factory(controller: MenuBarController, app_name: str) -> _FakeBridge:
            bridge = _FakeBridge(controller, app_name)
            self.bridges.append(bridge)
            return bridge

        self.coordinator._bridge_factory = factory
        self.attach(app.window)

    def attach(self, window: Window) -> None:
        """What ``install_platform_bridge`` does on macOS."""
        window._menubar_controller._coordinator = self.coordinator
        self.coordinator.window_created(window)

    def open_window(self, menu: Optional[MenuBar]) -> Window:
        window = Window(content=Container(), width=200, height=200, menu=menu).open()
        self.attach(window)
        return window

    def install_count(self) -> int:
        return sum(len(bridge.installed) for bridge in self.bridges)


def test_startup_installs_main_menu_synchronously(nuiitivet_app) -> None:
    model = _model("File")
    app = nuiitivet_app(Text("x"), size=(400, 300), menu=model)
    fx = _Fixture(app)

    # No clock pump: window_created applies at once, bound to the main
    # window's controller.
    assert [bridge.installed for bridge in fx.bridges] == [[model]]
    assert fx.bridges[0].controller is app.window._menubar_controller


def test_focus_swaps_to_secondary_menu_and_back(nuiitivet_app) -> None:
    main_model = _model("File")
    second_model = _model("Tools")
    app = nuiitivet_app(Text("x"), size=(400, 300), menu=main_model)
    fx = _Fixture(app)
    second = fx.open_window(second_model)

    app.window._set_os_active(False)
    second._set_os_active(True)
    app.settle()
    assert fx.bridges[-1].installed == [second_model]
    assert fx.bridges[-1].controller is second._menubar_controller
    # The outgoing bridge released its subscriptions.
    assert fx.bridges[0].uninstalled is True

    second._set_os_active(False)
    app.window._set_os_active(True)
    app.settle()
    assert fx.bridges[-1].installed == [main_model]
    assert fx.bridges[-1].controller is app.window._menubar_controller
    second.close()
    app.settle()


def test_menu_none_window_keeps_main_menu_without_reinstall(nuiitivet_app) -> None:
    app = nuiitivet_app(Text("x"), size=(400, 300), menu=_model("File"))
    fx = _Fixture(app)
    second = fx.open_window(None)
    before = fx.install_count()

    app.window._set_os_active(False)
    second._set_os_active(True)
    app.settle()
    # Effective model unchanged (main's stands in): nothing reinstalls.
    assert fx.install_count() == before
    second.close()
    app.settle()


def test_rapid_focus_flips_coalesce_on_one_tick(nuiitivet_app) -> None:
    app = nuiitivet_app(Text("x"), size=(400, 300), menu=_model("File"))
    fx = _Fixture(app)
    second = fx.open_window(_model("Tools"))
    before = fx.install_count()

    # Away and back before the tick: the settled state equals the installed
    # state, so the coalesced apply installs nothing.
    second._set_os_active(True)
    second._set_os_active(False)
    app.window._set_os_active(True)
    app.settle()
    assert fx.install_count() == before
    second.close()
    app.settle()


def test_closing_focused_window_restores_next_focus_menu(nuiitivet_app) -> None:
    main_model = _model("File")
    app = nuiitivet_app(Text("x"), size=(400, 300), menu=main_model)
    fx = _Fixture(app)
    second = fx.open_window(_model("Tools"))

    app.window._set_os_active(False)
    second._set_os_active(True)
    app.settle()

    second.close()
    app.settle()
    # Fallback to main while the OS decides, then main's activate confirms it.
    assert fx.bridges[-1].installed == [main_model]
    app.window._set_os_active(True)
    before = fx.install_count()
    app.settle()
    assert fx.install_count() == before


def test_model_replacement_reinstalls_through_same_bridge(nuiitivet_app) -> None:
    model = _model("File")
    app = nuiitivet_app(Text("x"), size=(400, 300), menu=model)
    fx = _Fixture(app)

    new_model = _model("View")
    app.window.menu = new_model
    app.settle()
    assert len(fx.bridges) == 1
    assert fx.bridges[0].installed == [model, new_model]


def test_model_replacement_on_unfocused_window_is_inert(nuiitivet_app) -> None:
    app = nuiitivet_app(Text("x"), size=(400, 300), menu=_model("File"))
    fx = _Fixture(app)
    second = fx.open_window(_model("Tools"))
    before = fx.install_count()

    second.menu = _model("Extras")
    app.settle()
    # Not the installed owner: the bar shows main's menu, untouched.
    assert fx.install_count() == before
    second.close()
    app.settle()


def test_last_menued_window_closing_falls_back_to_app_menu(nuiitivet_app) -> None:
    # Main window has no menu; the only menu lives on a secondary.
    app = nuiitivet_app(Text("x"), size=(400, 300))
    fx = _Fixture(app)
    second = fx.open_window(_model("Tools"))

    second._set_os_active(True)
    app.settle()
    assert fx.bridges[-1].installed == [second.menu]

    second.close()
    app.settle()
    # No model anywhere: the bare app menu (install(None)).
    assert fx.bridges[-1].installed[-1] is None


def test_menu_less_app_never_installs(nuiitivet_app) -> None:
    app = nuiitivet_app(Text("x"), size=(400, 300))
    fx = _Fixture(app)
    app.window._set_os_active(True)
    app.settle()
    assert fx.bridges == []


def test_attached_controller_reports_native_and_no_slot(nuiitivet_app) -> None:
    app = nuiitivet_app(Text("x"), size=(400, 300), menu=_model("File"))
    fx = _Fixture(app)
    second = fx.open_window(_model("Tools"))

    # Every attached window is native on macOS -- an unfocused window's menu
    # waits for focus rather than rendering in-app.
    for window in (app.window, second):
        controller = window._menubar_controller
        assert controller.native is True
        assert controller.active_slot() is None
    second.close()
    app.settle()
