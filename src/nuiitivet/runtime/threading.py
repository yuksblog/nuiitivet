"""Threading helpers for core runtime.

One definition of "the UI thread" lives here. Everything that has to decide
whether it is running on it -- the widget tree's assertions, and every
``Observable`` write, which now marshals by default -- asks :func:`is_ui_thread`
rather than comparing threads itself.

The test is an integer comparison against a cached ident, not
``threading.current_thread() is threading.main_thread()``. The two agree, but
``current_thread()`` costs a dict lookup on every call and this one runs on the
hot path of every observable write.
"""

from __future__ import annotations

import os
import threading
from typing import Optional


# Bound once: ``is_ui_thread`` runs on the hot path of every observable write,
# and a module-global lookup is cheaper than an attribute lookup on ``threading``.
_get_ident = threading.get_ident


def _main_thread_ident() -> Optional[int]:
    return threading.main_thread().ident


# The UI thread is the main thread until a backend says otherwise. Captured
# here rather than at first use so that importing from a worker cannot decide
# it -- ``main_thread()`` is the same object whichever thread asks.
_ui_thread_ident: Optional[int] = _main_thread_ident()


def set_ui_thread(ident: Optional[int] = None) -> None:
    """Register which thread the UI runs on. Defaults to the calling thread.

    The pyglet backend calls this when it installs its clock, so the two
    always agree: the thread that runs the frame loop is the thread deferred
    notifications are marshalled to. Nothing else needs to call it while the
    UI is the main thread, which is the only arrangement nuiitivet ships.
    """
    global _ui_thread_ident
    _ui_thread_ident = threading.get_ident() if ident is None else ident


def is_ui_thread() -> bool:
    """Whether the caller is running on the UI thread."""
    return _get_ident() == _ui_thread_ident


def assert_ui_thread() -> None:
    """Assert that the current thread is the UI thread.

    Raises:
        RuntimeError: If called from any other thread.
    """
    if not is_ui_thread():
        raise RuntimeError("This operation must be run on the UI thread (main thread).")


def _reset_after_fork() -> None:
    """Re-seat the UI thread on the child's main thread after ``os.fork()``.

    A forked child keeps only the forking thread, which it re-seats as its own
    ``main_thread()`` with a fresh ident, so the cached one would name a thread
    that no longer exists and ``is_ui_thread()`` would answer False everywhere.
    """
    global _ui_thread_ident
    _ui_thread_ident = _main_thread_ident()


if hasattr(os, "register_at_fork"):  # pragma: no branch - absent only on Windows
    os.register_at_fork(after_in_child=_reset_after_fork)
