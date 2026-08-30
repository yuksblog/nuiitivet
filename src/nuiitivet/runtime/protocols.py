"""Typed App and Window surfaces for ViewModels."""

from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Protocol

if TYPE_CHECKING:
    from nuiitivet.observable.protocols import ObservableBase
    from nuiitivet.theme.theme import Theme


class AppProtocol(Protocol):
    """The application surface a ViewModel depends on.

    Annotate the app a ViewModel receives with this protocol so the ViewModel
    stays independent of the runtime. Pass it per method call -- the View's
    event handler resolves ``App.of(context)`` and hands it over::

        class SettingsViewModel:
            def apply_dark_mode(self, app: AppProtocol) -> None:
                app.set_theme("dark")

    ``App.of(context)`` returns the running app typed as this protocol, and a
    hand-written fake needs only these three methods -- no widget tree and no
    event loop.
    """

    def exit(self, exit_code: int = 0) -> None:
        """Exit the application: close every window and stop the loop."""
        ...

    def set_theme(self, theme: "str | Theme") -> None:
        """Switch the app-wide theme: a registered name, ``"light"`` /
        ``"dark"``, or a :class:`~nuiitivet.theme.theme.Theme` instance."""
        ...

    def register_themes(self, themes: "dict[str, Theme]") -> None:
        """Register named themes for later :meth:`set_theme` calls by name."""
        ...


class WindowProtocol(Protocol):
    """The window surface a ViewModel depends on.

    Annotate the window a ViewModel receives with this protocol so it can
    command its window -- close it, hide it, resize it -- without holding the
    full :class:`~nuiitivet.runtime.window.Window`. Pass it per method call --
    the View's event handler resolves ``Window.of(context)`` and hands it
    over::

        class LauncherViewModel:
            def send_to_background(self, window: WindowProtocol) -> None:
                window.hide()

    ``Window.of(context)`` returns an object satisfying it, and a fake needs
    only these members. Every method is a no-op when the OS window does not
    exist (not realized yet, or already closed).
    """

    def close(self) -> None:
        """Close the window permanently."""
        ...

    def hide(self) -> None:
        """Hide the window without closing it; :meth:`show` brings it back."""
        ...

    def show(self) -> None:
        """Show the window and bring it to the front, focused."""
        ...

    def minimize(self) -> None:
        """Minimize the window."""
        ...

    def maximize(self) -> None:
        """Maximize the window."""
        ...

    def restore(self) -> None:
        """Restore the window from maximized/minimized state."""
        ...

    def full_screen(self) -> None:
        """Request full screen mode."""
        ...

    def center(self) -> None:
        """Center the window on its screen."""
        ...

    def move_to(self, x: int, y: int) -> None:
        """Move the window to a specific position."""
        ...

    def resize(self, width: int, height: int) -> None:
        """Resize the window."""
        ...

    @property
    def is_open(self) -> "ObservableBase[bool]":
        """Observable open state: ``True`` between open and close."""
        ...

    @property
    def is_visible(self) -> "ObservableBase[bool]":
        """Observable visibility: ``False`` while hidden or minimized."""
        ...

    @property
    def closed(self) -> Awaitable[None]:
        """An awaitable that resolves once the window has closed."""
        ...
