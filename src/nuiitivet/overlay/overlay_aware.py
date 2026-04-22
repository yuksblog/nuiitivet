"""OverlayAware mixin for widgets that receive their OverlayHandle automatically."""

from __future__ import annotations

from typing import Generic, TypeVar

from .overlay_handle import OverlayHandle

T = TypeVar("T")


class OverlayAware(Generic[T]):
    """Mixin that lets a widget receive its own :class:`OverlayHandle`.

    When a widget inheriting ``OverlayAware`` is displayed through any
    :class:`Overlay` show API (``show_modal``, ``show_modeless``,
    ``show_light_dismiss``, ``dialog``, ``side_sheet``, ``bottom_sheet``,
    ``snackbar``, ``loading``), the framework injects the created handle
    into the widget instance before mounting. The widget (or its ViewModel)
    can then close itself via ``self.overlay_handle.close(value)`` without
    requiring the caller to wire the handle manually.

    Type parameter ``T`` represents the result type returned from
    ``handle.close(value)`` / ``await handle``. Note that the return type
    of the ``Overlay`` show APIs stays ``OverlayHandle[Any]``; only the
    widget-side view is typed.

    Example:
        >>> class MyDialog(ComposableWidget, OverlayAware[str]):
        ...     def on_save(self) -> None:
        ...         self.overlay_handle.close("saved")
        ...
        >>> result = await overlay.dialog(MyDialog())
    """

    _overlay_handle: OverlayHandle[T] | None = None

    @property
    def overlay_handle(self) -> OverlayHandle[T]:
        """Return the handle injected by the overlay framework.

        Raises:
            RuntimeError: If accessed before the widget is displayed via
                an ``Overlay`` show API.
        """
        handle = self._overlay_handle
        if handle is None:
            raise RuntimeError(
                f"{type(self).__name__}.overlay_handle is not available yet. "
                "The widget must be displayed via an Overlay show API "
                "(e.g. overlay.dialog(...)) before accessing overlay_handle."
            )
        return handle

    def _set_overlay_handle(self, handle: OverlayHandle[T]) -> None:
        """Framework-internal setter. Do not call from user code.

        Raises:
            RuntimeError: If the widget is already attached to an active
                (not-yet-completed) handle. Re-display after the previous
                handle has completed is allowed.
        """
        existing = self._overlay_handle
        if existing is not None and not existing.done():
            raise RuntimeError(
                f"{type(self).__name__} is already attached to an active OverlayHandle. "
                "Cannot display the same OverlayAware widget instance concurrently."
            )
        self._overlay_handle = handle
