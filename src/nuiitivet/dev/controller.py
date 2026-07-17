"""Hot-reload controller: drives the reload sequence on the main thread.

Owns the wiring between the background :class:`FileWatcher` and the main-thread
reload. The watcher only *signals* (sets a flag); a pyglet clock callback that
runs on the UI thread drains the flag and performs the actual reload, satisfying
the main-thread-only rule for tree mutation (``docs/design/THREADING_MODEL.md``).

The reload sequence (§8 of HOT_RELOAD.md):

1. snapshot ``Observable`` state from the live tree;
2. reload user modules in dependency order and re-fetch the factory (§9.6/§9.1);
3. rebuild the content root (resets Navigator/Overlay roots, unmounts the old
   tree on commit);
4. restore snapshot state into the new tree;
5. repaint.

On any error during 2–3 the previous tree is kept and the error is surfaced
(§9.4); the app and debug session stay alive.
"""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, cast

from .error_overlay import clear_reload_error, show_reload_error
from .reloader import identify_user_modules, reload_user_modules
from .snapshot import restore_observables, snapshot_observables
from .watcher import FileWatcher

if TYPE_CHECKING:
    from nuiitivet.runtime.app import App, RootFactory

logger = logging.getLogger(__name__)


class HotReloadController:
    """Coordinates file watching and in-place reloads for one App."""

    def __init__(
        self,
        app: "App",
        project_root: Path,
        initial_factory: "RootFactory",
        *,
        poll_interval: float = 0.4,
        drain_interval: float = 0.1,
    ) -> None:
        self._app = app
        self._project_root = project_root.resolve()
        self._factory: "RootFactory" = initial_factory
        self._drain_interval = drain_interval
        # Coalesces bursts of saves into a single reload; set on the watcher
        # thread, consumed on the UI thread.
        self._pending = threading.Event()
        self._watcher = FileWatcher(
            self._watched_paths, self._request_reload, poll_interval=poll_interval
        )
        self._installed = False

    def _watched_paths(self) -> Iterable[Path]:
        """Current set of user-module files to watch (re-queried each poll)."""
        paths: set[Path] = set()
        for module in identify_user_modules(self._project_root).values():
            file = getattr(module, "__file__", None)
            if file:
                paths.add(Path(file))
        return paths

    def _request_reload(self) -> None:
        """Signal a reload (called on the watcher thread — must stay cheap)."""
        self._pending.set()

    def _drain(self, dt: float) -> None:
        """UI-thread tick: apply a pending reload, if any."""
        if not self._pending.is_set():
            return
        self._pending.clear()
        self._do_reload()

    def _do_reload(self) -> None:
        app = self._app
        snapshot = snapshot_observables(app.root)

        try:
            result = reload_user_modules(self._project_root, old_factory=self._factory)
            new_factory: "RootFactory" = (
                cast("RootFactory", result.new_factory)
                if result.new_factory is not None
                else self._factory
            )
            new_root = app._rebuild_content_root(new_factory)
        except Exception:
            show_reload_error(app, traceback.format_exc())
            return

        try:
            app._commit_content_root(new_root)
            restored = restore_observables(app.root, snapshot)
        except Exception:
            # The new root is already committed; report but stay alive.
            show_reload_error(app, traceback.format_exc())
            return

        self._factory = new_factory
        clear_reload_error(app)
        app.invalidate()
        print(
            f"[nuiitivet.dev] reloaded {len(result.reloaded)} module(s), "
            f"restored {restored} value(s).",
            file=sys.stderr,
            flush=True,
        )

    def install(self) -> None:
        """Register the UI-thread drain and start the watcher thread."""
        if self._installed:
            return
        self._installed = True
        import pyglet

        pyglet.clock.schedule_interval(self._drain, self._drain_interval)
        self._watcher.start()

    def shutdown(self) -> None:
        """Stop watching and unschedule the drain."""
        self._watcher.stop()
        try:
            import pyglet

            pyglet.clock.unschedule(self._drain)
        except Exception:
            logger.debug("hot reload: failed to unschedule drain", exc_info=True)
