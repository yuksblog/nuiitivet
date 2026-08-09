"""Tests for the on_size_changed() modifier."""

from __future__ import annotations

import asyncio

import pytest

from nuiitivet.layout.column import Column
from nuiitivet.layout.container import Container
from nuiitivet.modifiers import on_size_changed
from nuiitivet.rendering.size import Size
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget_size_change import flush_size_change_callbacks
from nuiitivet.widgets.box import Box


@pytest.fixture(autouse=True)
def _drain_queue():
    """Keep a test's queued measurements from leaking into the next test."""
    flush_size_change_callbacks()
    yield
    flush_size_change_callbacks()


class _DummyApp:
    def invalidate(self, immediate: bool = False) -> None:
        del immediate


def _make_widget() -> Box:
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50))


# --- Registration semantics -------------------------------------------------


def test_modifier_returns_same_instance_without_wrapping() -> None:
    widget = _make_widget()
    wrapped = widget.modifier(on_size_changed(lambda size: None))
    assert wrapped is widget


def test_multiple_callbacks_all_fire() -> None:
    first: list[Size] = []
    second: list[Size] = []
    widget = _make_widget().modifier(on_size_changed(first.append) | on_size_changed(second.append))

    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()

    assert first == [Size(300, 200)]
    assert second == [Size(300, 200)]


# --- Dispatch timing --------------------------------------------------------


def test_callback_does_not_run_during_layout() -> None:
    seen: list[Size] = []
    widget = _make_widget().modifier(on_size_changed(seen.append))

    widget.set_layout_rect(0, 0, 300, 200)
    # Still inside the layout pass as far as the widget is concerned: nothing
    # may have run yet.
    assert seen == []

    flush_size_change_callbacks()
    assert seen == [Size(300, 200)]


def test_only_the_final_size_of_a_pass_is_reported() -> None:
    seen: list[Size] = []
    widget = _make_widget().modifier(on_size_changed(seen.append))

    # Several measurements within one frame coalesce into one report.
    widget.set_layout_rect(0, 0, 100, 100)
    widget.set_layout_rect(0, 0, 200, 100)
    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()

    assert seen == [Size(300, 200)]


def test_flush_requests_a_frame() -> None:
    frames: list[bool] = []

    class _App(_DummyApp):
        def invalidate(self, immediate: bool = False) -> None:
            frames.append(True)

    widget = _make_widget().modifier(on_size_changed(lambda size: None))
    widget.mount(_App())
    frames.clear()

    widget.set_layout_rect(0, 0, 300, 200)

    # Without this an idle, draw-on-demand app would never reach the flush.
    assert frames


# --- Initial call and de-duplication ----------------------------------------


def test_first_measurement_fires() -> None:
    seen: list[Size] = []
    widget = _make_widget().modifier(on_size_changed(seen.append))

    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()

    assert seen == [Size(300, 200)]


def test_unchanged_size_does_not_refire() -> None:
    seen: list[Size] = []
    widget = _make_widget().modifier(on_size_changed(seen.append))

    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()
    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()

    assert seen == [Size(300, 200)]


def test_moving_without_resizing_does_not_fire() -> None:
    seen: list[Size] = []
    widget = _make_widget().modifier(on_size_changed(seen.append))

    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()
    widget.set_layout_rect(40, 80, 300, 200)  # same box, new position
    flush_size_change_callbacks()

    assert seen == [Size(300, 200)]


def test_resize_fires_again() -> None:
    seen: list[Size] = []
    widget = _make_widget().modifier(on_size_changed(seen.append))

    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()
    widget.set_layout_rect(0, 0, 640, 480)
    flush_size_change_callbacks()

    assert seen == [Size(300, 200), Size(640, 480)]


def test_registering_after_layout_fires_immediately() -> None:
    seen: list[Size] = []
    widget = _make_widget()
    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()

    # The widget was already measured; the contract is one initial call, so the
    # late arrival must not have to wait for the next resize.
    widget.modifier(on_size_changed(seen.append))

    assert seen == [Size(300, 200)]


# --- Integration with a real layout pass ------------------------------------


def test_reports_the_size_a_parent_imposes() -> None:
    seen: list[Size] = []
    child = Container(width=Sizing.weight(1), height=Sizing.weight(1)).modifier(on_size_changed(seen.append))
    root = Column([child], width=Sizing.fixed(400), height=Sizing.fixed(300))

    root.layout(400, 300)
    flush_size_change_callbacks()

    assert seen == [Size(400, 300)]


def test_a_callback_may_rebuild_the_tree() -> None:
    # The whole point of deferring past layout: user code is free to mutate.
    root = Column([], width=Sizing.fixed(400), height=Sizing.fixed(300))
    child = Container(width=Sizing.weight(1), height=Sizing.weight(1))

    def _add_a_child(size: Size) -> None:
        root.add_child(Box(width=Sizing.fixed(int(size.width // 2)), height=Sizing.fixed(10)))

    root.add_child(child.modifier(on_size_changed(_add_a_child)))
    root.layout(400, 300)
    flush_size_change_callbacks()

    assert len(root.children) == 2


# --- Unmounted widgets ------------------------------------------------------


def test_unmounted_widget_does_not_receive_a_queued_report() -> None:
    seen: list[Size] = []
    widget = _make_widget().modifier(on_size_changed(seen.append))
    widget.mount(_DummyApp())

    widget.set_layout_rect(0, 0, 300, 200)
    widget.unmount()
    flush_size_change_callbacks()

    assert seen == []


# --- Async callbacks --------------------------------------------------------


def test_async_callback_is_scheduled_as_a_task() -> None:
    seen: list[Size] = []

    async def _on_size(size: Size) -> None:
        seen.append(size)

    async def _run() -> None:
        widget = _make_widget().modifier(on_size_changed(_on_size))
        widget.set_layout_rect(0, 0, 300, 200)
        flush_size_change_callbacks()
        await asyncio.sleep(0)

    asyncio.run(_run())

    assert seen == [Size(300, 200)]


# --- Error containment ------------------------------------------------------


def test_a_raising_callback_does_not_break_the_others() -> None:
    seen: list[Size] = []

    def _boom(size: Size) -> None:
        raise RuntimeError("callback failed")

    widget = _make_widget().modifier(on_size_changed(_boom) | on_size_changed(seen.append))
    widget.set_layout_rect(0, 0, 300, 200)
    flush_size_change_callbacks()

    assert seen == [Size(300, 200)]
