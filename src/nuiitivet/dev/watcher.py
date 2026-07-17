"""File watcher thread for hot reload (§4/§8 of HOT_RELOAD.md).

The watcher runs on a **background thread** and does one job: notice that a
watched file changed. It must never touch the widget tree — tree mutation is
main-thread-only. On a change it invokes ``on_change`` (still on the watcher
thread); the runner's callback merely enqueues a request that a main-thread
pyglet clock tick later drains and applies. A useful consequence: a save made
while stopped at a breakpoint (event loop paused) is simply queued and applied on
resume.

Implementation is a dependency-free mtime poller. ``paths_provider`` is re-queried
each tick so newly imported user modules become watched automatically.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Iterable

logger = logging.getLogger(__name__)


class FileWatcher:
    """Poll a set of files for modification and fire a callback on change."""

    def __init__(
        self,
        paths_provider: Callable[[], Iterable[Path]],
        on_change: Callable[[], None],
        *,
        poll_interval: float = 0.4,
    ) -> None:
        """Create a watcher.

        Args:
            paths_provider: Called each tick to get the current set of files to
                watch. Re-querying keeps the watch set in sync as modules load.
            on_change: Invoked (on the watcher thread) when any watched file's
                modification time changes. Must be thread-safe and quick — it
                should only signal the main thread, not do the reload itself.
            poll_interval: Seconds between polls.
        """
        self._paths_provider = paths_provider
        self._on_change = on_change
        self._poll_interval = max(0.05, float(poll_interval))
        self._mtimes: dict[Path, float] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def _snapshot_mtimes(self) -> dict[Path, float]:
        result: dict[Path, float] = {}
        for path in self._paths_provider():
            try:
                result[path] = path.stat().st_mtime
            except OSError:
                continue
        return result

    def _run(self) -> None:
        # Prime with the current state so we don't fire on the first tick.
        self._mtimes = self._snapshot_mtimes()
        while not self._stop.wait(self._poll_interval):
            current = self._snapshot_mtimes()
            changed = any(
                path not in self._mtimes or self._mtimes[path] != mtime
                for path, mtime in current.items()
            )
            self._mtimes = current
            if changed:
                try:
                    self._on_change()
                except Exception:
                    logger.exception("hot reload: on_change callback raised")

    def start(self) -> None:
        """Start the background polling thread (idempotent)."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="nuiitivet-hot-reload-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the thread to stop. Does not block."""
        self._stop.set()
