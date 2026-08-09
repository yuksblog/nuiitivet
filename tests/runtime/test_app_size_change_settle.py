"""Tests for how the app dispatches size callbacks around a frame."""

from __future__ import annotations

from nuiitivet.layout.container import Container
from nuiitivet.modifiers import on_size_changed
from nuiitivet.rendering.size import Size
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.runtime.app import App
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks
import pytest


@pytest.fixture(autouse=True)
def _drained_size_callbacks():
    """Keep queued size-change callbacks from leaking between tests."""
    flush_size_change_callbacks()
    try:
        yield
    finally:
        flush_size_change_callbacks()


class _Panel(ComposableWidget):
    """A filling panel that records the sizes it is told about."""

    def __init__(self) -> None:
        super().__init__(width=Sizing.weight(1), height=Sizing.weight(1))
        self.seen: list[Size] = []

    def _on_size(self, size: Size) -> None:
        self.seen.append(size)

    def build(self) -> Widget:
        return Container(width=Sizing.weight(1), height=Sizing.weight(1)).modifier(on_size_changed(self._on_size))


def _mounted_app(panel: Widget, width: int = 800, height: int = 600) -> App:
    app = App(content=panel, width=width, height=height)
    app.root.mount(app)
    return app


def test_layout_alone_does_not_run_callbacks() -> None:
    """The layout pass only queues; user code must never run inside it."""
    panel = _Panel()
    app = _mounted_app(panel)

    app.root.layout(800, 600)

    assert panel.seen == []


def test_the_next_frames_flush_dispatches() -> None:
    panel = _Panel()
    app = _mounted_app(panel)

    app.root.layout(800, 600)
    flush_size_change_callbacks()

    # The panel fills the window, so it is measured at the window size.
    assert panel.seen == [Size(800, 600)]


def test_a_frame_at_the_same_size_is_silent() -> None:
    panel = _Panel()
    app = _mounted_app(panel)

    app.root.layout(800, 600)
    flush_size_change_callbacks()
    app.root.layout(800, 600)
    flush_size_change_callbacks()

    assert panel.seen == [Size(800, 600)]


def test_a_resize_reports_again() -> None:
    panel = _Panel()
    app = _mounted_app(panel)

    app.root.layout(800, 600)
    flush_size_change_callbacks()
    app.root.layout(1024, 600)
    flush_size_change_callbacks()

    assert panel.seen == [Size(800, 600), Size(1024, 600)]


# --- One-shot render settling ----------------------------------------------


def test_snapshot_settling_applies_the_callbacks_effect() -> None:
    """A single render must not capture the pre-callback state."""

    class _Reflowing(ComposableWidget):
        def __init__(self) -> None:
            super().__init__(width=Sizing.weight(1), height=Sizing.weight(1))
            self.wide = False

        def _on_size(self, size: Size) -> None:
            self.wide = size.width >= 700

        def build(self) -> Widget:
            return Container(width=Sizing.weight(1), height=Sizing.weight(1)).modifier(on_size_changed(self._on_size))

    panel = _Reflowing()
    app = _mounted_app(panel)

    app.root.layout(800, 600)
    app._settle_pending_size_changes(800, 600)

    assert panel.wide is True


def test_snapshot_settling_is_bounded_when_a_callback_keeps_resizing() -> None:
    """A callback that resizes what it measures must not loop forever."""
    calls: list[Size] = []

    class _Oscillating(ComposableWidget):
        def __init__(self) -> None:
            super().__init__(width=Sizing.weight(1), height=Sizing.weight(1))
            self._box = Container(width=Sizing.fixed(100), height=Sizing.weight(1))

        def _on_size(self, size: Size) -> None:
            calls.append(size)
            # Feed the measurement straight back into the measured widget.
            self._box.width_sizing = Sizing.fixed(100 if size.width != 100 else 300)

        def build(self) -> Widget:
            return self._box.modifier(on_size_changed(self._on_size))

    app = _mounted_app(_Oscillating())

    app.root.layout(800, 600)
    app._settle_pending_size_changes(800, 600)

    assert 0 < len(calls) <= App._MAX_SNAPSHOT_SETTLE_PASSES
