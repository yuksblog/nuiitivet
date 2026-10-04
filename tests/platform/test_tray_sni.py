"""Tests for the Linux StatusNotifierItem tray backend.

The menu plan and the icon encoding touch no bus and run on every platform.
The bus tests at the bottom run on Linux against a private ``dbus-daemon``,
with a fake StatusNotifierWatcher and a dbusmenu client inside the test; they
skip where the daemon binary or jeepney is missing.
"""

from __future__ import annotations

import queue
import shutil
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Iterator, List, Tuple

import pytest
import skia as _skia

from nuiitivet.menus import MenuEntry
from nuiitivet.observable import Observable, runtime
from nuiitivet.platform.tray import TrayIcon
from nuiitivet.platform.tray_sni_plan import (
    LAYOUT_SIGNATURE,
    ROOT_ID,
    encode_layout,
    find_node,
    flatten,
    load_icon_argb,
    placeholder_icon,
    plan_menu,
    select_properties,
)

# The skia stub covers only what src/ uses.
skia: Any = _skia


# ---- Menu plan --------------------------------------------------------------


def test_plan_gives_every_item_an_id_and_maps_actions() -> None:
    open_entry = MenuEntry("Open", on_select=lambda: None)
    child = MenuEntry("Child", on_select=lambda: None)
    quit_entry = MenuEntry.quit()
    root, commands = plan_menu([open_entry, MenuEntry.separator(), MenuEntry("More", submenu=[child]), quit_entry])

    assert root.id == ROOT_ID
    assert [node.id for node in flatten(root)] == [0, 1, 2, 3, 4, 5]
    open_item, separator, more, quit_item = root.children
    assert open_item.properties == {"label": ("s", "Open"), "enabled": ("b", True)}
    assert separator.properties == {"type": ("s", "separator")}
    assert more.properties["children-display"] == ("s", "submenu")
    assert commands == {open_item.id: open_entry, more.children[0].id: child, quit_item.id: quit_entry}


def test_plan_reads_observables_at_plan_time_and_keeps_ids() -> None:
    label = Observable("Ping (0)")
    enabled = Observable(True)
    checked = Observable(False)
    menu = [MenuEntry(label, on_select=lambda: None, enabled=enabled, checked=checked)]

    before, _ = plan_menu(menu)
    assert before.children[0].properties == {
        "label": ("s", "Ping (0)"),
        "enabled": ("b", True),
        "toggle-type": ("s", "checkmark"),
        "toggle-state": ("i", 0),
    }

    label.value = "Ping (1)"
    enabled.value = False
    checked.value = True
    after, _ = plan_menu(menu)
    assert after.children[0].id == before.children[0].id
    assert after.children[0].properties == {
        "label": ("s", "Ping (1)"),
        "enabled": ("b", False),
        "toggle-type": ("s", "checkmark"),
        "toggle-state": ("i", 1),
    }


def test_plan_escapes_underscore() -> None:
    root, _ = plan_menu([MenuEntry("snake_case", on_select=lambda: None)])
    assert root.children[0].properties["label"] == ("s", "snake__case")


def test_layout_encodes_children_as_variants() -> None:
    root, _ = plan_menu([MenuEntry("More", submenu=[MenuEntry("Child", on_select=lambda: None)])])

    item_id, properties, children = encode_layout(root, -1, [])
    assert (item_id, properties) == (ROOT_ID, {"children-display": ("s", "submenu")})
    signature, (more_id, _more_properties, more_children) = children[0]
    assert (signature, more_id) == (LAYOUT_SIGNATURE, 1)
    assert more_children[0][1][0] == 2


def test_layout_honours_depth_and_property_names() -> None:
    root, _ = plan_menu([MenuEntry("More", submenu=[MenuEntry("Child", on_select=lambda: None)])])

    assert encode_layout(root, 0, [])[2] == []
    _, _, children = encode_layout(root, 1, ["label"])
    _, (_, properties, grandchildren) = children[0]
    assert properties == {"label": ("s", "More")}
    assert grandchildren == []


def test_find_node_and_select_properties() -> None:
    root, _ = plan_menu([MenuEntry("Open", on_select=lambda: None)])
    node = find_node(root, 1)
    assert node is not None
    assert select_properties(node, ["enabled", "missing"]) == {"enabled": ("b", True)}
    assert find_node(root, 99) is None


# ---- Icon encoding ----------------------------------------------------------


def _write_png(path: Path, width: int, height: int, color: int) -> None:
    surface = skia.Surface(width, height)
    surface.getCanvas().clear(color)
    surface.makeImageSnapshot().save(str(path), skia.kPNG)


def test_icon_encodes_to_argb_with_straight_alpha(tmp_path: Path) -> None:
    path = tmp_path / "icon.png"
    _write_png(path, 16, 16, skia.Color(255, 0, 0, 128))

    pixmap = load_icon_argb(path)
    assert pixmap is not None
    width, height, pixels = pixmap
    assert (width, height, len(pixels)) == (16, 16, 16 * 16 * 4)
    alpha, red, green, blue = pixels[:4]
    assert (alpha, green, blue) == (128, 0, 0)
    assert red >= 254  # not premultiplied down to 128


def test_large_icon_is_scaled_down_keeping_its_shape(tmp_path: Path) -> None:
    path = tmp_path / "icon.png"
    _write_png(path, 512, 256, skia.Color(0, 0, 255, 255))

    pixmap = load_icon_argb(path)
    assert pixmap is not None
    width, height, pixels = pixmap
    assert (width, height) == (128, 64)
    assert tuple(pixels[:4]) == (255, 0, 0, 255)


def test_icon_that_cannot_be_decoded_is_none(tmp_path: Path) -> None:
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not an image")
    assert load_icon_argb(broken) is None
    assert load_icon_argb(tmp_path / "missing.png") is None


def test_placeholder_icon_is_a_full_pixmap() -> None:
    width, height, pixels = placeholder_icon()
    assert len(pixels) == width * height * 4


# ---- Bus tests (Linux, private dbus-daemon) ---------------------------------

_WATCHER_NAME = "org.kde.StatusNotifierWatcher"
_ITEM_PATH = "/StatusNotifierItem"
_ITEM_INTERFACE = "org.kde.StatusNotifierItem"
_MENU_PATH = "/MenuBar"
_MENU_INTERFACE = "com.canonical.dbusmenu"
_PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
_TIMEOUT = 5.0


class _RecordingClock:
    """Collects the callbacks the bridge hops to the UI thread; ``run`` plays them."""

    def __init__(self) -> None:
        self.scheduled: List[Callable[[float], None]] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        self.scheduled.append(fn)

    def run(self) -> None:
        scheduled, self.scheduled = self.scheduled, []
        for fn in scheduled:
            fn(0.0)


class _FakeWatcher:
    """Owns the watcher name and records every registration it receives."""

    def __init__(self, address: str) -> None:
        import jeepney
        from jeepney.io.blocking import Proxy, open_dbus_connection

        self._jeepney: Any = jeepney
        self._conn: Any = open_dbus_connection(bus=address)
        Proxy(jeepney.message_bus, self._conn, timeout=_TIMEOUT).RequestName(_WATCHER_NAME)
        self.registrations: "queue.Queue[Tuple[str, str]]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        jeepney = self._jeepney
        while True:
            try:
                message = self._conn.receive()
            except Exception:
                return
            fields = message.header.fields
            if (
                message.header.message_type is jeepney.MessageType.method_call
                and fields.get(jeepney.HeaderFields.member) == "RegisterStatusNotifierItem"
            ):
                self.registrations.put((fields[jeepney.HeaderFields.sender], message.body[0]))
                self._conn.send(jeepney.new_method_return(message))

    def stop(self) -> None:
        self._conn.sock.shutdown(socket.SHUT_RDWR)
        self._thread.join(timeout=_TIMEOUT)
        self._conn.close()


class _Client:
    """The desktop's side: calls the item and its menu, and waits for their signals."""

    def __init__(self, address: str, item: str) -> None:
        import jeepney
        from jeepney.io.blocking import Proxy, open_dbus_connection

        self._jeepney: Any = jeepney
        self._conn: Any = open_dbus_connection(bus=address)
        self._bus: Any = Proxy(jeepney.message_bus, self._conn, timeout=_TIMEOUT)
        self._item = item

    def call(self, path: str, interface: str, member: str, signature: str = "", body: Tuple[Any, ...] = ()) -> Any:
        from jeepney.wrappers import unwrap_msg

        jeepney = self._jeepney
        target = jeepney.DBusAddress(path, bus_name=self._item, interface=interface)
        message = jeepney.new_method_call(target, member, signature or None, body)
        return unwrap_msg(self._conn.send_and_get_reply(message, timeout=_TIMEOUT))

    def item_property(self, name: str) -> Any:
        return self.call(_ITEM_PATH, _PROPERTIES_INTERFACE, "Get", "ss", (_ITEM_INTERFACE, name))[0][1]

    def layout(self) -> Tuple[int, Any]:
        revision, layout = self.call(_MENU_PATH, _MENU_INTERFACE, "GetLayout", "iias", (ROOT_ID, -1, []))
        return revision, layout

    def expect_signal(self, interface: str, member: str, trigger: Callable[[], None]) -> Any:
        """Run ``trigger`` and return the body of the signal it must cause."""
        jeepney = self._jeepney
        rule = jeepney.MatchRule(type="signal", sender=self._item, interface=interface, member=member)
        self._bus.AddMatch(rule)
        with self._conn.filter(rule) as matches:
            trigger()
            return self._conn.recv_until_filtered(matches, timeout=_TIMEOUT).body

    def close(self) -> None:
        self._conn.close()


class _App:
    """Weakref-able stand-in for the App a tray is installed on."""


@pytest.fixture
def session_bus(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A private session bus; ``DBUS_SESSION_BUS_ADDRESS`` points at it."""
    if sys.platform != "linux":
        pytest.skip("StatusNotifierItem backend is Linux-only")
    pytest.importorskip("jeepney")
    daemon = shutil.which("dbus-daemon")
    if daemon is None:
        pytest.skip("dbus-daemon is not installed")
    process = subprocess.Popen(
        [daemon, "--session", "--nofork", "--print-address"], stdout=subprocess.PIPE, text=True
    )
    assert process.stdout is not None
    address = process.stdout.readline().strip()
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", address)
    try:
        yield address
    finally:
        process.terminate()
        process.wait(timeout=_TIMEOUT)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _RecordingClock:
    recording = _RecordingClock()
    monkeypatch.setattr(runtime, "clock", recording)
    return recording


@pytest.fixture
def watcher(session_bus: str) -> Iterator[_FakeWatcher]:
    fake = _FakeWatcher(session_bus)
    try:
        yield fake
    finally:
        fake.stop()


def _install(tray: TrayIcon) -> Any:
    bridge = tray._create_bridge()
    bridge.install()
    return bridge


def test_without_watcher_install_fails_and_installed_stays_false(session_bus: str) -> None:
    tray = TrayIcon(menu=[MenuEntry.quit()])
    with pytest.raises(RuntimeError):
        tray._create_bridge().install()

    tray._install(_App())  # type: ignore[arg-type]
    assert tray.installed.value is False


def test_registers_and_serves_item_properties(session_bus: str, watcher: _FakeWatcher) -> None:
    tooltip = Observable("My Sync App")
    bridge = _install(TrayIcon(tooltip=tooltip, menu=[MenuEntry.quit()]))
    try:
        item, path = watcher.registrations.get(timeout=_TIMEOUT)
        assert path == _ITEM_PATH
        client = _Client(session_bus, item)

        properties = client.call(_ITEM_PATH, _PROPERTIES_INTERFACE, "GetAll", "s", (_ITEM_INTERFACE,))[0]
        assert properties["Title"] == ("s", "My Sync App")
        assert properties["Menu"] == ("o", _MENU_PATH)
        assert properties["ItemIsMenu"] == ("b", True)
        width, height, pixels = properties["IconPixmap"][1][0]
        assert len(pixels) == width * height * 4

        def change_tooltip() -> None:
            tooltip.value = "Syncing"

        client.expect_signal(_ITEM_INTERFACE, "NewToolTip", change_tooltip)
        assert client.item_property("Title") == "Syncing"
        assert client.item_property("ToolTip")[2] == "Syncing"
        client.close()
    finally:
        bridge.uninstall()


def test_menu_layout_and_click(session_bus: str, watcher: _FakeWatcher, clock: _RecordingClock) -> None:
    selected: List[str] = []
    muted = Observable(False)
    label = Observable("Ping (0)")
    tray = TrayIcon(
        menu=[
            MenuEntry(label, on_select=lambda: selected.append("ping")),
            MenuEntry.separator(),
            MenuEntry("Muted", on_select=lambda: selected.append("muted"), checked=muted),
            MenuEntry("More", submenu=[MenuEntry("Child", on_select=lambda: selected.append("child"))]),
        ]
    )
    bridge = _install(tray)
    try:
        item, _path = watcher.registrations.get(timeout=_TIMEOUT)
        client = _Client(session_bus, item)

        revision, (_root_id, _root_properties, children) = client.layout()
        ping, separator, muted_item, more = [child[1] for child in children]
        assert ping[1]["label"] == ("s", "Ping (0)")
        assert separator[1]["type"] == ("s", "separator")
        assert muted_item[1]["toggle-state"] == ("i", 0)
        child = more[2][0][1]
        assert child[1]["label"] == ("s", "Child")

        client.call(_MENU_PATH, _MENU_INTERFACE, "Event", "isvu", (child[0], "clicked", ("s", ""), 0))
        clock.run()
        assert selected == ["child"]

        # The click toggles the model on the UI thread; the desktop is told to ask again.
        client.call(_MENU_PATH, _MENU_INTERFACE, "Event", "isvu", (muted_item[0], "clicked", ("s", ""), 0))
        updated = client.expect_signal(_MENU_INTERFACE, "LayoutUpdated", clock.run)
        assert updated[0] > revision
        assert muted.value is True
        assert client.layout()[1][2][2][1][1]["toggle-state"] == ("i", 1)

        def change_label() -> None:
            label.value = "Ping (1)"

        client.expect_signal(_MENU_INTERFACE, "LayoutUpdated", change_label)
        assert client.layout()[1][2][0][1][1]["label"] == ("s", "Ping (1)")

        group = client.call(_MENU_PATH, _MENU_INTERFACE, "GetGroupProperties", "aias", ([ping[0]], ["label"]))[0]
        assert group == [(ping[0], {"label": ("s", "Ping (1)")})]
        client.close()
    finally:
        bridge.uninstall()


def test_activate_fires_on_activate(session_bus: str, watcher: _FakeWatcher, clock: _RecordingClock) -> None:
    activations: List[int] = []
    bridge = _install(TrayIcon(menu=[MenuEntry.quit()], on_activate=lambda: activations.append(1)))
    try:
        item, _path = watcher.registrations.get(timeout=_TIMEOUT)
        client = _Client(session_bus, item)
        assert client.item_property("ItemIsMenu") is False

        client.call(_ITEM_PATH, _ITEM_INTERFACE, "Activate", "ii", (0, 0))
        clock.run()
        assert activations == [1]
        client.close()
    finally:
        bridge.uninstall()


def test_unknown_method_is_an_error_reply(session_bus: str, watcher: _FakeWatcher) -> None:
    import jeepney

    bridge = _install(TrayIcon())
    try:
        item, _path = watcher.registrations.get(timeout=_TIMEOUT)
        client = _Client(session_bus, item)
        with pytest.raises(jeepney.DBusErrorResponse):
            client.call(_ITEM_PATH, _ITEM_INTERFACE, "NoSuchMethod")
        client.close()
    finally:
        bridge.uninstall()


def test_registers_again_when_the_watcher_returns(session_bus: str) -> None:
    first = _FakeWatcher(session_bus)
    bridge = _install(TrayIcon())
    try:
        item, _path = first.registrations.get(timeout=_TIMEOUT)
        first.stop()

        second = _FakeWatcher(session_bus)
        try:
            assert second.registrations.get(timeout=_TIMEOUT) == (item, _ITEM_PATH)
        finally:
            second.stop()
    finally:
        bridge.uninstall()
