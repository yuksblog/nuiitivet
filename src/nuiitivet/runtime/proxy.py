"""What ``App.proxy(widget)`` and ``Window.proxy(widget)`` return."""

from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable

from nuiitivet.observable import State
from nuiitivet.platform.badge import BadgeValue

from ..widgeting.context_lookup import ContextProxy
from .protocols import AppProtocol, WindowProtocol

if TYPE_CHECKING:
    from nuiitivet.observable.protocols import MutableStateBase, StateBase
    from nuiitivet.theme.theme import Theme


async def _already_closed() -> None:
    return None


class AppProxy(ContextProxy[AppProtocol]):
    """Forwards :class:`~nuiitivet.runtime.protocols.AppProtocol` to the app of one widget.

    After the widget is unmounted, calls go to the app it was mounted in.
    """

    def exit(self, exit_code: int = 0) -> None:
        """Exit the application: close every window and stop the loop."""
        app = self._provider()
        if app is not None:
            app.exit(exit_code)

    def set_theme(self, theme: "str | Theme") -> None:
        """Switch the app-wide theme: a registered name, ``"light"`` /
        ``"dark"``, or a :class:`~nuiitivet.theme.theme.Theme` instance."""
        app = self._provider()
        if app is not None:
            app.set_theme(theme)

    def register_themes(self, themes: "dict[str, Theme]") -> None:
        """Register named themes for later :meth:`set_theme` calls by name."""
        app = self._provider()
        if app is not None:
            app.register_themes(themes)

    @property
    def badge(self) -> "MutableStateBase[BadgeValue]":
        """The badge on the app's Dock or taskbar icon: a count, a short
        text, or ``None`` for no badge."""
        app = self._provider()
        if app is None:
            return State(None)
        return app.badge


class WindowProxy(ContextProxy[WindowProtocol]):
    """Forwards :class:`~nuiitivet.runtime.protocols.WindowProtocol` to the window of one widget.

    After the widget is unmounted, calls go to the window it was mounted in.
    """

    def close(self) -> None:
        """Close the window permanently."""
        window = self._provider()
        if window is not None:
            window.close()

    def hide(self) -> None:
        """Hide the window without closing it; :meth:`show` brings it back."""
        window = self._provider()
        if window is not None:
            window.hide()

    def show(self) -> None:
        """Show the window and bring it to the front, focused."""
        window = self._provider()
        if window is not None:
            window.show()

    def minimize(self) -> None:
        """Minimize the window."""
        window = self._provider()
        if window is not None:
            window.minimize()

    def maximize(self) -> None:
        """Maximize the window."""
        window = self._provider()
        if window is not None:
            window.maximize()

    def restore(self) -> None:
        """Restore the window from maximized/minimized state."""
        window = self._provider()
        if window is not None:
            window.restore()

    def full_screen(self) -> None:
        """Request full screen mode."""
        window = self._provider()
        if window is not None:
            window.full_screen()

    def center(self) -> None:
        """Center the window on its screen."""
        window = self._provider()
        if window is not None:
            window.center()

    def move_to(self, x: int, y: int) -> None:
        """Move the window to a specific position."""
        window = self._provider()
        if window is not None:
            window.move_to(x, y)

    def resize(self, width: int, height: int) -> None:
        """Resize the window."""
        window = self._provider()
        if window is not None:
            window.resize(width, height)

    @property
    def is_open(self) -> "StateBase[bool]":
        """State open state: ``True`` between open and close."""
        window = self._provider()
        if window is None:
            return State(False)
        return window.is_open

    @property
    def is_visible(self) -> "StateBase[bool]":
        """State visibility: ``False`` while hidden or minimized."""
        window = self._provider()
        if window is None:
            return State(False)
        return window.is_visible

    @property
    def closed(self) -> Awaitable[None]:
        """An awaitable that resolves once the window has closed."""
        window = self._provider()
        if window is None:
            return _already_closed()
        return window.closed
