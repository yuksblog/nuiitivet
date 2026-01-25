"""Tests for Overlay.show() timeout behavior."""

from __future__ import annotations

import types

from nuiitivet.observable import runtime
from nuiitivet.overlay import Overlay
from nuiitivet.overlay.result import OverlayDismissReason
from nuiitivet.widgets.text import TextBase as Text


def test_overlay_show_timeout_auto_dismisses_via_clock(monkeypatch) -> None:
    overlay = Overlay()

    calls: list[float] = []

    def schedule_once(fn, delay: float) -> None:
        calls.append(float(delay))
        fn(float(delay))

    def unschedule(_fn) -> None:
        return None

    monkeypatch.setattr(runtime, "clock", types.SimpleNamespace(schedule_once=schedule_once, unschedule=unschedule))

    handle = overlay.show(Text("Hi"), passthrough=True, timeout=0.1)
    assert overlay.has_entries() is False
    assert handle.done() is True

    result = handle.result()
    assert result is not None
    assert result.value is None
    assert result.reason is OverlayDismissReason.TIMEOUT
