"""A window's frame lays out what the frame before left pending, and asks for the frame after while a subtree waits.

The frames here follow each other with no idle time between them, as while a
live image or an animation asks for a frame every frame.
"""

from __future__ import annotations

from time import perf_counter

import pytest

from nuiitivet.layout import layout_utils
from nuiitivet.layout.column import Column
from nuiitivet.layout.layout_utils import has_pending_layout
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.app import App
from nuiitivet.runtime.window import Window
from nuiitivet.widgeting import frame_clock
from nuiitivet.widgeting.frame_clock import begin_frame, end_frame
from nuiitivet.widgets.box import Box


class _Probe(Box):
    """A box that counts its paints."""

    painted = 0

    def paint(self, canvas, x: int, y: int, width: int, height: int) -> None:
        self.painted += 1
        super().paint(canvas, x, y, width, height)


class _OsWindow:
    """Stands in for the pyglet window: ``on_draw`` renders the raster path's frame."""

    has_exit = False

    def __init__(self, window: Window) -> None:
        self._window = window

    def switch_to(self) -> None:
        return None

    def dispatch_event(self, name: str) -> None:
        assert name == "on_draw"
        self._window._render_display_frame(1.0)

    def flip(self) -> None:
        return None


@pytest.fixture(autouse=True)
def no_leftover_state():
    layout_utils._pending.clear()
    frame_clock._started_at = None
    yield
    layout_utils._pending.clear()
    frame_clock._started_at = None


def _window(probe: _Probe) -> Window:
    window = App(Window(content=Column([probe], width="wt", height="wt"), width=300, height=200)).main_window
    window._window = _OsWindow(window)  # type: ignore[assignment]
    window._visible_obs.value = True
    return window


def _frame(window: Window) -> None:
    begin_frame(perf_counter())
    try:
        window._render_frame(1 / 60)
    finally:
        end_frame()


def test_the_frame_after_a_cut_lays_the_pending_subtree_out_and_paints_it(monkeypatch) -> None:
    probe = _Probe(width=Sizing.fixed(50), height=Sizing.fixed(20))
    window = _window(probe)

    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.0)
    _frame(window)
    assert has_pending_layout() and probe.painted == 0
    assert window._paint_dirty, "the frame asked for the one that paints the tree again"

    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 1000.0)
    _frame(window)
    assert not has_pending_layout()
    assert probe.painted == 1
    assert not window._paint_dirty, "nothing waits: no further frame is asked for"


def test_a_frame_that_cuts_nothing_asks_for_no_frame() -> None:
    probe = _Probe(width=Sizing.fixed(50), height=Sizing.fixed(20))
    window = _window(probe)

    _frame(window)
    assert probe.painted == 1
    assert not has_pending_layout() and not window._paint_dirty


def test_a_draw_that_raises_asks_for_no_frame(monkeypatch) -> None:
    probe = _Probe(width=Sizing.fixed(50), height=Sizing.fixed(20))
    window = _window(probe)
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.0)
    _frame(window)
    assert has_pending_layout()

    def raising(_name: str) -> None:
        raise ValueError("the draw failed")

    monkeypatch.setattr(window._window, "dispatch_event", raising)
    window._paint_dirty = False
    _frame(window)
    assert not window._paint_dirty, "a draw that fails every frame must not ask for frames without end"


def test_a_subtree_pending_in_another_window_asks_this_one_for_no_frame(monkeypatch) -> None:
    probe = _Probe(width=Sizing.fixed(50), height=Sizing.fixed(20))
    window = _window(probe)
    _frame(window)
    assert not window._paint_dirty

    other = _window(_Probe(width=Sizing.fixed(50), height=Sizing.fixed(20)))
    monkeypatch.setattr(layout_utils, "LAYOUT_SHARE", 0.0)
    _frame(other)
    assert has_pending_layout(other) and not has_pending_layout(window)

    window._request_frame_for_pending_layout()
    assert not window._paint_dirty
