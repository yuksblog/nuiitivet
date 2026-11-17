"""``X.proxy(widget)``: a lookup made in ``__init__`` and resolved at each use.

``Geometry.proxy`` is covered in ``tests/layout/test_geometry.py``.
"""

from __future__ import annotations

import gc
import logging
import weakref
from typing import Any, Callable

import pytest

import nuiitivet as core
import nuiitivet.material as nv
from nuiitivet.layout.container import Container
from nuiitivet.layout.geometry import Geometry
from nuiitivet.navigation.navigator import Navigator
from nuiitivet.overlay.overlay import Overlay
from nuiitivet.overlay.result import OverlayDismissReason
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.testing import AppHarness, mount
from nuiitivet.transition.spec import Transitions
from nuiitivet.widgeting.widget import ComposableWidget, Widget

SIZE = (400, 300)
INSTANT = Transitions.empty()
LOOKUP_LOGGER = "nuiitivet.widgeting.context_lookup"


# --- Static conformance: mypy checks the bodies ---------------------------


def _core_overlay_proxy(widget: Widget) -> core.OverlayProtocol:
    return Overlay.proxy(widget)


def _material_overlay_proxy(widget: Widget) -> nv.OverlayProtocol:
    return nv.Overlay.proxy(widget, root=True)


def _navigator_proxy(widget: Widget) -> nv.NavigatorProtocol:
    return nv.Navigator.proxy(widget, root=True)


def _window_proxy(widget: Widget) -> nv.WindowProtocol:
    return nv.Window.proxy(widget)


def _app_proxy(widget: Widget) -> nv.AppProtocol:
    return nv.App.proxy(widget)


# --- A ViewModel built in __init__ ----------------------------------------


class ItemViewModel:
    def __init__(self, navigator: nv.NavigatorProtocol, overlay: nv.OverlayProtocol) -> None:
        self._navigator = navigator
        self._overlay = overlay

    def open(self) -> None:
        self._navigator.push(DetailScreen(), transition=INSTANT)

    def back(self) -> None:
        self._navigator.pop()

    def can_go_back(self) -> bool:
        return self._navigator.can_pop()

    def confirm(self) -> Any:
        return self._overlay.dialog(nv.BasicDialogIntent(title="Delete?"))

    def notify(self) -> Any:
        return self._overlay.snackbar("Saved")

    def work(self) -> list[str]:
        ran: list[str] = []
        with self._overlay.while_loading():
            ran.append("body")
        return ran


class ItemScreen(ComposableWidget):
    def __init__(self) -> None:
        super().__init__()
        self.vm = ItemViewModel(nv.Navigator.proxy(self), nv.Overlay.proxy(self))

    def build(self) -> Widget:
        return Container(width="wt", height="wt")


class DetailScreen(ComposableWidget):
    def build(self) -> Widget:
        return Container(width="wt", height="wt")


class HomeScreen(ComposableWidget):
    def build(self) -> Widget:
        return Container(width="wt", height="wt")


def test_view_model_built_in_init_pushes_and_shows_a_dialog() -> None:
    screen = ItemScreen()
    with AppHarness(screen, size=SIZE) as app:
        handle = screen.vm.confirm()
        app.settle()
        assert len(app.open_overlays) == 1
        assert not handle.done()
        handle.close(True)

        screen.vm.open()
        app.settle()
        assert isinstance(app.current_screen, DetailScreen)
        assert screen.vm.can_go_back() is True


def test_proxy_takes_root_like_of() -> None:
    inner = ItemScreen()
    nested = nv.Navigator(HomeScreen())
    with AppHarness(Container(nested, width="wt", height="wt"), size=SIZE) as app:
        nested.push(inner, transition=INSTANT)

        nv.Navigator.proxy(inner, root=True).push(DetailScreen(), transition=INSTANT)
        assert (len(app.route_stack), len(nested.stack)) == (2, 2)

        nv.Navigator.proxy(inner).push(DetailScreen(), transition=INSTANT)
        assert (len(app.route_stack), len(nested.stack)) == (2, 3)


# --- Before mount ----------------------------------------------------------


def _service_calls() -> list[tuple[str, Callable[[Widget], Any]]]:
    return [
        ("Overlay", lambda w: nv.Overlay.proxy(w).snackbar("x")),
        ("CoreOverlay", lambda w: Overlay.proxy(w).close()),
        ("Navigator", lambda w: nv.Navigator.proxy(w).pop()),
        ("Window", lambda w: nv.Window.proxy(w).hide()),
        ("WindowValue", lambda w: nv.Window.proxy(w).is_open),
        ("App", lambda w: nv.App.proxy(w).exit()),
        ("AppValue", lambda w: nv.App.proxy(w).badge),
    ]


@pytest.mark.parametrize("name,call", _service_calls(), ids=[n for n, _ in _service_calls()])
def test_service_call_before_mount_raises_premature(name: str, call: Callable[[Widget], Any]) -> None:
    with pytest.raises(RuntimeError, match="was used before Widget was mounted"):
        call(Widget())


def _proxies() -> list[tuple[str, Callable[[Widget], Any]]]:
    return [
        ("Geometry", Geometry.proxy),
        ("Overlay", Overlay.proxy),
        ("MaterialOverlay", nv.Overlay.proxy),
        ("Navigator", Navigator.proxy),
        ("Window", Window.proxy),
        ("App", App.proxy),
    ]


@pytest.mark.parametrize("name,make", _proxies(), ids=[n for n, _ in _proxies()])
def test_proxy_before_super_init_raises(name: str, make: Callable[[Widget], Any]) -> None:
    class _Early(Widget):
        def __init__(self) -> None:
            make(self)
            super().__init__()

    with pytest.raises(RuntimeError, match=rf"{name}\.proxy\(\) was called on _Early before super\(\).__init__\(\)"):
        _Early()


@pytest.mark.parametrize("name,call", _service_calls(), ids=[n for n, _ in _service_calls()])
def test_service_call_in_a_tree_with_no_provider_raises_not_found(name: str, call: Callable[[Widget], Any]) -> None:
    root = Widget()
    root.mount(None)

    with pytest.raises(RuntimeError) as excinfo:
        call(root)

    assert "before" not in str(excinfo.value)
    root.unmount()


# --- After unmount: Overlay and Navigator drop the call ---------------------


async def _pushed_and_popped(app: AppHarness, screen: Widget) -> None:
    app.window.navigator.push(screen, transition=INSTANT)
    app.settle()
    app.window.navigator.pop()
    await app.wait_for(lambda: len(app.route_stack) == 1)


async def test_overlay_and_navigator_calls_after_unmount_are_dropped(caplog: pytest.LogCaptureFixture) -> None:
    screen = ItemScreen()
    with AppHarness(HomeScreen(), size=SIZE) as app:
        await _pushed_and_popped(app, screen)

        with caplog.at_level(logging.DEBUG, logger=LOOKUP_LOGGER):
            dialog = screen.vm.confirm()
            snackbar = screen.vm.notify()
            screen.vm.open()
            screen.vm.back()
            app.settle()

            assert dialog.done() and snackbar.done()
            assert (await dialog).reason is OverlayDismissReason.DISPOSED
            assert (await dialog).value is None
            dialog.close(True)
            assert screen.vm.can_go_back() is False
            assert screen.vm.work() == ["body"]
            assert app.open_overlays == ()
            assert len(app.route_stack) == 1

    dropped = [r for r in caplog.records if "call dropped" in r.getMessage()]
    # Once per proxy: one line for the navigator's, one for the overlay's.
    assert sorted(r.getMessage() for r in dropped) == [
        "MaterialNavigator.proxy: call dropped, ItemScreen is no longer mounted",
        "MaterialOverlay.proxy: call dropped, ItemScreen is no longer mounted",
    ]
    assert all(r.levelno == logging.DEBUG for r in dropped)


async def test_proxy_resolves_again_once_its_widget_is_mounted_again() -> None:
    screen = ItemScreen()
    with AppHarness(HomeScreen(), size=SIZE) as app:
        await _pushed_and_popped(app, screen)
        assert screen.vm.notify().done()

        app.window.navigator.push(screen, transition=INSTANT)
        app.settle()
        handle = screen.vm.confirm()
        app.settle()

        assert not handle.done()
        assert len(app.open_overlays) == 1
        handle.close(None)


# --- After unmount: Window and App still answer -----------------------------


async def test_window_and_app_calls_after_unmount_reach_where_the_widget_was_mounted() -> None:
    screen = DetailScreen()
    window = nv.Window.proxy(screen)
    app_proxy = nv.App.proxy(screen)
    with AppHarness(HomeScreen(), size=SIZE) as app:
        await _pushed_and_popped(app, screen)

        assert window.is_open is app.window.is_open
        assert window.is_visible is app.window.is_visible
        window.hide()
        assert app.window.is_visible.value is False

        app_proxy.badge.value = 3
        assert app.app.badge.value == 3


def test_app_call_after_unmount_reaches_the_host() -> None:
    probe = Container()
    proxy = App.proxy(probe)
    with mount(probe) as host:
        pass

    proxy.exit(2)

    assert host.exit_requests == [2]


def test_window_and_app_proxies_of_a_widget_never_mounted_drop_the_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    probe: Widget | None = Container()
    assert probe is not None
    window, app = Window.proxy(probe), App.proxy(probe)
    probe = None
    gc.collect()

    with caplog.at_level(logging.DEBUG, logger=LOOKUP_LOGGER):
        window.close()
        app.exit()
        app.badge.value = 3

    assert window.is_open.value is False
    assert window.is_visible.value is False
    assert app.badge.value is None
    assert [r.getMessage() for r in caplog.records] == [
        "Window.proxy: call dropped, Container is no longer mounted",
        "App.proxy: call dropped, Container is no longer mounted",
    ]


async def test_closed_of_a_dropped_window_proxy_is_already_resolved() -> None:
    probe: Widget | None = Container()
    assert probe is not None
    window = Window.proxy(probe)
    probe = None
    gc.collect()

    await window.closed


# --- Weak hold ---------------------------------------------------------------


@pytest.mark.parametrize("name,make", _proxies(), ids=[n for n, _ in _proxies()])
def test_proxy_does_not_keep_its_widget_alive(name: str, make: Callable[[Widget], Any]) -> None:
    gc.collect()
    gc.disable()
    try:
        probe = Container()
        proxy = make(probe)
        ref = weakref.ref(probe)

        del probe
        assert ref() is None, f"{name}.proxy holds its widget"
        del proxy
    finally:
        gc.enable()
