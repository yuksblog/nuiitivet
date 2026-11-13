"""Tests for the app badge: the label, the binding, and each platform's bridge.

The label, the binding, the Windows overlay pixels and the Linux launcher
properties touch no platform API and run everywhere. The Dock test is
macOS-only. The bus test runs on Linux against a private ``dbus-daemon``. The
Windows smoke test is Windows-only: CI runs on Linux, so run it manually on a
Windows machine.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, List, Optional

import pytest

from nuiitivet.common.logging_once import _clear_log_once_keys_for_tests
from nuiitivet.observable import State
from nuiitivet.platform.badge import BadgeBinding, BadgeValue, badge_label
from nuiitivet.platform.badge_launcher_plan import desktop_entry_uri, launcher_properties
from nuiitivet.platform.badge_win32_plan import overlay_label, render_overlay_bgra

macos_only = pytest.mark.skipif(sys.platform != "darwin", reason="The Dock badge is macOS-only")
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="The taskbar overlay is Windows-only")

_TIMEOUT = 5.0


@pytest.fixture(autouse=True)
def _fresh_once_log() -> None:
    _clear_log_once_keys_for_tests()


# ---- Label --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "label"),
    [(3, "3"), (120, "120"), ("!", "!"), (" new ", "new"), (None, ""), (0, ""), (-2, ""), ("", ""), ("  ", "")],
)
def test_label_of_a_value(value: BadgeValue, label: str) -> None:
    assert badge_label(value) == label


def test_a_value_of_another_type_is_refused() -> None:
    with pytest.raises(TypeError, match="App.badge takes an int, a str or None"):
        badge_label(1.5)  # type: ignore[arg-type]


# ---- Binding ------------------------------------------------------------------


class _Bridge:
    def __init__(self, fails: bool = False) -> None:
        self.shown: List[str] = []
        self.closed = False
        self._fails = fails

    def show(self, label: str) -> None:
        if self._fails:
            raise OSError("the platform refused the badge")
        self.shown.append(label)

    def close(self) -> None:
        self.closed = True


class _Binding(BadgeBinding):
    """A binding whose bridge is the test's, and which counts how often one was asked for."""

    def __init__(self, badge: State[BadgeValue], bridge: Optional[_Bridge], raises: bool = False) -> None:
        super().__init__(badge, lambda: None)
        self.created = 0
        self._fake = bridge
        self._raises = raises

    def _create_bridge(self) -> Optional[_Bridge]:
        self.created += 1
        if self._raises:
            raise RuntimeError("no session bus")
        return self._fake


def test_no_bridge_is_made_until_a_badge_shows() -> None:
    badge: State[BadgeValue] = State(None)
    binding = _Binding(badge, _Bridge())

    binding.install()
    badge.value = 0
    assert binding.created == 0

    badge.value = 2
    assert binding.created == 1


def test_a_platform_without_a_badge_is_logged_once(caplog: pytest.LogCaptureFixture) -> None:
    badge: State[BadgeValue] = State(1)
    binding = _Binding(badge, None)

    with caplog.at_level(logging.WARNING, logger="nuiitivet.platform.badge"):
        binding.install()
        badge.value = 2
        badge.value = 3

    assert binding.created == 1
    assert [record.getMessage() for record in caplog.records] == [
        "This platform shows no app badge; App.badge is ignored"
    ]


def test_a_bridge_that_cannot_be_made_is_logged_once_and_the_writes_go_on(caplog: pytest.LogCaptureFixture) -> None:
    badge: State[BadgeValue] = State(1)
    binding = _Binding(badge, None, raises=True)

    with caplog.at_level(logging.ERROR, logger="nuiitivet.platform.badge"):
        binding.install()
        badge.value = 2

    assert binding.created == 1
    assert [record.getMessage() for record in caplog.records] == [
        "The app badge is unavailable; continuing without one"
    ]


def test_a_bridge_that_fails_to_show_never_raises_into_the_writer(caplog: pytest.LogCaptureFixture) -> None:
    badge: State[BadgeValue] = State(None)
    binding = _Binding(badge, _Bridge(fails=True))
    binding.install()

    with caplog.at_level(logging.ERROR, logger="nuiitivet.platform.badge"):
        badge.value = 1
        badge.value = 2

    assert [record.getMessage() for record in caplog.records] == [
        "The app badge could not be shown; continuing without one"
    ]
    binding.uninstall()


def test_a_value_that_is_not_a_badge_is_logged_and_leaves_the_badge(caplog: pytest.LogCaptureFixture) -> None:
    bridge = _Bridge()
    badge: State[Any] = State(1)
    binding = _Binding(badge, bridge)
    binding.install()

    with caplog.at_level(logging.ERROR, logger="nuiitivet.platform.badge"):
        badge.value = 1.5

    assert bridge.shown == ["1"]
    assert [record.getMessage() for record in caplog.records] == [
        "App.badge holds a value that is not a badge; ignored"
    ]


# ---- Windows overlay plan -----------------------------------------------------


@pytest.mark.parametrize(
    ("label", "shown"),
    [("3", "3"), ("99", "99"), ("100", "99+"), ("12345", "99+"), ("!", "!"), ("new!", "new")],
)
def test_overlay_label_fits_a_small_icon(label: str, shown: str) -> None:
    assert overlay_label(label) == shown


@pytest.mark.parametrize("size", [16, 20, 24, 32])
def test_overlay_is_a_red_disc_with_white_text(size: int) -> None:
    pixels = render_overlay_bgra("3", size)

    assert len(pixels) == size * size * 4
    # A corner lies outside the disc.
    assert pixels[3] == 0
    # BGRA: the disc is red where the text does not cover it.
    blue, green, red, alpha = pixels[(size // 2) * size * 4 + 4 : (size // 2) * size * 4 + 8]
    assert alpha == 255 and red > 200 and blue < 80 and green < 80
    whites = sum(1 for i in range(0, len(pixels), 4) if pixels[i : i + 4] == b"\xff\xff\xff\xff")
    assert whites > 0


@pytest.mark.parametrize("label", ["8", "88", "99+", "WWW"])
def test_overlay_text_stays_inside_the_icon(label: str) -> None:
    size = 16
    pixels = render_overlay_bgra(label, size)

    def is_white(x: int, y: int) -> bool:
        offset = (y * size + x) * 4
        return pixels[offset : offset + 4] == b"\xff\xff\xff\xff"

    edge = [(x, y) for x in range(size) for y in range(size) if x in (0, size - 1) or y in (0, size - 1)]
    assert not any(is_white(x, y) for x, y in edge)


# ---- Linux launcher plan ------------------------------------------------------


def test_the_entry_the_launcher_started_names_the_app() -> None:
    environ = {
        "GIO_LAUNCHED_DESKTOP_FILE": "/usr/share/applications/org.example.Mail.desktop",
        "GIO_LAUNCHED_DESKTOP_FILE_PID": "4242",
    }
    assert desktop_entry_uri(environ, 4242, 1, "/opt/mail/main.py") == "application://org.example.Mail.desktop"


def test_the_entry_the_launcher_started_the_parent_from_names_the_app() -> None:
    # A one-file bundle: the launcher started the bootloader, and the app runs as its child.
    environ = {
        "GIO_LAUNCHED_DESKTOP_FILE": "/usr/share/applications/myapp.desktop",
        "GIO_LAUNCHED_DESKTOP_FILE_PID": "5000",
    }
    assert desktop_entry_uri(environ, 5001, 5000, "/opt/myapp/MyApp") == "application://myapp.desktop"


def test_an_entry_inherited_from_further_up_is_not_this_app() -> None:
    # Started from a terminal: the variables name the terminal's entry and pid, and the parent is the shell.
    environ = {
        "GIO_LAUNCHED_DESKTOP_FILE": "/usr/share/applications/org.gnome.Terminal.desktop",
        "GIO_LAUNCHED_DESKTOP_FILE_PID": "100",
    }
    assert desktop_entry_uri(environ, 4242, 101, "/home/me/mail.py") == "application://mail.desktop"


def test_without_a_launcher_the_program_names_the_entry() -> None:
    assert desktop_entry_uri({}, 4242, 1, "/opt/mail/MyMail") == "application://MyMail.desktop"


def test_launcher_properties_of_a_count() -> None:
    assert launcher_properties("3") == {"count": ("x", 3), "count-visible": ("b", True)}


def test_launcher_properties_of_no_badge() -> None:
    assert launcher_properties("") == {"count": ("x", 0), "count-visible": ("b", False)}


@pytest.mark.parametrize("label", ["!", "99+", "²"])
def test_a_text_has_no_launcher_properties(label: str) -> None:
    assert launcher_properties(label) is None


# ---- macOS: the Dock tile -----------------------------------------------------


@macos_only
def test_dock_tile_carries_the_label_and_loses_it() -> None:
    from pyglet.libs.darwin.cocoapy import ObjCClass, cfstring_to_string

    from nuiitivet.platform.badge_cocoa import DockBadgeBridge

    tile = ObjCClass("NSApplication").sharedApplication().dockTile()
    bridge = DockBadgeBridge()
    try:
        bridge.show("3")
        assert cfstring_to_string(tile.badgeLabel()) == "3"
    finally:
        bridge.show("")
    assert not tile.badgeLabel()


# ---- Linux: the bus -----------------------------------------------------------


def test_launcher_entry_update_reaches_the_bus(session_bus: str, monkeypatch: pytest.MonkeyPatch) -> None:
    import jeepney
    from jeepney.io.blocking import Proxy, open_dbus_connection

    from nuiitivet.platform.badge_launcher import LauncherEntryBridge

    monkeypatch.delenv("GIO_LAUNCHED_DESKTOP_FILE", raising=False)
    monkeypatch.setattr(sys, "argv", ["/opt/mail/mail.py"])

    listener: Any = open_dbus_connection(bus=session_bus)
    rule = jeepney.MatchRule(type="signal", interface="com.canonical.Unity.LauncherEntry", member="Update")
    Proxy(jeepney.message_bus, listener, timeout=_TIMEOUT).AddMatch(rule)
    bridge = LauncherEntryBridge()
    try:
        with listener.filter(rule) as matches:
            bridge.show("3")
            assert listener.recv_until_filtered(matches, timeout=_TIMEOUT).body == (
                "application://mail.desktop",
                {"count": ("x", 3), "count-visible": ("b", True)},
            )
            bridge.show("!")
            assert listener.recv_until_filtered(matches, timeout=_TIMEOUT).body == (
                "application://mail.desktop",
                {"count": ("x", 0), "count-visible": ("b", False)},
            )
    finally:
        bridge.close()
        listener.close()


# ---- Windows smoke test (manual: CI is Linux-only) ----------------------------


@windows_only
def test_overlay_icon_is_built_from_the_pixels() -> None:
    from nuiitivet.platform import tray_win32

    hicon = tray_win32._create_icon(render_overlay_bgra("3", 16), 16)
    assert hicon
    user32: Any = getattr(tray_win32, "_user32")
    user32.DestroyIcon(hicon)
