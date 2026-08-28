"""App-scoped runtime intents.

Only intents that address the application as a whole live here. Intents that
address one window are in :mod:`nuiitivet.runtime.window_intents` and dispatch
through ``Window.of(context)``; see ``docs/design/APP_WINDOW.md``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExitAppIntent:
    """Intent to exit the application: close every window and stop the loop."""

    exit_code: int = 0
