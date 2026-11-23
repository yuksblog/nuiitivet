"""Hot-reload controller: drives the reload sequence on the main thread.

Owns the wiring between the background :class:`FileWatcher` and the main-thread
reload. The watcher only *signals* (sets a flag); a pyglet clock callback that
runs on the UI thread drains the flag and performs the actual reload, satisfying
the main-thread-only rule for tree mutation.

The reload sequence:

1. snapshot ``State`` values and the declarative navigation stack from the
   live tree;
2. apply the saved modules and re-fetch the factory;
3. rebuild the content root (on commit: unmounts the old tree and hands the App
   its new navigator/overlay);
4. restore snapshot state and replay the navigation stack into the new tree;
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
from typing import TYPE_CHECKING, Any, Iterable, Optional, cast

from nuiitivet.widgeting.widget import Widget

from nuiitivet.remote.worker import retire_pool

from .error_overlay import clear_reload_error, show_reload_error
from .journal import ReloadJournal
from .navigation_snapshot import restore_navigation, snapshot_navigation
from .overlay_snapshot import restore_overlay, snapshot_overlay
from .comments import Comments
from .patcher import count_instances
from .reloader import Reloader, ReloadResult
from .slow_calls import SlowCallReporter
from .snapshot import restore_states, snapshot_states
from .source_edit import EditLog
from .watcher import FileWatcher

if TYPE_CHECKING:
    from nuiitivet.runtime.window import RootFactory, Window

logger = logging.getLogger(__name__)


class HotReloadController:
    """Coordinates file watching and in-place reloads for one App."""

    def __init__(
        self,
        app: "Window",
        project_root: Path,
        initial_factory: "RootFactory",
        *,
        poll_interval: float = 0.4,
        drain_interval: float = 0.1,
        journal: Optional[ReloadJournal] = None,
        comments: Optional[Comments] = None,
        edits: Optional[EditLog] = None,
        slow_calls: Optional[SlowCallReporter] = None,
    ) -> None:
        self._app = app
        self._project_root = project_root.resolve()
        self._factory: "RootFactory" = initial_factory
        self._drain_interval = drain_interval
        # Optional pull-able record of reload outcomes for an agent.
        # When present, every reload -- success or failure -- is recorded so the
        # agent can notice the code changed under it between turns.
        self._journal = journal
        # The human's comment-mode mark, whose members are weak and so
        # evaporate when the rebuild replaces every live object. Re-resolved
        # below like State values and the navigation stack, because a reload
        # lands in the middle of essentially every use of it.
        self._comments = comments
        # Layout edit mode's edits. Told after every reload whether its pending edit
        # landed, since a reload is how an edit takes effect at all.
        self._edits = edits
        # Forgets its reports once a save is applied: a function still slow after the edit is reported again.
        self._slow_calls = slow_calls
        self._reloader = Reloader(self._project_root)
        # Coalesces bursts of saves into a single reload; set on the watcher
        # thread, consumed on the UI thread.
        self._pending = threading.Event()
        self._watcher = FileWatcher(
            self._watched_paths, self._request_reload, poll_interval=poll_interval
        )
        self._installed = False

    def _watched_paths(self) -> Iterable[Path]:
        """Current set of user-module files to watch (re-queried each poll)."""
        return self._reloader.track()

    def _request_reload(self) -> None:
        """Signal a reload (called on the watcher thread — must stay cheap)."""
        self._pending.set()

    def request_reload(self, path: Optional[str] = None) -> None:
        """Reload on the next UI tick, for a file the dev runner wrote itself.

        The watcher is told it has seen ``path`` as written, so the poll that
        follows does not reload a second time.
        """
        if path is not None:
            self._watcher.acknowledge(Path(path))
        self._pending.set()

    def _drain(self, dt: float) -> None:
        """UI-thread tick: apply a pending reload, if any."""
        if not self._pending.is_set():
            return
        self._pending.clear()
        self._do_reload()

    def _do_reload(self) -> None:
        if self._slow_calls is None:
            self._reload()
            return
        # The rebuild runs every build at once and holds no frame up.
        with self._slow_calls.paused():
            self._reload()

    def _reload(self) -> None:
        app = self._app
        snapshot = snapshot_states(app.root)
        # Capture the declarative navigation stack before the rebuild replaces
        # the App's navigator with a fresh one at its initial route.
        nav_snapshot = snapshot_navigation(app)

        try:
            result = self._reloader.reload(old_factory=self._factory)
            if self._slow_calls is not None:
                self._slow_calls.reset()
            # The next worker call runs the reloaded source, not a child's copy of the old one.
            retire_pool()
            new_factory: "RootFactory" = (
                cast("RootFactory", result.new_factory)
                if result.new_factory is not None
                else self._factory
            )
            new_content = app._rebuild_content_root(new_factory)
        except Exception:
            self._reload_failed(app, traceback.format_exc())
            return

        # Taken only once the rebuild succeeded: from here the old overlay hands its entries over.
        overlay_snapshot = snapshot_overlay(app)
        try:
            app._commit_content_root(new_content)
            # Before the State restore, so a re-shown dialog gets its state back too.
            restored_entries = restore_overlay(app, overlay_snapshot)
            restored = restore_states(app.root, snapshot)
            restored_routes = restore_navigation(app, nav_snapshot)
            if self._comments is not None:
                self._comments.restore(app.root)
        except Exception:
            # The new root is already committed; report but stay alive.
            self._reload_failed(app, traceback.format_exc())
            return

        self._factory = new_factory
        clear_reload_error(app)
        app.invalidate()
        self._reload_secondary_windows(result.changed)
        self._edit_landed()
        # The snapshots hold what the old tree held; counted, they would read as left behind.
        del snapshot, nav_snapshot, overlay_snapshot
        stale = self._stale_instances(result, result.reloaded)
        if self._journal is not None:
            self._journal.record_success(
                result.reloaded,
                patched=result.patched,
                changed=result.changed,
                stale=stale,
                inert_windows=self._inert_window_ids(),
            )
        print(
            f"[nuiitivet.dev] patched {len(result.patched)} module(s), re-executed {len(result.reloaded)}, "
            f"restored {restored} value(s), {restored_routes} route(s), {restored_entries} overlay layer(s).",
            file=sys.stderr,
            flush=True,
        )
        if stale:
            print(
                f"[nuiitivet.dev] {_stale_message(result.reloaded, stale)} Restart the app to update them.",
                file=sys.stderr,
                flush=True,
            )

    def _reload_failed(self, app: "Window", traceback_text: str) -> None:
        """Report a reload that raised, with the old instances that may be its cause."""
        result = self._reloader.last
        stale = self._stale_instances(result, result.edited)
        hint = (
            f"{_stale_message(result.edited, stale)} "
            "Restart the app unless the error below is in the code you just changed."
            if stale
            else None
        )
        if self._journal is not None:
            self._journal.record_error(traceback_text, changed=result.changed, stale=stale)
        show_reload_error(app, traceback_text, hint=hint)
        self._edit_failed(traceback_text)

    def _stale_instances(self, result: ReloadResult, modules: Iterable[str]) -> dict[str, int]:
        """Living non-widget instances of the classes ``modules`` defined before they were re-executed.

        A tree owns its widgets, so an old widget is the old tree's and not what the save left behind.
        """
        classes = [
            ref
            for name in modules
            for ref in result.replaced.get(name, ())
            if (cls := ref()) is not None and not issubclass(cls, Widget)
        ]
        result.replaced.clear()
        counts = count_instances(classes)
        return {f"{cls.__module__}.{cls.__qualname__}": count for cls, count in counts.items()}

    def _windows(self) -> list[Any]:
        """Every open window, the main one included."""
        try:
            owner = self._app.app
            return list(getattr(owner, "windows", ()) or ())
        except Exception:
            return [self._app]

    def _inert_window_ids(self) -> list[int]:
        """Ids of open windows whose instance root makes reload a no-op for them.

        Per-window, not scalar: a multi-window app can mix a factory root with
        an instance root, and only the latter is inert.
        """
        return [w.id for w in self._windows() if getattr(w, "_hot_reload_inert", False)]

    def _edit_landed(self) -> None:
        """Let a pending layout edit check itself against the rebuilt trees."""
        if self._edits is None:
            return
        try:
            self._edits.after_reload([getattr(w, "root", None) for w in self._windows()])
        except Exception:
            logger.debug("hot reload: checking the pending edit failed", exc_info=True)

    def _edit_failed(self, traceback_text: str) -> None:
        if self._edits is not None:
            self._edits.reload_failed(traceback_text)

    def _reload_secondary_windows(self, changed: list[str]) -> None:
        """Rebuild every other open window's tree from its own root factory.

        The main window's rebuild re-resolves its factory from the reloaded
        entry module; a secondary window keeps the factory it was constructed
        with, re-invoked here so its content picks up the reloaded modules.
        State values are snapshotted and restored per window, like the main
        one. A window whose rebuild fails shows the reload error overlay in
        that window and does not abort the others.
        """
        try:
            owner = self._app.app
        except Exception:
            return
        for window in list(getattr(owner, "windows", ()) or ()):
            if window is self._app:
                continue
            snapshot = snapshot_states(window.root)
            try:
                content = window._rebuild_content_root()
                window._commit_content_root(content)
                restore_states(window.root, snapshot)
            except Exception:
                tb = traceback.format_exc()
                if self._journal is not None:
                    self._journal.record_error(tb, changed=changed)
                show_reload_error(window, tb)
                continue
            clear_reload_error(window)
            window.invalidate()

    def install(self) -> None:
        """Register the UI-thread drain and start the watcher thread."""
        if self._installed:
            return
        self._installed = True
        self._reloader.track()
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


def _stale_message(modules: Iterable[str], stale: dict[str, int]) -> str:
    listed = ", ".join(f"{name} x{count}" for name, count in sorted(stale.items()))
    return (
        f"This save re-executed {', '.join(modules)}. "
        f"Objects made before it still use the old classes: {listed}."
    )
