"""The application runtime: theme, event loop, exit policy, and windows.

``App`` owns no pixels of its own. Every per-window concern — the widget
tree, overlay, navigator, focus, rendering, the menu bar — lives on
:class:`~nuiitivet.runtime.window.Window`; the App is the process-wide
runtime that runs the loop, supplies the theme, dispatches app-scoped
intents, and decides when the application exits.
The window is constructed separately and passed in:
``App(Window(content=...))``. See ``docs/design/APP_WINDOW.md``.
"""

from __future__ import annotations

import logging
import weakref
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

from nuiitivet.common.logging_once import exception_once
from nuiitivet.platform.tray import TrayIcon
from nuiitivet.theme.manager import ThemeManager
from nuiitivet.theme.plain_theme import PlainTheme
from ..widgeting.context_lookup import find_provider, raise_if_premature_lookup
from ..widgeting.widget import Widget
from .renderer import RendererMode, parse_renderer_mode
from .window import Window

if TYPE_CHECKING:
    from nuiitivet.theme.theme import Theme


logger = logging.getLogger(__name__)


class ExitPolicy(Enum):
    """When ``App.run()`` returns.

    Attributes:
        LAST_WINDOW_CLOSED: The default — the app exits once no window
            remains open.
        MAIN_WINDOW_CLOSED: Closing the main window closes every other
            window and exits, regardless of what else is open.
        EXPLICIT: Only ``ExitAppIntent`` (or ``app.exit()``) exits; the app
            keeps running with zero open windows, so some window must be
            reopenable from app-held state.
    """

    LAST_WINDOW_CLOSED = "last_window_closed"
    MAIN_WINDOW_CLOSED = "main_window_closed"
    EXPLICIT = "explicit"


class AppProxy:
    """Proxy for interacting with the App instance from the widget tree.

    This class provides a restricted interface to the App instance, primarily
    for dispatching app-scoped intents.
    """

    def __init__(self, app: "App") -> None:
        self._app = weakref.ref(app)

    def dispatch(self, intent: Any) -> None:
        """Dispatch an app-scoped intent to the application."""
        app = self._app()
        if app is not None:
            app.dispatch(intent)


class AppScope(Widget):
    """Inherited widget that provides access to the App instance.

    Also the theme provider: ``Theme.of`` resolves against the nearest one of
    these. Theme changes are fanned out by the App itself (which owns the
    :class:`ThemeManager`) to every open window; this scope only serves reads.
    """

    def __init__(self, app: "App", child: Widget) -> None:
        super().__init__()
        self.app_proxy = AppProxy(app)
        self.theme_manager = app._theme_manager
        self._app_ref = weakref.ref(app)
        self.add_child(child)

    @property
    def app(self) -> Optional["App"]:
        """The App this scope belongs to, or ``None`` once it has been collected.

        The App-scoped half of ``X.of(context)`` resolves through here — see
        :func:`nuiitivet.widgeting.context_lookup.find_app`.
        """
        return self._app_ref()

    def layout(self, width: int, height: int) -> None:
        super().layout(width, height)
        for child in self.children:
            child.layout(width, height)
            child.set_layout_rect(0, 0, width, height)


class App:
    """The application runtime.

    Takes its main :class:`Window` as the first argument —
    ``App(Window(content=...))`` — plus the app-level options ``theme`` and
    ``exit_policy``. Window-flavored options (``title``, ``width``, ``menu``,
    ...) belong to the :class:`Window`. Secondary windows are constructed
    with ``Window(...)`` and shown with ``window.open()`` while the app runs.
    """

    def __init__(
        self,
        window: Window,
        *,
        theme: Optional[Any] = None,
        exit_policy: ExitPolicy = ExitPolicy.LAST_WINDOW_CLOSED,
        tray: Optional[TrayIcon] = None,
    ):
        """Initialize the App (and open its main window).

        Args:
            window: The main :class:`Window`.
            theme: Theme to install, app-wide.
            exit_policy: When :meth:`run` returns; see :class:`ExitPolicy`.
            tray: A :class:`~nuiitivet.platform.tray.TrayIcon` to show while
                the app runs. Installed when :meth:`run` starts, removed when
                it returns; see :attr:`TrayIcon.installed` for whether the
                platform actually showed it.
        """
        if not isinstance(window, Window):
            raise TypeError(
                "App() takes a Window as its first argument; wrap the content "
                "in one: App(Window(content=...))."
            )

        if theme is None:
            theme = PlainTheme.light()
        self._theme_manager = ThemeManager(initial=theme)
        self._theme_manager.on_change = self._on_theme_changed
        self._theme_registry: dict[str, Any] = {}

        self.exit_policy = exit_policy
        if tray is not None and not isinstance(tray, TrayIcon):
            raise TypeError("App(tray=...) takes a TrayIcon.")
        self._tray = tray
        self._windows: list[Window] = []
        self._main_window: Window | None = None
        # Set by the running backend so a Window opened mid-run gets its OS
        # window immediately; ``None`` before run() (open() then only builds
        # the tree, and run() realizes every open window).
        self._realize_window_hook: Optional[Callable[[Window], None]] = None
        # Dev-only seam: the dev runner installs per-window instrumentation
        # (inspect mode, interaction recorder) through this; it runs once for
        # every window as it registers. ``None`` in production.
        self._instrument_window_hook: Optional[Callable[[Window], None]] = None
        # Dev-only seam, the counterpart of ``_instrument_window_hook``: runs
        # once for every tracked window as it unregisters, whatever the close
        # path (OS close, ``close()``, parent cascade). ``None`` in production.
        self._unregister_window_hook: Optional[Callable[[Window], None]] = None
        self._event_loop: Any = None
        self._preferred_draw_fps: Optional[float] = None
        self._exiting = False
        self._exit_code = 0

        global _current_app_ref
        _current_app_ref = weakref.ref(self)

        self._main_window = window
        window._attach_app(self)
        window.open()

    # --- Windows -------------------------------------------------------

    @property
    def main_window(self) -> Window:
        """The main window (see :class:`ExitPolicy.MAIN_WINDOW_CLOSED`)."""
        window = self._main_window
        if window is None:
            raise RuntimeError("App has no main window.")
        return window

    @property
    def windows(self) -> tuple[Window, ...]:
        """A snapshot of the currently open windows, in open order."""
        return tuple(self._windows)

    def _register_window(self, window: Window) -> None:
        """Track an opened window; realize it at once when the loop runs."""
        if window not in self._windows:
            self._windows.append(window)
            instrument = self._instrument_window_hook
            if instrument is not None:
                try:
                    instrument(window)
                except Exception:
                    exception_once(logger, "app_instrument_window_exc", "Window instrumentation raised")
        hook = self._realize_window_hook
        if hook is not None:
            try:
                hook(window)
            except Exception:
                exception_once(logger, "app_realize_window_exc", "Realizing an opened window raised")

    def _unregister_window(self, window: Window) -> None:
        """Untrack a closed window and apply the exit policy."""
        try:
            self._windows.remove(window)
        except ValueError:
            pass
        else:
            hook = self._unregister_window_hook
            if hook is not None:
                try:
                    hook(window)
                except Exception:
                    exception_once(logger, "app_unregister_window_exc", "Window unregistration hook raised")
        if self._exiting:
            return
        if self.exit_policy is ExitPolicy.MAIN_WINDOW_CLOSED and window is self._main_window:
            self.exit()
        elif self.exit_policy is not ExitPolicy.EXPLICIT and not self._windows:
            self._stop_loop()

    # --- Context lookup ------------------------------------------------

    @staticmethod
    def of(context: Widget) -> AppProxy:
        """Get the AppProxy for the given context.

        Args:
            context: The widget context.

        Returns:
            The AppProxy instance.

        Raises:
            RuntimeError: If called before ``context`` is mounted (typically from
                ``__init__``), or if the widget is not attached to an App.
        """
        scope = find_provider(context, AppScope)
        if scope is None:
            raise_if_premature_lookup("App.of", context)
            raise RuntimeError("AppScope not found. Is the widget attached to an App?")
        return scope.app_proxy

    # --- Theme ---------------------------------------------------------

    def _on_theme_changed(self, _theme: "Theme") -> None:
        """Fan a theme change out to every open window.

        Widgets do not subscribe to the theme; they read it, and the read
        registers a dependency that is invalidated here, per window. See
        ``nuiitivet/theme/dependency.py``.
        """
        from nuiitivet.theme.dependency import invalidate_theme_readers

        for window in list(self._windows):
            root = window.root
            if root is not None:
                try:
                    invalidate_theme_readers(root)
                except Exception:
                    exception_once(logger, "app_theme_invalidate_readers_exc", "invalidate_theme_readers raised")
            # The window's clear colour is the Window's own, not a widget's, so
            # nothing marked it as a reader; refresh it when it is token-based.
            try:
                if window._background_uses_theme():
                    window._update_background_color()
            except Exception:
                exception_once(logger, "app_theme_background_exc", "Background update raised on theme change")
            try:
                window.invalidate()
            except Exception:
                exception_once(logger, "app_theme_invalidate_exc", "Window.invalidate raised on theme change")

    # --- Intents -------------------------------------------------------

    def dispatch(self, intent: Any) -> None:
        """Dispatch an app-scoped intent.

        Only app-scoped intents are accepted (``ExitAppIntent`` and the theme
        intents). A window-scoped intent here is a scope error and raises
        rather than being silently misdelivered; dispatch those through
        ``Window.of(context).dispatch(...)``. See ``docs/design/APP_WINDOW.md``.
        """
        from nuiitivet.theme.intents import ThemeModeIntent, ThemeRegistryIntent

        if isinstance(intent, ThemeRegistryIntent):
            self._theme_registry.update(intent.themes)
            return

        if isinstance(intent, ThemeModeIntent):
            from nuiitivet.theme.theme import Theme

            theme_val = intent.theme
            if isinstance(theme_val, Theme):
                self._theme_manager.set_theme(theme_val)
            else:
                # Look up by name; fall back to light/dark built-ins
                theme_obj = self._theme_registry.get(str(theme_val))
                if theme_obj is None:
                    if str(theme_val) == "dark":
                        theme_obj = PlainTheme.dark()
                    else:
                        theme_obj = PlainTheme.light()
                self._theme_manager.set_theme(theme_obj)
            return

        from nuiitivet.runtime.intents import ExitAppIntent

        if isinstance(intent, ExitAppIntent):
            self.exit(intent.exit_code)
            return

        from nuiitivet.runtime.window_intents import (
            CenterWindowIntent,
            CloseWindowIntent,
            FullScreenIntent,
            MaximizeWindowIntent,
            MinimizeWindowIntent,
            MoveWindowIntent,
            ResizeWindowIntent,
            RestoreWindowIntent,
        )

        if isinstance(
            intent,
            (
                CenterWindowIntent,
                CloseWindowIntent,
                FullScreenIntent,
                MaximizeWindowIntent,
                MinimizeWindowIntent,
                MoveWindowIntent,
                ResizeWindowIntent,
                RestoreWindowIntent,
            ),
        ):
            raise TypeError(
                f"{type(intent).__name__} is a window-scoped intent; dispatch it "
                "through Window.of(context).dispatch(...)."
            )

        raise TypeError(f"App.dispatch() does not handle {type(intent).__name__}.")

    # --- Lifecycle -----------------------------------------------------

    def exit(self, exit_code: int = 0) -> None:
        """Exit the application: close every window, then stop the loop."""
        if self._exiting:
            return
        self._exiting = True
        self._exit_code = int(exit_code)
        try:
            for window in list(reversed(self._windows)):
                try:
                    window.close()
                except Exception:
                    exception_once(logger, "app_exit_close_window_exc", "Closing a window on exit raised")
        finally:
            self._stop_loop()

    @property
    def tray(self) -> Optional[TrayIcon]:
        """The registered tray icon, or ``None``."""
        return self._tray

    def _install_tray(self) -> None:
        """Backend hook: install the tray icon once the loop is up."""
        if self._tray is not None:
            self._tray._install(self)

    def _uninstall_tray(self) -> None:
        """Backend hook: remove the tray icon when the loop stops."""
        if self._tray is not None:
            self._tray._uninstall()

    def _visible_window_count(self) -> int:
        """How many open windows are currently visible (hidden ones excluded)."""
        return sum(
            1
            for w in self._windows
            if w._lifecycle_state == "open" and bool(w.is_visible.value)
        )

    def _window_visibility_changed(self) -> None:
        """A window was shown, hidden, opened, or closed.

        Feeds the tray's ``dock_visibility="auto"`` policy (macOS: Dock icon
        only while some window is visible).
        """
        if self._tray is not None:
            self._tray._refresh_dock(self._visible_window_count())

    def _stop_loop(self) -> None:
        import sys

        # Never *imports* the backend: if pyglet was never loaded there is no
        # loop to stop (offscreen rendering, tests).
        if "pyglet" not in sys.modules:
            return
        try:
            import pyglet

            pyglet.app.exit()
        except ImportError:
            pass
        except Exception:
            exception_once(logger, "app_exit_exc", "Failed to exit application")

    def set_draw_fps(self, fps: Optional[float]) -> None:
        """Update the preferred draw FPS for the interactive loop."""
        if fps is not None:
            try:
                fps = float(fps)
            except Exception:
                raise ValueError("fps must be convertible to float or None") from None
            if fps <= 0:
                fps = None
        self._preferred_draw_fps = fps
        loop = self._event_loop
        if loop is not None:
            try:
                loop.set_draw_fps(fps)
            except Exception:
                exception_once(logger, "app_set_draw_fps_exc", "Event loop set_draw_fps raised")

    def render_to_png(self, path: str) -> None:
        """Render the main window to a PNG file (the headless counterpart of
        :meth:`run`; other windows render through their own
        :meth:`Window.render_to_png`)."""
        self.main_window.render_to_png(path)

    def run(self, draw_fps: Optional[float] = None, *, renderer: RendererMode = "auto"):
        """Run the application using the pyglet backend.

        Realizes an OS window for every open :class:`Window`, runs the event
        loop, and returns when the exit policy says so (see
        :class:`ExitPolicy`).

        Args:
            draw_fps: Upper-bound frame-rate throttle. ``None`` (the default)
                draws purely on demand — a clean widget tree produces zero
                frames. A positive value caps the frame rate but still only
                draws when something has invalidated; it is a throttle, not a
                mandate to draw every frame.
            renderer: Renderer selection.

                - ``"auto"`` (default): try the GPU and silently fall back to
                  software (raster) rendering when it is unavailable.
                - ``"gpu"``: require the GPU; raise ``RuntimeError`` if the GPU
                  backend cannot be initialized or a GPU frame fails to render.
                - ``"cpu"``: always render in software; the GPU is never touched.

                For GPU-less, software-GL, or remote environments (with a
                display) prefer ``"cpu"``. Truly headless environments cannot
                use ``run()`` at all — render offscreen via
                :meth:`render_to_png`.

        When launched under ``python -m nuiitivet.dev`` (hot reload), this
        method does **not** block. It hands the App and the main window's root
        factory to the active dev session and returns; the dev runner then
        drives the real event loop, file watching, and reloads. In production
        (no dev session) it blocks on the pyglet loop as usual.
        """

        resolved_renderer = parse_renderer_mode(renderer)

        # Hot-reload handoff: if the dev runner installed a session, give it the
        # App + factory and return without blocking. See nuiitivet.dev.
        try:
            from nuiitivet.dev import current_dev_session
        except Exception:
            current_dev_session = None  # type: ignore[assignment]
        if current_dev_session is not None:
            session = current_dev_session()
            if session is not None:
                session.attach(
                    app=self,
                    root_factory=self.main_window._root_factory,
                    draw_fps=draw_fps,
                    renderer=resolved_renderer,
                )
                return

        from ..backends.pyglet.runner import run_app

        run_app(self, draw_fps=draw_fps, renderer=resolved_renderer)


# Process-global current App, resolved by ``Window.open()`` for windows that
# were constructed standalone. One App per process is the operating
# assumption; a newer App simply supersedes an older one (tests construct
# many Apps sequentially).
_current_app_ref: "weakref.ref[App] | None" = None


def current_app() -> Optional[App]:
    """Return the most recently constructed App, or ``None``."""
    ref = _current_app_ref
    return ref() if ref is not None else None
