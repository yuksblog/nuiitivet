"""Which runtime the app is on: the desktop or a browser."""

from __future__ import annotations

import sys


def is_web() -> bool:
    """Whether the app runs in a browser, on Pyodide.

    The runtime decides, not the app code: the same ``app.py`` picks the
    browser backend there and the desktop backend everywhere else.
    """
    return sys.platform == "emscripten"


__all__ = ["is_web"]
