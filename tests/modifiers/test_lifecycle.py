"""Tests for on_mount() / on_unmount() modifiers."""

from __future__ import annotations

import asyncio

import pytest

from nuiitivet.modifiers import on_mount, on_unmount
from nuiitivet.rendering.sizing import Sizing
from nuiitivet.widgeting.widget import ComposableWidget, Widget
from nuiitivet.widgets.box import Box


class _DummyApp:
    def invalidate(self, immediate: bool = False) -> None:
        del immediate


def _make_widget() -> Box:
    return Box(width=Sizing.fixed(100), height=Sizing.fixed(50))


# --- Registration semantics -------------------------------------------------


def test_modifier_returns_same_instance_without_wrapping() -> None:
    widget = _make_widget()
    wrapped = widget.modifier(on_mount(lambda: None) | on_unmount(lambda: None))
    assert wrapped is widget


def test_mount_and_unmount_callbacks_fire() -> None:
    calls: list[str] = []
    widget = _make_widget().modifier(
        on_mount(lambda: calls.append("mount")) | on_unmount(lambda: calls.append("unmount"))
    )

    widget.mount(_DummyApp())
    assert calls == ["mount"]

    widget.unmount()
    assert calls == ["mount", "unmount"]


def test_callbacks_fire_after_the_corresponding_override() -> None:
    calls: list[str] = []

    class _HookWidget(Box):
        def on_mount(self) -> None:
            super().on_mount()
            calls.append("on_mount override")

        def on_unmount(self) -> None:
            super().on_unmount()
            calls.append("on_unmount override")

    widget = _HookWidget().modifier(
        on_mount(lambda: calls.append("mount callback"))
        | on_unmount(lambda: calls.append("unmount callback"))
    )

    widget.mount(_DummyApp())
    widget.unmount()

    assert calls == [
        "on_mount override",
        "mount callback",
        "on_unmount override",
        "unmount callback",
    ]


def test_mount_callback_runs_before_children_mount() -> None:
    calls: list[str] = []

    class _ChildWidget(Box):
        def on_mount(self) -> None:
            super().on_mount()
            calls.append("child mounted")

    parent = Box(width=Sizing.fixed(100), height=Sizing.fixed(50))
    parent.add_child(_ChildWidget())
    parent.modifier(on_mount(lambda: calls.append("parent mount callback")))

    parent.mount(_DummyApp())

    assert calls == ["parent mount callback", "child mounted"]


def test_multiple_callbacks_fire_in_registration_order() -> None:
    calls: list[str] = []
    widget = _make_widget().modifier(
        on_mount(lambda: calls.append("first")) | on_mount(lambda: calls.append("second"))
    )

    widget.mount(_DummyApp())

    assert calls == ["first", "second"]


def test_registering_on_a_mounted_widget_fires_immediately() -> None:
    calls: list[str] = []
    widget = _make_widget()
    widget.mount(_DummyApp())

    widget.modifier(on_mount(lambda: calls.append("mount")))

    assert calls == ["mount"]


# --- Error containment ------------------------------------------------------


def test_exception_in_mount_callback_is_contained() -> None:
    calls: list[str] = []

    def _boom() -> None:
        raise RuntimeError("boom")

    widget = _make_widget().modifier(on_mount(_boom) | on_mount(lambda: calls.append("after")))

    widget.mount(_DummyApp())

    # The failing callback does not prevent the next one, nor the mount itself.
    assert calls == ["after"]
    assert widget._app is not None


def test_exception_in_unmount_callback_is_contained() -> None:
    calls: list[str] = []

    def _boom() -> None:
        raise RuntimeError("boom")

    widget = _make_widget().modifier(on_unmount(_boom) | on_unmount(lambda: calls.append("after")))

    widget.mount(_DummyApp())
    widget.unmount()

    assert calls == ["after"]
    assert widget._unmounted is True


# --- Re-mount ---------------------------------------------------------------


def test_callbacks_fire_again_on_remount() -> None:
    calls: list[str] = []
    widget = _make_widget().modifier(
        on_mount(lambda: calls.append("mount")) | on_unmount(lambda: calls.append("unmount"))
    )
    app = _DummyApp()

    widget.mount(app)
    widget.unmount()
    widget.mount(app)
    widget.unmount()

    assert calls == ["mount", "unmount", "mount", "unmount"]


# --- Async support ----------------------------------------------------------


@pytest.mark.asyncio
async def test_async_mount_callback_is_started_as_task() -> None:
    started = asyncio.Event()

    async def _work() -> None:
        started.set()

    widget = _make_widget().modifier(on_mount(_work))
    widget.mount(_DummyApp())

    await asyncio.wait_for(started.wait(), timeout=1.0)


@pytest.mark.asyncio
async def test_async_mount_task_is_cancelled_on_unmount() -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def _poll() -> None:
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    widget = _make_widget().modifier(on_mount(_poll))
    widget.mount(_DummyApp())

    await asyncio.wait_for(started.wait(), timeout=1.0)
    assert len(widget._mount_tasks) == 1

    widget.unmount()

    await asyncio.wait_for(cancelled.wait(), timeout=1.0)
    assert widget._mount_tasks == []


async def test_completed_async_mount_task_is_discarded(nuiitivet_mount) -> None:
    async def _work() -> None:
        return None

    widget = _make_widget().modifier(on_mount(_work))
    host = nuiitivet_mount(widget)
    host.layout(100, 50)

    # idle() runs the mount task to completion; its done callback drops it.
    await host.idle()

    assert widget._mount_tasks == []


@pytest.mark.asyncio
async def test_exception_in_async_mount_callback_is_contained() -> None:
    """Production behaviour: a raising mount callback must not kill the frame.

    Deliberately *not* on a harness. Under one the containment is the bug -- a
    handler that raised would otherwise read as one that worked -- so the
    harness re-raises from ``idle()``. Testing the containment itself therefore
    means testing it with nobody observing, which is what ``_DummyApp`` gives.
    """
    async def _boom() -> None:
        raise RuntimeError("boom")

    widget = _make_widget().modifier(on_mount(_boom))
    widget.mount(_DummyApp())

    # Awaiting the task itself, rather than guessing at a number of loop turns.
    await asyncio.gather(*list(widget._mount_tasks), return_exceptions=True)

    assert widget._mount_tasks == []


# --- Rebuild caveat ---------------------------------------------------------


def test_rebuild_remounts_freshly_built_instances() -> None:
    """A ComposableWidget rebuild mounts a new instance, so the callback runs again."""
    calls: list[str] = []

    class _Screen(ComposableWidget):
        def build(self) -> Widget:
            return _make_widget().modifier(
                on_mount(lambda: calls.append("mount")) | on_unmount(lambda: calls.append("unmount"))
            )

    screen = _Screen()
    screen.mount(_DummyApp())
    assert calls == ["mount"]

    screen.rebuild()

    # The previously built child is unmounted and a fresh one is mounted.
    assert calls == ["mount", "unmount", "mount"]
