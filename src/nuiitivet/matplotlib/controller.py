"""matplotlib's navigation for a figure shown by a MatplotlibFigure: pan, zoom and view history, with no widget."""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Any, Optional, cast

from matplotlib.backend_bases import MouseEvent, NavigationToolbar2, _Mode

from nuiitivet.observable import State

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from nuiitivet.matplotlib.figure import MatplotlibFigure

#: The scale one wheel step zooms by; three steps double it.
_WHEEL_ZOOM_STEP = 1.25

#: The controller of each figure that has one; the figure outlives the widgets that show it.
_CONTROLLERS: "weakref.WeakKeyDictionary[Figure, MatplotlibController]" = weakref.WeakKeyDictionary()

#: The widget showing each figure now; a controller made after the widget attaches to it.
_WIDGETS: "weakref.WeakKeyDictionary[Figure, weakref.ref[MatplotlibFigure]]" = weakref.WeakKeyDictionary()


class MatplotlibController(NavigationToolbar2):
    """matplotlib's navigation for a figure, driven from the app's own buttons.

    Made beside the figure, as a :class:`ScrollController` is made beside a
    scrollable; the :class:`MatplotlibFigure` that shows the figure finds it.
    ``home()``, ``back()``, ``forward()``, ``pan()`` and ``zoom()`` are
    matplotlib's ``NavigationToolbar2``'s; call them from any button. Pan and
    the zoom rectangle take the left button, the right button zooms out, and
    ``x`` or ``y`` held limits either to one axis. The wheel zooms the axes
    under the pointer, around it. A ``picker`` is quiet while pan or zoom is
    on, as in matplotlib.

    The controller has no widgets; it talks through States instead.
    ``panning`` and ``zooming`` are the two tools' switches: a toggle button
    bound to one turns the tool on and off, and deselects when the other
    tool is turned on. ``can_back`` and ``can_forward`` enable the history
    buttons, ``message`` is the pointer's data coordinates.

    A figure has one controller, kept across the widgets that show the
    figure, as a rebuild makes a new one, with the view history. The
    controller is made before or after the widget.
    """

    @classmethod
    def of_figure(cls, figure: "Figure") -> Optional["MatplotlibController"]:
        """The controller made for *figure*, or ``None``."""
        return _CONTROLLERS.get(figure)

    @classmethod
    def _shown(cls, figure: "Figure", widget: "MatplotlibFigure") -> None:
        """*widget* shows *figure* now; its controller, made already or later, serves the widget."""
        _WIDGETS[figure] = weakref.ref(widget)
        controller = _CONTROLLERS.get(figure)
        if controller is not None:
            controller._attach(widget)

    def __init__(self, figure: "Figure") -> None:
        """Initialize a MatplotlibController for *figure*.

        Args:
            figure: The figure navigated; it is shown by a :class:`MatplotlibFigure`.

        Raises:
            ValueError: *figure* has a controller already.
        """
        if figure in _CONTROLLERS:
            raise ValueError("the figure has a MatplotlibController already")
        self._widget: Optional["MatplotlibFigure"] = None
        #: Whether the pan tool is on; writable.
        self.panning: State[bool] = State(False)
        #: Whether the zoom-rectangle tool is on; writable.
        self.zooming: State[bool] = State(False)
        #: Whether ``back()`` has a view to go to.
        self.can_back: State[bool] = State(False)
        #: Whether ``forward()`` has a view to go to.
        self.can_forward: State[bool] = State(False)
        #: The pointer's data coordinates as matplotlib formats them, ``""`` outside the axes.
        self.message: State[str] = State("")
        _CONTROLLERS[figure] = self
        super().__init__(figure.canvas)
        self.canvas.mpl_connect("scroll_event", self._wheel_zoom)
        self.panning.subscribe(lambda on: self._switch(_Mode.PAN, on))
        self.zooming.subscribe(lambda on: self._switch(_Mode.ZOOM, on))
        shown = _WIDGETS.get(figure)
        widget = shown() if shown is not None else None
        if widget is not None:
            self._attach(widget)

    def _attach(self, widget: "MatplotlibFigure") -> None:
        """Serve *widget*, which shows the figure now; the connections and the history stay."""
        self._widget = widget
        self.canvas = widget.figure.canvas
        self.canvas.toolbar = self
        if self.mode != _Mode.NONE:
            self.canvas.widgetlock(self)

    def pan(self, *args: Any) -> None:
        """Toggle the pan tool."""
        super().pan(*args)
        self._sync_mode()

    def zoom(self, *args: Any) -> None:
        """Toggle the zoom-rectangle tool."""
        super().zoom(*args)
        self._sync_mode()

    def _sync_mode(self) -> None:
        self.panning.value = self.mode == _Mode.PAN
        self.zooming.value = self.mode == _Mode.ZOOM

    def _switch(self, mode: _Mode, on: bool) -> None:
        """Turn the tool of *mode* on or off to match its State, written from outside."""
        if bool(on) != (self.mode == mode):
            if mode == _Mode.PAN:
                self.pan()
            else:
                self.zoom()

    def set_message(self, s: str) -> None:
        self.message.value = s

    def set_history_buttons(self) -> None:
        # The view stack is matplotlib's private cursor-and-list; its Qt toolbar reads the same two fields.
        stack = cast(Any, self)._nav_stack
        self.can_back.value = stack._pos > 0
        self.can_forward.value = stack._pos < len(stack) - 1

    def draw_rubberband(self, event: Any, x0: float, y0: float, x1: float, y1: float) -> None:
        if self._widget is not None:
            self._widget._set_rubberband((x0, y0, x1, y1))

    def remove_rubberband(self) -> None:
        if self._widget is not None:
            self._widget._set_rubberband(None)

    def _wheel_zoom(self, event: Any) -> None:
        if not isinstance(event, MouseEvent) or not event.step or event.x is None or event.y is None:
            return
        if not self.canvas.widgetlock.available(self):
            return
        axes = cast(Any, self)._start_event_axes_interaction(event, method="zoom")
        if not axes:
            return
        scale = _WHEEL_ZOOM_STEP ** float(event.step)
        mode: Optional[str] = event.key if event.key in ("x", "y") else None
        for i, ax in enumerate(axes):
            # A twin shares one axis with an earlier one of the list; that axis is zoomed once.
            twinx = any(ax.get_shared_x_axes().joined(ax, prev) for prev in axes[:i])
            twiny = any(ax.get_shared_y_axes().joined(ax, prev) for prev in axes[:i])
            cast(Any, ax)._set_view_from_bbox((event.x, event.y, scale), mode=mode, twinx=twinx, twiny=twiny)
        self.canvas.draw_idle()
        self.push_current()


__all__ = ["MatplotlibController"]
