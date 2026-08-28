"""Dev session: the handoff object between ``App.run()`` and the hot-reload runner.

When the app is launched via ``python -m nuiitivet.dev``, the runner installs a
process-global :class:`DevSession` *before* importing the user's app module. The
user's unmodified ``main()`` then calls :meth:`App.run`, which detects the active
session and — instead of blocking on the pyglet loop — hands the ``App`` and its
root factory to the session and returns. Control returns to the runner, which
owns the real event loop, the file watcher, and the reload sequence.

This inversion is what lets a single ``app.py`` serve both ``python -m yourapp``
(normal, blocking run) and ``python -m nuiitivet.dev run yourapp/app.py`` (hot
reload) with no dev/prod branching in user code. See ``docs/design/HOT_RELOAD.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nuiitivet.runtime.app import App
    from nuiitivet.runtime.window import RootFactory
    from nuiitivet.runtime.renderer import RendererMode


class DevSession:
    """Handoff state captured when the user's ``App.run()`` is called under dev.

    A session is single-shot: exactly one ``App`` is expected to attach during a
    dev run (the one built by the user's ``main()``). Attaching is idempotent for
    the same app but a second, different app is a usage error.
    """

    def __init__(self) -> None:
        self._app: Optional["App"] = None
        self._root_factory: Optional["RootFactory"] = None
        self._draw_fps: Optional[float] = None
        self._renderer: "RendererMode" = "auto"
        self._attached: bool = False

    @property
    def attached(self) -> bool:
        """True once an ``App`` has handed itself off via :meth:`attach`."""
        return self._attached

    @property
    def app(self) -> Optional["App"]:
        """The attached ``App``, or ``None`` before :meth:`attach`."""
        return self._app

    @property
    def root_factory(self) -> Optional["RootFactory"]:
        """The root factory captured from the attached ``App``."""
        return self._root_factory

    @property
    def draw_fps(self) -> Optional[float]:
        """The ``draw_fps`` the user passed to ``App.run()``."""
        return self._draw_fps

    @property
    def renderer(self) -> "RendererMode":
        """The renderer mode the user passed to ``App.run()``."""
        return self._renderer

    def attach(
        self,
        *,
        app: "App",
        root_factory: "RootFactory",
        draw_fps: Optional[float],
        renderer: "RendererMode",
    ) -> None:
        """Capture the app + run parameters so the runner can drive the loop.

        Called from :meth:`App.run` when a dev session is active. Does not start
        the loop; the runner does that after ``main()`` returns.

        Args:
            app: The ``App`` the user built in ``main()``.
            root_factory: The app's root factory (re-invoked on reload).
            draw_fps: The draw-rate throttle the user requested.
            renderer: The resolved renderer mode.

        Raises:
            RuntimeError: If a *different* app tries to attach to an already
                attached session.
        """
        if self._attached and self._app is not app:
            raise RuntimeError(
                "A dev session already has an App attached. Only one App.run() "
                "is supported under 'python -m nuiitivet.dev'."
            )
        self._app = app
        self._root_factory = root_factory
        self._draw_fps = draw_fps
        self._renderer = renderer
        self._attached = True


# Process-global current session. ``None`` outside a dev run, which is what makes
# ``App.run()`` block normally in production.
_current_session: Optional[DevSession] = None


def current_dev_session() -> Optional[DevSession]:
    """Return the active dev session, or ``None`` when not under the dev runner.

    ``App.run()`` consults this to decide whether to block on the pyglet loop
    (production) or hand off to the runner (hot reload).
    """
    return _current_session


def set_dev_session(session: Optional[DevSession]) -> None:
    """Install (or clear) the process-global dev session. Runner-internal."""
    global _current_session
    _current_session = session
