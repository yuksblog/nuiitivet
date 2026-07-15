"""Mount/unmount support for widgets."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, List, Optional

from ..common.logging_once import exception_once
from ..runtime.threading import assert_ui_thread
from .callbacks import VoidCallback, invoke_event_handler


_logger = logging.getLogger(__name__)


class LifecycleHostMixin:
    """Manages app association and lifecycle hooks."""

    _app: Any
    _mount_callbacks: List[VoidCallback]
    _unmount_callbacks: List[VoidCallback]
    _dispose_callbacks: List[Callable[[], None]]
    _mount_tasks: List["asyncio.Task[None]"]

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[override]
        super().__init__(*args, **kwargs)
        self._app = None
        self._mount_callbacks = []
        self._unmount_callbacks = []
        self._dispose_callbacks = []
        self._mount_tasks = []
        self._unmounted = False
        self._mounted = False

    # --- Lifecycle ---------------------------------------------------------
    def mount(self, app) -> None:
        if __debug__:
            assert_ui_thread()
        # Mounting is idempotent: a widget already mounted to this app must not
        # re-run its lifecycle. Providers such as ForEach add their children to
        # the child store (mounting them eagerly) and are then walked again by
        # the parent's mount loop; without this guard every such child would
        # fire on_mount twice. (``app`` may legitimately be None, so a dedicated
        # flag rather than ``_app`` tracks whether we are already mounted.)
        if self._mounted and self._app is app:
            return
        self._unmounted = False
        self._mounted = True
        self._app = app
        self._safe_call(self.on_mount)
        for callback in list(self._mount_callbacks):
            self._invoke_mount_callback(callback)
        for child in self._safe_children_snapshot():
            self._safe_call(child.mount, app)

    def unmount(self) -> None:
        if __debug__:
            assert_ui_thread()
        if self._unmounted:
            return
        # Call parent's on_unmount first
        self._safe_call(self.on_unmount)
        # Then the registered unmount callbacks. Unlike dispose callbacks these
        # persist, so they fire again if the widget is re-mounted and unmounted.
        for callback in list(self._unmount_callbacks):
            invoke_event_handler(
                callback,
                error_key="widget_lifecycle_unmount_callback",
                error_msg="Exception in unmount callback",
                owner_name=type(self).__name__,
            )
        # Call dispose callbacks (one-shot)
        for dispose_callback in self._dispose_callbacks:
            try:
                dispose_callback()
            except Exception:
                exception_once(
                    _logger,
                    "widget_lifecycle_dispose_callback_exc",
                    "Exception in dispose callback: callback=%r",
                    dispose_callback,
                )
        self._dispose_callbacks.clear()
        # Cancel any still-running async mount callbacks
        self._cancel_mount_tasks()
        # Then unmount children
        for child in self._safe_children_snapshot():
            self._safe_call(child.unmount)
        manager = self._pointer_capture_manager()
        if manager is not None:
            try:
                manager.cancel_all_for(self)
            except Exception:
                exception_once(
                    _logger,
                    "widget_lifecycle_cancel_all_for_exc",
                    "Exception while canceling pointer captures for widget",
                )
        self._app = None
        self._unmounted = True
        self._mounted = False

    def on_mount(self) -> None:  # pragma: no cover - default no-op
        return None

    def on_unmount(self) -> None:  # pragma: no cover - default no-op
        return None

    # --- Callback registration ---------------------------------------------
    def add_mount_callback(self, callback: VoidCallback) -> None:
        """Register a callback to be invoked when this widget is mounted.

        The callback runs during ``mount()``, right after :meth:`on_mount` and
        before children are mounted. A coroutine function is started as a task
        that is cancelled when the widget unmounts.

        Registering after the widget is already mounted invokes the callback
        immediately, so that modifiers applied to a live widget still fire.

        Args:
            callback: A no-argument callable, sync or async.
        """
        self._mount_callbacks.append(callback)
        if self._app is not None and not self._unmounted:
            self._invoke_mount_callback(callback)

    def add_unmount_callback(self, callback: VoidCallback) -> None:
        """Register a callback to be invoked when this widget is unmounted.

        The callback runs during ``unmount()``, after :meth:`on_unmount` and
        before children are unmounted. A coroutine function is scheduled as a
        task, which may outlive the widget — prefer a synchronous callback for
        cleanup that must complete.

        Args:
            callback: A no-argument callable, sync or async.
        """
        self._unmount_callbacks.append(callback)

    def on_dispose(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when this widget is disposed.

        The callback will be invoked during unmount(), after on_unmount() is called
        but before children are unmounted. This is useful for cleaning up resources
        when the widget is being removed from the tree.

        Args:
            callback: A function to call when the widget is disposed.
                     Should take no arguments and return None.

        Example:
            def cleanup():
                print("Widget is being disposed")

            widget.on_dispose(cleanup)
        """
        self._dispose_callbacks.append(callback)

    # --- Helpers -----------------------------------------------------------
    def _invoke_mount_callback(self, callback: VoidCallback) -> None:
        task = invoke_event_handler(
            callback,
            error_key="widget_lifecycle_mount_callback",
            error_msg="Exception in mount callback",
            owner_name=type(self).__name__,
        )
        if task is None:
            return
        self._mount_tasks.append(task)
        task.add_done_callback(self._discard_mount_task)

    def _discard_mount_task(self, task: "asyncio.Task[None]") -> None:
        try:
            self._mount_tasks.remove(task)
        except ValueError:
            pass

    def _cancel_mount_tasks(self) -> None:
        for task in list(self._mount_tasks):
            if not task.done():
                task.cancel()
        self._mount_tasks.clear()

    def _safe_call(self, func, *args, **kwargs) -> Optional[Any]:
        try:
            return func(*args, **kwargs)
        except Exception:
            name = getattr(func, "__name__", "<unknown>")
            exception_once(
                _logger,
                f"widget_lifecycle_safe_call_exc:{name}",
                "Exception in lifecycle hook: %s",
                name,
            )
            return None

    def _safe_children_snapshot(self):
        snapshot_fn = getattr(self, "children_snapshot", None)
        if callable(snapshot_fn):
            try:
                return list(snapshot_fn())
            except Exception:
                exception_once(
                    _logger,
                    "widget_lifecycle_children_snapshot_exc",
                    "Exception while taking children snapshot",
                )
                return []
        return []

    def _pointer_capture_manager(self):  # pragma: no cover - helper
        app = getattr(self, "_app", None)
        if app is None:
            return None
        return getattr(app, "_pointer_capture_manager", None)
