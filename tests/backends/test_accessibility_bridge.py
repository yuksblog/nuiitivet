"""The AccessKit bridge: the tree as AccessKit takes it, and the two callbacks."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any, Callable, Optional

import pytest

accesskit = pytest.importorskip("accesskit")

from nuiitivet.backends.pyglet.accessibility import AccessKitBridge, tree_update  # noqa: E402
from nuiitivet.layout.column import Column  # noqa: E402
from nuiitivet.material import Checkbox, Text  # noqa: E402
from nuiitivet.material.buttons import Button  # noqa: E402
from nuiitivet.material.slider import HorizontalRangeSlider  # noqa: E402
from nuiitivet.runtime.app import App  # noqa: E402
from nuiitivet.runtime.semantics_tree import ROOT_ID, SemanticsEntry, SemanticsTree  # noqa: E402
from nuiitivet.runtime.window import Window  # noqa: E402
from nuiitivet.widgets.semantics import SemanticsRole  # noqa: E402


def _mounted(root) -> Window:
    window = App(Window(content=root, title="Demo")).main_window
    assert window.root is not None
    window.root.mount(window)
    window.root.layout(400, 400)
    return window


def _nodes(update: Any) -> dict[int, Any]:
    return {entry_id: node for entry_id, node in update.nodes}


def _entry(tree: SemanticsTree, role: SemanticsRole) -> SemanticsEntry:
    """The one entry of ``role`` beneath the window's own."""
    (entry,) = [
        entry for entry_id, entry in tree.entries.items() if entry.semantics.role is role and entry_id != ROOT_ID
    ]
    return entry


# --- the tree as an update ----------------------------------------------------


def test_the_window_entry_is_the_root_window_node_scaled_to_backing_pixels() -> None:
    update = tree_update(_mounted(Column([])).semantics_tree(), pixel_ratio=2.0)

    assert update.tree.root == ROOT_ID
    assert update.focus == ROOT_ID
    root = _nodes(update)[ROOT_ID]
    assert root.role == accesskit.Role.WINDOW
    assert root.label == "Demo"
    assert root.transform.coeffs == [2.0, 0.0, 0.0, 2.0, 0.0, 0.0]


def test_a_control_carries_its_role_label_bounds_and_actions() -> None:
    window = _mounted(Column([Text("Title"), Button("Save", on_click=lambda: None)]))
    tree = window.semantics_tree()
    entry = _entry(tree, SemanticsRole.BUTTON)

    node = _nodes(tree_update(tree, 1.0))[entry.id]

    assert node.role == accesskit.Role.BUTTON
    assert node.label == "Save"
    x, y, w, h = entry.rect
    assert (node.bounds.x0, node.bounds.y0, node.bounds.x1, node.bounds.y1) == (x, y, x + w, y + h)
    assert node.supports_action(accesskit.Action.CLICK)
    assert node.supports_action(accesskit.Action.FOCUS)
    assert not node.supports_action(accesskit.Action.INCREMENT)
    assert ROOT_ID in _nodes(tree_update(tree, 1.0)) and entry.id in _nodes(tree_update(tree, 1.0))[ROOT_ID].children


def test_a_text_says_its_words_as_its_value() -> None:
    tree = _mounted(Column([Text("Hello")])).semantics_tree()

    node = _nodes(tree_update(tree, 1.0))[_entry(tree, SemanticsRole.TEXT).id]

    assert node.role == accesskit.Role.LABEL
    assert node.value == "Hello"
    assert node.label is None


def test_a_toggle_and_a_slider_carry_their_state() -> None:
    tree = _mounted(
        Column([Checkbox(indeterminate=True), HorizontalRangeSlider(value_start=20.0, value_end=80.0, max_value=100.0)])
    ).semantics_tree()
    nodes = _nodes(tree_update(tree, 1.0))

    checkbox = nodes[_entry(tree, SemanticsRole.CHECKBOX).id]
    assert checkbox.role == accesskit.Role.CHECK_BOX
    assert checkbox.toggled == accesskit.Toggled.MIXED

    group = _entry(tree, SemanticsRole.GROUP)
    start, end = (nodes[child] for child in group.children)
    assert start.role == accesskit.Role.SLIDER
    assert (start.numeric_value, start.min_numeric_value, start.max_numeric_value) == (20.0, 0.0, 80.0)
    assert end.supports_action(accesskit.Action.INCREMENT)
    assert end.supports_action(accesskit.Action.DECREMENT)


def test_a_disabled_control_is_disabled_and_takes_no_action() -> None:
    tree = _mounted(Column([Button("Save", on_click=lambda: None, disabled=True)])).semantics_tree()

    node = _nodes(tree_update(tree, 1.0))[_entry(tree, SemanticsRole.BUTTON).id]

    assert node.is_disabled
    assert not node.supports_action(accesskit.Action.CLICK)


# --- the bridge ---------------------------------------------------------------


class _Events:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    def raise_events(self) -> None:
        self._log.append("raised")


class _FakeAdapter:
    def __init__(self, *, active: bool = True) -> None:
        self.active = active
        self.updates: list[Any] = []
        self.focus_states: list[bool] = []
        self.log: list[str] = []

    def update_if_active(self, update_factory: Callable[[], Any]) -> Optional[_Events]:
        if not self.active:
            return None
        self.updates.append(update_factory())
        return _Events(self.log)

    def update_view_focus_state(self, is_focused: bool) -> Optional[_Events]:
        self.focus_states.append(is_focused)
        return _Events(self.log)


class _Request:
    def __init__(self, action: Any, target: int) -> None:
        self.action = action
        self.target = target


def _bridge(root) -> tuple[AccessKitBridge, Window, list[Callable[[], None]], _FakeAdapter]:
    window = _mounted(root)
    deferred: list[Callable[[], None]] = []
    bridge = AccessKitBridge(window, pixel_ratio=lambda: 1.0, defer=deferred.append)
    adapter = _FakeAdapter()
    bridge.attach(adapter)
    return bridge, window, deferred, adapter


def test_sync_pushes_the_tree_and_raises_its_events_only_while_active() -> None:
    bridge, _, _, adapter = _bridge(Column([Text("Hi")]))

    bridge.sync()
    assert len(adapter.updates) == 1
    assert adapter.log == ["raised"]

    adapter.active = False
    bridge.sync()
    assert len(adapter.updates) == 1


def test_the_activation_handler_lays_out_a_window_that_never_drew() -> None:
    window = App(Window(content=Column([Button("Save", on_click=lambda: None)]), title="Demo")).main_window
    assert window.root is not None
    window.root.mount(window)
    bridge = AccessKitBridge(window, pixel_ratio=lambda: 1.0, defer=lambda run: None)

    update = bridge.activation_handler()

    button = [node for _, node in update.nodes if node.role == accesskit.Role.BUTTON]
    assert len(button) == 1
    assert button[0].bounds.x1 > button[0].bounds.x0


def test_an_action_runs_on_the_next_turn_and_pushes_the_tree() -> None:
    clicks: list[bool] = []
    bridge, window, deferred, adapter = _bridge(Column([Button("Save", on_click=lambda: clicks.append(True))]))
    entry = _entry(window.semantics_tree(), SemanticsRole.BUTTON)

    bridge.action_handler(_Request(accesskit.Action.CLICK, entry.id))

    assert clicks == []
    (run,) = deferred
    run()
    assert clicks == [True]
    assert len(adapter.updates) == 1


def test_an_unknown_action_or_a_bad_request_is_dropped() -> None:
    bridge, _, deferred, _ = _bridge(Column([Button("Save", on_click=lambda: None)]))

    bridge.action_handler(_Request(accesskit.Action.SCROLL_DOWN, ROOT_ID))
    bridge.action_handler(object())

    assert deferred == []


def test_the_view_focus_state_reaches_the_adapter() -> None:
    bridge, _, _, adapter = _bridge(Column([]))

    bridge.set_view_focused(True)
    bridge.set_view_focused(False)

    assert adapter.focus_states == [True, False]


def test_a_raising_tree_build_answers_an_empty_tree() -> None:
    window = _mounted(Column([]))
    bridge = AccessKitBridge(window, pixel_ratio=lambda: 1 / 0, defer=lambda run: None)

    update = bridge.activation_handler()

    assert [entry_id for entry_id, _ in update.nodes] == [ROOT_ID]


# --- the Windows install ------------------------------------------------------


class _FakeSubclassingAdapter:
    """``accesskit.windows.SubclassingAdapter`` as the install sees it."""

    created: list["_FakeSubclassingAdapter"] = []

    def __init__(self, hwnd: Any, activation_handler: Any, action_handler: Any) -> None:
        self.hwnd = hwnd
        self.activation_handler = activation_handler
        self.action_handler = action_handler
        self.updates: list[Any] = []
        _FakeSubclassingAdapter.created.append(self)

    def update_if_active(self, update_factory: Callable[[], Any]) -> _Events:
        self.updates.append(update_factory())
        return _Events([])


def _windows_install(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Import ``accessibility_windows`` as it imports on Windows, over a fake ``accesskit.windows``."""
    name = "nuiitivet.backends.pyglet.accessibility_windows"
    fake = types.ModuleType("accesskit.windows")
    fake.SubclassingAdapter = _FakeSubclassingAdapter  # type: ignore[attr-defined]
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "accesskit.windows", fake)
    monkeypatch.setattr(accesskit, "windows", fake, raising=False)
    sys.modules.pop(name, None)
    return importlib.import_module(name).install


def test_the_windows_install_subclasses_the_hwnd_with_the_bridge_callbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    install = _windows_install(monkeypatch)
    try:
        _FakeSubclassingAdapter.created.clear()
        bridge = AccessKitBridge(_mounted(Column([Text("Hi")])), pixel_ratio=lambda: 1.0, defer=lambda run: None)

        install(types.SimpleNamespace(_hwnd=0x1234), bridge)
        bridge.sync()
        bridge.set_view_focused(True)

        (adapter,) = _FakeSubclassingAdapter.created
        assert adapter.hwnd == 0x1234
        assert adapter.activation_handler == bridge.activation_handler
        assert adapter.action_handler == bridge.action_handler
        assert len(adapter.updates) == 1
    finally:
        sys.modules.pop("nuiitivet.backends.pyglet.accessibility_windows", None)
