"""``settle`` finishes the layout a frame left pending: the tree read after it is whole."""

from __future__ import annotations

from time import perf_counter

import pytest

from nuiitivet._interaction.action import settle
from nuiitivet.layout import layout_utils
from nuiitivet.layout.column import Column
from nuiitivet.layout.layout_utils import has_pending_layout, layout_frame
from nuiitivet.layout.row import Row
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.pointer import PointerCaptureManager
from nuiitivet.widgeting import frame_clock
from nuiitivet.widgeting.frame_clock import begin_frame, end_frame
from nuiitivet.widgets.box import Box


class _App:
    def __init__(self) -> None:
        self.width = 200
        self.height = 100
        self.root: Column | None = None
        self._pointer_capture_manager = PointerCaptureManager()

    def invalidate(self, immediate: bool = False) -> None:
        del immediate


def _frame(root: Column, *, root_pass: bool) -> None:
    begin_frame(perf_counter())
    try:
        layout_frame(root, 200, 100, root_pass=root_pass)
    finally:
        end_frame()


@pytest.fixture(autouse=True)
def no_leftover_state():
    layout_utils._pending.clear()
    frame_clock._started_at = None
    yield
    layout_utils._pending.clear()
    frame_clock._started_at = None


@pytest.mark.parametrize("strict", [False, True])
def test_settle_lays_out_what_a_frame_left_pending(strict: bool, monkeypatch) -> None:
    inner = Box(width=Sizing.fixed(50), height=Sizing.fixed(20))
    row = Row([inner], width=Sizing.weight(), height=Sizing.fixed(20))
    app = _App()
    app.root = Column([row], width=Sizing.fixed(200), height=Sizing.fixed(100))
    app.root.mount(app)

    # A frame with no time leaves the row pending. The next one has time for
    # the row alone: the row is clean, and its child is pending below it.
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.0)
    _frame(app.root, root_pass=True)
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.5)
    clock = [0.0, 0.0]
    monkeypatch.setattr(layout_utils, "perf_counter", lambda: clock.pop(0) if clock else float("inf"))
    _frame(app.root, root_pass=False)
    monkeypatch.setattr(layout_utils, "perf_counter", perf_counter)
    assert inner._layout_pending and not row.needs_layout and not row._layout_pending

    settle(app, strict=strict)
    assert not inner._layout_pending and not has_pending_layout()
    assert inner.layout_rect == (0, 0, 50, 20)
