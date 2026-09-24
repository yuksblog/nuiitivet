"""A live overlay entry stays mounted while other entries open and close."""

from __future__ import annotations

from nuiitivet.overlay import Overlay
from nuiitivet.widgeting.widget import Widget


class _LifecycleCounter(Widget):
    def __init__(self) -> None:
        super().__init__(width=20, height=20)
        self.mount_count = 0
        self.unmount_count = 0

    def on_mount(self) -> None:
        self.mount_count += 1
        super().on_mount()

    def on_unmount(self) -> None:
        self.unmount_count += 1
        super().on_unmount()

    def build(self) -> Widget:
        return self


def test_showing_an_entry_leaves_the_others_mounted(nuiitivet_mount) -> None:
    overlay = Overlay()
    host = nuiitivet_mount(overlay)
    host.layout(400, 300)

    first = _LifecycleCounter()
    second = _LifecycleCounter()
    overlay.show(first, passthrough=True)
    overlay.show(second, passthrough=True)
    host.settle()

    assert (first.mount_count, first.unmount_count) == (1, 0)
    assert (second.mount_count, second.unmount_count) == (1, 0)


def test_closing_an_entry_leaves_the_others_mounted(nuiitivet_mount) -> None:
    overlay = Overlay()
    host = nuiitivet_mount(overlay)
    host.layout(400, 300)

    first = _LifecycleCounter()
    second = _LifecycleCounter()
    third = _LifecycleCounter()
    overlay.show(first, passthrough=True)
    second_handle = overlay.show(second, passthrough=True)
    overlay.show(third, passthrough=True)
    host.settle()

    second_handle.close()
    host.settle()

    assert (second.mount_count, second.unmount_count) == (1, 1)
    assert (first.mount_count, first.unmount_count) == (1, 0)
    assert (third.mount_count, third.unmount_count) == (1, 0)
    assert [entry.content for entry in overlay.open_entries] == [first, third]
