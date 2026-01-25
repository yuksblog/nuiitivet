"""Mount/unmount support for widgets."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

from ..common.logging_once import exception_once
from ..runtime.threading import assert_ui_thread


_logger = logging.getLogger(__name__)


class LifecycleHostMixin:
    """Manages app association and lifecycle hooks."""

    _app: Any
    _dispose_callbacks: List[Callable[[], None]]

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[override]
        super().__init__(*args, **kwargs)
        self._app = None
        self._dispose_callbacks = []
        self._unmounted = False

    # --- Lifecycle ---------------------------------------------------------
    def mount(self, app) -> None:
        if __debug__:
            assert_ui_thread()
        self._unmounted = False
        self._app = app
        self._safe_call(self.on_mount)
        for child in self._safe_children_snapshot():
            self._safe_call(child.mount, app)

    def unmount(self) -> None:
        if __debug__:
            assert_ui_thread()
        if self._unmounted:
            return
        # Call parent's on_unmount first
        self._safe_call(self.on_unmount)
        # Call dispose callbacks
        for callback in self._dispose_callbacks:
            try:
                callback()
            except Exception:
                exception_once(
                    _logger,
                    "widget_lifecycle_dispose_callback_exc",
                    "Exception in dispose callback: callback=%r",
                    callback,
                )
        self._dispose_callbacks.clear()
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

    def on_mount(self) -> None:  # pragma: no cover - default no-op
        return None

    def on_unmount(self) -> None:  # pragma: no cover - default no-op
        return None

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
