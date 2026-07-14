"""on_mount() / on_unmount() modifiers - attach lifecycle callbacks declaratively.

These modifiers expose the widget mount/unmount lifecycle without forcing the
user to subclass a widget just to override :meth:`Widget.on_mount` /
:meth:`Widget.on_unmount`.

Unlike most modifiers they do **not** wrap the target in a new widget: the
callback is registered on the target itself and the same instance is returned,
so no extra node appears in the tree.

Usage::

    Column(...).modifier(
        on_mount(vm.start_polling) | on_unmount(vm.stop_polling)
    )

A coroutine function passed to :func:`on_mount` is started as a task when the
widget mounts and cancelled when it unmounts, which covers polling,
subscriptions and async loading::

    async def _poll() -> None:
        while True:
            await vm.refresh()
            await asyncio.sleep(5)

    Column(...).modifier(on_mount(_poll))
"""

from __future__ import annotations

from dataclasses import dataclass

from nuiitivet.widgeting.callbacks import VoidCallback
from nuiitivet.widgeting.modifier import ModifierElement
from nuiitivet.widgeting.widget import Widget


@dataclass(slots=True)
class OnMountModifier(ModifierElement):
    """Modifier that registers *callback* to run when the target widget mounts."""

    callback: VoidCallback

    def apply(self, widget: Widget) -> Widget:
        widget.add_mount_callback(self.callback)
        return widget


@dataclass(slots=True)
class OnUnmountModifier(ModifierElement):
    """Modifier that registers *callback* to run when the target widget unmounts."""

    callback: VoidCallback

    def apply(self, widget: Widget) -> Widget:
        widget.add_unmount_callback(self.callback)
        return widget


def on_mount(callback: VoidCallback) -> OnMountModifier:
    """Return a modifier that runs *callback* when the widget is mounted.

    The callback runs right after the widget's :meth:`Widget.on_mount` hook and
    before its children are mounted. Exceptions are logged and contained.

    Args:
        callback: A no-argument callable. If it is a coroutine function, it is
            started as a task on mount and cancelled on unmount.

    Returns:
        An :class:`OnMountModifier` to apply via ``widget.modifier(...)``.

    Note:
        Mount is *not* "once per logical component". A ``ComposableWidget``
        rebuild discards the built subtree and mounts freshly-created widget
        instances, so the callback runs again for the new instance. Use it for
        work tied to the widget instance's presence in the tree, not for
        one-time initialization of a component.
    """
    return OnMountModifier(callback=callback)


def on_unmount(callback: VoidCallback) -> OnUnmountModifier:
    """Return a modifier that runs *callback* when the widget is unmounted.

    The callback runs right after the widget's :meth:`Widget.on_unmount` hook
    and before its children are unmounted. Exceptions are logged and contained.

    Args:
        callback: A no-argument callable. A coroutine function is scheduled as
            a task, which may outlive the widget — prefer a synchronous
            callback for cleanup that must complete.

    Returns:
        An :class:`OnUnmountModifier` to apply via ``widget.modifier(...)``.
    """
    return OnUnmountModifier(callback=callback)


__all__ = [
    "OnMountModifier",
    "OnUnmountModifier",
    "on_mount",
    "on_unmount",
]
