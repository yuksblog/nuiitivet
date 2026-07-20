"""In-process hot reload for nuiitivet (dev-only).

Launch an app with hot reload via::

    python -m nuiitivet.dev path/to/app.py
    python -m nuiitivet.dev --module yourpkg.app

Editing and saving a user module rebuilds the widget tree in place while the
window, the debugger session, and ``Observable`` state survive. See
``docs/design/HOT_RELOAD.md`` for the design and #359 for background.

This package is import-safe in production: importing it has no effect until the
runner installs a session. ``App.run()`` only consults :func:`current_dev_session`.
"""

from __future__ import annotations

from .bridge import DevBridge
from .interaction import InteractionEvent, InteractionJournal, InteractionRecorder
from .journal import ReloadEvent, ReloadJournal
from .perception import describe_tree
from .runtime_capture import RuntimeLogCapture
from .runtime_journal import RuntimeEvent, RuntimeJournal
from .session import DevSession, current_dev_session, set_dev_session

__all__ = [
    "DevBridge",
    "DevSession",
    "InteractionEvent",
    "InteractionJournal",
    "InteractionRecorder",
    "ReloadEvent",
    "ReloadJournal",
    "RuntimeEvent",
    "RuntimeJournal",
    "RuntimeLogCapture",
    "current_dev_session",
    "describe_tree",
    "set_dev_session",
]
