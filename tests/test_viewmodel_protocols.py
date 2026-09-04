"""The ViewModel-facing Navigator / Overlay / App / Window protocols.

Two invariants:

1. The shipped concrete classes satisfy the protocols with no changes. The
   ``_conforms_*`` functions below are annotated, so mypy checks their bodies
   and fails the build if a signature ever drifts.
2. A ViewModel typed against the protocols can be constructed and exercised
   with hand-written fakes -- no widget tree, no ``App``.
"""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Literal

import pytest

import nuiitivet as core
import nuiitivet.material as nv
from nuiitivet.material.overlay import MaterialOverlay, WhileLoading
from nuiitivet.navigation.navigator import Navigator as CoreNavigator
from nuiitivet.overlay.overlay import Overlay as CoreOverlay
from nuiitivet.overlay.overlay_handle import OverlayHandle
from nuiitivet.overlay.result import OverlayDismissReason, OverlayResult
from nuiitivet.navigation.route import Route
from nuiitivet.observable.protocols import ObservableBase
from nuiitivet.runtime.app import App as CoreApp
from nuiitivet.runtime.window import Window as CoreWindow
from nuiitivet.widgeting.widget import Widget


# --- 1. Static conformance --------------------------------------------------
# Return-type mismatches here are mypy errors, not runtime ones.


def _conforms_core_navigator(navigator: CoreNavigator) -> core.NavigatorProtocol:
    return navigator


def _conforms_material_navigator(navigator: nv.Navigator) -> nv.NavigatorProtocol:
    return navigator


def _conforms_core_overlay(overlay: CoreOverlay) -> core.OverlayProtocol:
    return overlay


def _conforms_material_overlay(overlay: nv.Overlay) -> nv.OverlayProtocol:
    return overlay


def _material_protocol_widens_to_core(overlay: nv.OverlayProtocol) -> core.OverlayProtocol:
    return overlay


def _conforms_core_app(app: CoreApp) -> core.AppProtocol:
    return app


def _conforms_material_app(app: nv.App) -> nv.AppProtocol:
    return app


def _conforms_core_window(window: CoreWindow) -> core.WindowProtocol:
    return window


def _conforms_material_window(window: nv.Window) -> nv.WindowProtocol:
    return window


def test_material_root_aliases_the_material_protocol() -> None:
    """``nv.OverlayProtocol`` names the Material protocol, as ``nv.Overlay`` names MaterialOverlay."""
    from nuiitivet.material.protocols import MaterialOverlayProtocol
    from nuiitivet.overlay.protocols import OverlayProtocol as CoreOverlayProtocol

    assert nv.OverlayProtocol is MaterialOverlayProtocol
    assert core.OverlayProtocol is CoreOverlayProtocol
    assert nv.OverlayProtocol is not core.OverlayProtocol
    # Navigator needs no Material-specific half: one protocol serves both layers.
    assert nv.NavigatorProtocol is core.NavigatorProtocol
    # Neither do App and Window.
    assert nv.AppProtocol is core.AppProtocol
    assert nv.WindowProtocol is core.WindowProtocol


def test_concrete_classes_expose_every_protocol_member() -> None:
    """Structural conformance, asserted at runtime as a backstop to mypy."""
    for name in ("push", "pop", "can_pop"):
        assert callable(getattr(CoreNavigator, name))
    assert callable(getattr(CoreOverlay, "close"))
    for name in ("dialog", "snackbar", "loading", "while_loading", "side_sheet", "bottom_sheet"):
        assert callable(getattr(MaterialOverlay, name))
    for name in ("exit", "set_theme", "register_themes"):
        assert callable(getattr(CoreApp, name))
    for name in (
        "close",
        "hide",
        "show",
        "minimize",
        "maximize",
        "restore",
        "full_screen",
        "center",
        "move_to",
        "resize",
    ):
        assert callable(getattr(CoreWindow, name))
    for name in ("is_open", "is_visible", "closed"):
        assert isinstance(getattr(CoreWindow, name), property)


# --- 2. A ViewModel against hand-written fakes ------------------------------


class DetailsIntent:
    """A navigation intent -- plain data, resolved to a Route by the View layer."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id


class ConfirmDeleteIntent:
    """A dialog intent."""


class FakeNavigator:
    """Implements ``NavigatorProtocol`` with a recorded stack."""

    def __init__(self) -> None:
        self.pushed: list[Any] = []
        self.pop_count = 0

    def push(self, route_or_widget_or_intent: Route | Widget | Any) -> None:
        self.pushed.append(route_or_widget_or_intent)

    def pop(self) -> None:
        self.pop_count += 1
        if self.pushed:
            self.pushed.pop()

    def can_pop(self) -> bool:
        return bool(self.pushed)


class _FakeHandleHost:
    """Minimal ``OverlayHandle`` host so fakes can hand back awaitable handles."""

    def __init__(self) -> None:
        self._futures: dict[int, asyncio.Future[OverlayResult[Any]]] = {}

    def _close_entry(self, entry: Any, value: Any = None) -> None:
        future = self._get_future_for_entry(entry)
        if future is not None and not future.done():
            future.set_result(OverlayResult(value=value, reason=OverlayDismissReason.CLOSED))

    def _future_for_entry(self, entry: Any) -> asyncio.Future[OverlayResult[Any]]:
        future = self._futures.get(id(entry))
        if future is None:
            future = asyncio.get_event_loop().create_future()
            self._futures[id(entry)] = future
        return future

    def _get_future_for_entry(self, entry: Any) -> asyncio.Future[OverlayResult[Any]] | None:
        return self._futures.get(id(entry))

    def _get_pending_result_for_entry(self, entry: Any) -> OverlayResult[Any] | None:
        return None

    def _pop_pending_result_for_entry(self, entry: Any) -> OverlayResult[Any] | None:
        return None

    def _request_dismiss_entry(self, entry: Any, *, value: Any = None, reason: Any) -> None:
        self._close_entry(entry, value)


class FakeOverlay:
    """Implements ``nv.OverlayProtocol`` by recording what was presented."""

    def __init__(self) -> None:
        self.dialogs: list[Any] = []
        self.snackbars: list[str] = []
        self.sheets: list[Any] = []
        self.loading_depth = 0
        self.closed: list[Any] = []
        self._host = _FakeHandleHost()

    def _handle(self, entry: Any) -> OverlayHandle[Any]:
        return OverlayHandle(overlay=self._host, entry=entry)

    def dialog(self, dialog: Widget | Any, *, dismiss_on_outside_tap: bool = True) -> OverlayHandle[Any]:
        self.dialogs.append(dialog)
        return self._handle(dialog)

    def snackbar(self, message: str | nv.Snackbar, *, duration: float = 3.0) -> OverlayHandle[None]:
        self.snackbars.append(str(message))
        return OverlayHandle(overlay=self._host, entry=message)

    def loading(self, indicator: Widget | Any | None = None) -> OverlayHandle[Any]:
        self.loading_depth += 1
        return self._handle(indicator)

    def while_loading(self, indicator: Widget | Any | None = None) -> WhileLoading:
        return WhileLoading(self, indicator)

    def side_sheet(
        self,
        sheet: Widget,
        *,
        side: Literal["right", "left"] = "right",
        dismiss_on_outside_tap: bool = True,
    ) -> OverlayHandle[Any]:
        self.sheets.append(sheet)
        return self._handle(sheet)

    def bottom_sheet(self, sheet: Widget, *, dismiss_on_outside_tap: bool = True) -> OverlayHandle[Any]:
        self.sheets.append(sheet)
        return self._handle(sheet)

    def close(self, value: Any = None, target: Widget | Route | None = None) -> None:
        self.closed.append(value)


def _conforms_fake_navigator(navigator: FakeNavigator) -> nv.NavigatorProtocol:
    return navigator


def _conforms_fake_overlay(overlay: FakeOverlay) -> nv.OverlayProtocol:
    return overlay


class ItemViewModel:
    """A ViewModel that knows the protocols and nothing about widgets."""

    def __init__(self, navigator: nv.NavigatorProtocol, overlay: nv.OverlayProtocol) -> None:
        self._navigator = navigator
        self._overlay = overlay

    def open(self, item_id: int) -> None:
        self._navigator.push(DetailsIntent(item_id=item_id))

    def back(self) -> None:
        if self._navigator.can_pop():
            self._navigator.pop()

    async def delete(self, item_id: int) -> bool:
        result = await self._overlay.dialog(ConfirmDeleteIntent())
        if not result.value:
            return False
        self._overlay.snackbar(f"Deleted {item_id}")
        return True

    def sync_work(self) -> None:
        with self._overlay.while_loading():
            pass


class PerCallViewModel:
    """The shape the guide recommends: the navigator arrives per call.

    A widget cannot resolve a navigator in ``__init__`` (neither ``of()`` nor
    ``root()`` works that early), so the View resolves one inside the event
    handler. The protocol types the parameter just as well as a constructor
    argument, and the ViewModel stays constructible anywhere.
    """

    def open(self, navigator: nv.NavigatorProtocol, item_id: int) -> None:
        navigator.push(DetailsIntent(item_id=item_id))


def test_per_call_injection_is_typed_by_the_same_protocol() -> None:
    navigator = FakeNavigator()

    PerCallViewModel().open(navigator, item_id=7)

    assert isinstance(navigator.pushed[0], DetailsIntent)


def test_view_model_navigates_without_a_widget_tree() -> None:
    navigator = FakeNavigator()
    vm = ItemViewModel(navigator, FakeOverlay())

    vm.open(7)

    assert len(navigator.pushed) == 1
    intent = navigator.pushed[0]
    assert isinstance(intent, DetailsIntent)
    assert intent.item_id == 7

    vm.back()
    assert navigator.pop_count == 1
    assert navigator.can_pop() is False

    vm.back()  # nothing left to pop
    assert navigator.pop_count == 1


def test_view_model_while_loading_uses_the_fake_overlay() -> None:
    overlay = FakeOverlay()
    vm = ItemViewModel(FakeNavigator(), overlay)

    vm.sync_work()

    assert overlay.loading_depth == 1


@pytest.mark.asyncio
async def test_view_model_awaits_a_dialog_result() -> None:
    overlay = FakeOverlay()
    vm = ItemViewModel(FakeNavigator(), overlay)

    task = asyncio.ensure_future(vm.delete(7))
    # Not a harness wait: there is no widget tree here, only a ViewModel and a
    # fake overlay, so there is nothing for idle() to settle. One turn is enough
    # to reach `await overlay.dialog(...)`, and the fake resolves in-process.
    await asyncio.sleep(0)

    assert len(overlay.dialogs) == 1
    assert isinstance(overlay.dialogs[0], ConfirmDeleteIntent)

    overlay._host._close_entry(overlay.dialogs[0], True)
    assert await task is True
    assert overlay.snackbars == ["Deleted 7"]


@pytest.mark.asyncio
async def test_view_model_honours_a_declined_dialog() -> None:
    overlay = FakeOverlay()
    vm = ItemViewModel(FakeNavigator(), overlay)

    task = asyncio.ensure_future(vm.delete(7))
    await asyncio.sleep(0)  # see above: no tree to settle, one turn to the await
    overlay._host._close_entry(overlay.dialogs[0], False)

    assert await task is False
    assert overlay.snackbars == []


# --- 3. App / Window fakes ---------------------------------------------------


class FakeApp:
    """Implements ``AppProtocol`` by recording what was requested."""

    def __init__(self) -> None:
        self.exit_codes: list[int] = []
        self.themes: list[Any] = []
        self.registry: dict[str, Any] = {}

    def exit(self, exit_code: int = 0) -> None:
        self.exit_codes.append(exit_code)

    def set_theme(self, theme: str | core.Theme) -> None:
        self.themes.append(theme)

    def register_themes(self, themes: dict[str, core.Theme]) -> None:
        self.registry.update(themes)


class FakeWindow:
    """Implements ``WindowProtocol`` with recorded calls and live observables."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._is_open: core.Observable[bool] = core.Observable(True)
        self._is_visible: core.Observable[bool] = core.Observable(True)
        self._closed_event = asyncio.Event()

    def close(self) -> None:
        self.calls.append("close")
        self._is_open.value = False
        self._is_visible.value = False
        self._closed_event.set()

    def hide(self) -> None:
        self.calls.append("hide")
        self._is_visible.value = False

    def show(self) -> None:
        self.calls.append("show")
        self._is_visible.value = True

    def minimize(self) -> None:
        self.calls.append("minimize")

    def maximize(self) -> None:
        self.calls.append("maximize")

    def restore(self) -> None:
        self.calls.append("restore")

    def full_screen(self) -> None:
        self.calls.append("full_screen")

    def center(self) -> None:
        self.calls.append("center")

    def move_to(self, x: int, y: int) -> None:
        self.calls.append(f"move_to({x},{y})")

    def resize(self, width: int, height: int) -> None:
        self.calls.append(f"resize({width},{height})")

    @property
    def is_open(self) -> ObservableBase[bool]:
        return self._is_open

    @property
    def is_visible(self) -> ObservableBase[bool]:
        return self._is_visible

    @property
    def closed(self) -> Awaitable[None]:
        return self._wait_closed()

    async def _wait_closed(self) -> None:
        await self._closed_event.wait()


def _conforms_fake_app(app: FakeApp) -> nv.AppProtocol:
    return app


def _conforms_fake_window(window: FakeWindow) -> nv.WindowProtocol:
    return window


class ShellViewModel:
    """Commands window and app through the protocols, received per call.

    Per-call injection is the standard shape: the widget builds its ViewModel
    in ``__init__``, where ``.of(context)`` cannot resolve yet, so the event
    handler resolves the object and hands it to the method.
    """

    def send_to_background(self, window: nv.WindowProtocol) -> None:
        window.hide()

    def quit(self, app: nv.AppProtocol) -> None:
        app.exit()

    def apply_dark_mode(self, app: nv.AppProtocol) -> None:
        app.set_theme("dark")


def test_view_model_commands_the_window_without_a_tree() -> None:
    window = FakeWindow()

    ShellViewModel().send_to_background(window)

    assert window.calls == ["hide"]
    assert window.is_visible.value is False


def test_view_model_commands_the_app_without_a_tree() -> None:
    app = FakeApp()
    vm = ShellViewModel()

    vm.apply_dark_mode(app)
    vm.quit(app)

    assert app.themes == ["dark"]
    assert app.exit_codes == [0]


@pytest.mark.asyncio
async def test_view_model_awaits_window_closed() -> None:
    window = FakeWindow()

    task = asyncio.ensure_future(window.closed)
    await asyncio.sleep(0)
    assert not task.done()

    window.close()
    await task
    assert window.is_open.value is False
