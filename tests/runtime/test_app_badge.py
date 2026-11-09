"""``App.badge``: the value an app writes, and the hooks a backend shows it through."""

from __future__ import annotations

import threading
from typing import Callable, List

import pytest

import nuiitivet.material as nv
from nuiitivet.observable import runtime
from nuiitivet.platform.badge import BadgeBinding
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgets.text import TextBase as Text


class _Bridge:
    def __init__(self) -> None:
        self.shown: List[str] = []
        self.closed = False

    def show(self, label: str) -> None:
        self.shown.append(label)

    def close(self) -> None:
        self.closed = True


class _RecordingClock:
    """Collects what is marshalled to the UI thread; ``run`` plays it there."""

    def __init__(self) -> None:
        self.scheduled: List[Callable[[float], None]] = []

    def schedule_once(self, fn: Callable[[float], None], delay: float) -> None:
        self.scheduled.append(fn)

    def run(self) -> None:
        scheduled, self.scheduled = self.scheduled, []
        for fn in scheduled:
            fn(0.0)


@pytest.fixture
def bridge(monkeypatch: pytest.MonkeyPatch) -> _Bridge:
    fake = _Bridge()
    monkeypatch.setattr(BadgeBinding, "_create_bridge", lambda self: fake)
    return fake


def _app() -> App:
    return App(Window(content=lambda: Text("x")))


def test_no_badge_by_default() -> None:
    assert _app().badge.value is None


def test_the_public_app_carries_the_badge() -> None:
    app = nv.App(nv.Window(content=lambda: nv.Text("x")))
    app.badge.value = 3
    assert app.badge.value == 3


def test_a_value_written_before_the_loop_shows_at_install(bridge: _Bridge) -> None:
    app = _app()
    app.badge.value = 3
    assert bridge.shown == []

    app._install_badge(lambda: None)

    assert bridge.shown == ["3"]


def test_every_later_write_reaches_the_platform(bridge: _Bridge) -> None:
    app = _app()
    app._install_badge(lambda: None)

    app.badge.value = 3
    app.badge.value = "!"
    app.badge.value = None

    assert bridge.shown == ["3", "!", ""]


def test_a_write_from_another_thread_is_shown_on_the_ui_thread(
    bridge: _Bridge, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = _RecordingClock()
    monkeypatch.setattr(runtime, "clock", clock)
    app = _app()
    app._install_badge(lambda: None)

    worker = threading.Thread(target=lambda: setattr(app.badge, "value", 5))
    worker.start()
    worker.join()

    assert bridge.shown == []
    clock.run()
    assert bridge.shown == ["5"]


def test_uninstall_removes_the_badge_and_stops_following(bridge: _Bridge) -> None:
    app = _app()
    app._install_badge(lambda: None)
    app.badge.value = 3

    app._uninstall_badge()
    app.badge.value = 4

    assert bridge.shown == ["3", ""]
    assert bridge.closed


def test_a_window_shown_again_gets_the_badge_again(bridge: _Bridge) -> None:
    app = _app()
    app._install_badge(lambda: None)
    app.badge.value = 3

    app._window_visibility_changed()

    assert bridge.shown == ["3", "3"]
