"""Threading helpers for core runtime."""

from __future__ import annotations

import threading


def assert_ui_thread() -> None:
    """Assert that the current thread is the main thread.

    Raises:
        RuntimeError: If called from a non-main thread.
    """
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("This operation must be run on the UI thread (main thread).")
